"""
Oren Tirosh <orent@hishome.net>

Convert code objects (functions bodies only) to source code and back.
This doesn't actually decompile the bytecode - it simply fetches the
source code from the .py file and then carefully compiles it back to 
a 100% identical code object:

    c == recompile(*uncompile(c))

Not supported:
    Lambdas
    Nested functions  (you can still process the function containing them)
    Anything for which inspect.getsource can't get the source de

http://code.activestate.com/recipes/578353-code-to-source-and-back/
"""

import ast, inspect, re
import astdump
from types import CodeType as code, FunctionType as function
from contract import any_t
import inspect

import __future__
PyCF_MASK = sum(v for k, v in vars(__future__).items() if k.startswith('CO_FUTURE'))

class Error(Exception):
    pass

class Unsupported(Error):
    pass

class NoSource(Error):
    pass

def uncompile(c):
    """ uncompile(codeobj) -> [source, filename, mode, flags, firstlineno, privateprefix] """
    if c.co_flags & inspect.CO_NESTED or c.co_freevars:
        raise Unsupported('nested functions not supported')
    if c.co_name == '<lambda>':
        raise Unsupported('lambda functions not supported')
    if c.co_filename == '<string>':
        raise Unsupported('code without source file not supported')

    filename = inspect.getfile(c)
    try:
        lines, firstlineno = inspect.getsourcelines(c)
    except IOError:
        raise NoSource('source code not available')
    source = ''.join(lines)

    # __X is mangled to _ClassName__X in methods. Find this prefix:
    privateprefix = None
    for name in c.co_names:
        m = re.match('^(_[A-Za-z][A-Za-z0-9_]*)__.*$', name)
        if m:
            privateprefix = m.group(1)
            break

    return [source, filename, 'exec', c.co_flags & PyCF_MASK, firstlineno, privateprefix]

def recompile(source, filename, mode, flags=0, firstlineno=1, privateprefix=None):
    """ recompile output of uncompile back to a code object. source may also be preparsed AST """
    if isinstance(source, ast.AST):
        a = source
    else:
        a = parse_snippet(source, filename, mode, flags, firstlineno)
    node = a.body[0]
    if not isinstance(node, ast.FunctionDef):
        raise Error('Expecting function AST node')

    c0 = compile(a, filename, mode, flags, True)

    # This code object defines the function. Find the function's actual body code:
    for c in c0.co_consts:
        if not isinstance(c, code):
            continue
        if c.co_name == node.name and c.co_firstlineno == node.lineno:
            break
    else:
        raise Error('Function body code not found')

    # Re-mangle private names:
    if privateprefix is not None:

        def fixnames(names):
            isprivate = re.compile('^__.*(?<!__)$').match
            return tuple(privateprefix + name if isprivate(name) else name for name in names)

        c = code(c.co_argcount, c.co_nlocals, c.co_stacksize, c.co_flags, c.co_code, c.co_consts,
                fixnames(c.co_names), fixnames(c.co_varnames), c.co_filename, c.co_name,
                c.co_firstlineno, c.co_lnotab, c.co_freevars, c.co_cellvars)
    return c

def parse_snippet(source, filename, mode, flags, firstlineno, privateprefix_ignored=None):
    """ Like ast.parse, but accepts indented code snippet with a line number offset. """
    args = filename, mode, flags | ast.PyCF_ONLY_AST, True
    prefix = '\n'
    try:
        a = compile(prefix + source, *args)
    except IndentationError:
        # Already indented? Wrap with dummy compound statement
        prefix = 'with 0:\n'
        a = compile(prefix + source, *args)
        # peel wrapper
        a.body = a.body[0].body
    ast.increment_lineno(a, firstlineno - 2)
    return a

def monadic_comp(monad):
    """ Decorator that creates helper functions within the function body and transforms
        all the list comprehension into a monadic expression """
    module_name = inspect.getmodule(monad).__name__
    monad_name = monad.__name__

    def wrapper(func):
        # uncompile function
        unc = uncompile(func.func_code)

        # convert to ast and apply visitor
        tree = parse_snippet(*unc)
        MonadicFunctionDef(module_name, monad_name).visit(tree)
        MonadicListComp().visit(tree)
        ast.fix_missing_locations(tree)
        unc[0] = tree

        # recompile and patch function's code
        func.func_code = recompile(*unc)
        return func

    return wrapper

def monadic(monad):
    """ Decorator that creates helper functions within the function body and transforms
        it into a monadic expression """
    module_name = inspect.getmodule(monad).__name__
    monad_name = monad.__name__

    def wrapper(func):
        # uncompile function
        unc = uncompile(func.func_code)

        # convert to ast and apply visitor
        tree = parse_snippet(*unc)
        MonadicStatement().visit(tree)
        MonadicFunctionDef(module_name, monad_name).visit(tree)
        ast.fix_missing_locations(tree)
        unc[0] = tree

        # recompile and patch function's code
        func.func_code = recompile(*unc)
        return func

    return wrapper

# Monadic bind example
# x3 for x1 in call1
#    for x2 in call2(x1)
#    for x3 in call3(x1, x2)
#
# bind(call(), lambda x1:
# bind(call2(x1), lambda x2:
# bind(call3(x1,x2), lambda x3: monad['1'](x3))))

class MonadicListComp(ast.NodeTransformer):

    def visit_ListComp(self, node):
        generators = node.generators

        def create_bind(gs):
            l = len(gs)
            g = gs[0]
            iter_call = g.iter
            if l == 1:
                la = ast.Lambda(args=ast.arguments(args=[g.target], defaults=[]),
                                body=func_call(name('unit'), args=[node.elt])) # ast.Str(s="TODO")) # TODO
                return func_call(name('bind'), [iter_call, la])
            if l > 1:
                la = ast.Lambda(args=ast.arguments(args=[g.target], defaults=[]),
                                body=create_bind(gs[1:]))
                return func_call(name('bind'), [iter_call, la])
            raise Exception('Empty generators for list comprehension')

        call = create_bind(generators)
        newnode = call
        ast.copy_location(newnode, node)
        ast.fix_missing_locations(newnode)
        return newnode


class MonadicFunctionDef(ast.NodeTransformer):
    """ Import and declare the necessary functions to create monad abstractions """

    def __init__(self, module_name, monad_name):
        self.module_name = module_name
        self.monad_name = monad_name

    def visit_FunctionDef(self, node):
        monad_any_t = func_call(name(self.monad_name), [name('any_t')])

        ## from contract import any_t, flat_map
        import_contract = ast.ImportFrom(module="contract",
                                         names=map(alias, ["any_t", "flat_map", "unit"]))
        ast.fix_missing_locations(import_contract)

        ## from monad_module import monad_name
        import_monad = ast.ImportFrom(module=self.module_name,
                                         names=map(alias, [self.monad_name]))
        ast.fix_missing_locations(import_monad)

        ## bind = flat_map(monad_name(any_t))
        bind = ast.Assign(
            [name_store('bind')],
            func_call(name('flat_map'), [monad_any_t])
        )
        ast.fix_missing_locations(bind)

        ## unit = unit(monad_name(any_t))
        unit = ast.Assign(
            [name_store('unit')],
            func_call(name('unit'), [monad_any_t])
        )
        ast.fix_missing_locations(unit)

        ## non_monadic = unit
        normal = ast.Assign(
            [name_store('normal')],
            name('unit')
        )
        ast.fix_missing_locations(normal)

        node.body = [import_contract, import_monad, bind, unit, normal] + node.body
        return node


class MonadicStatement(ast.NodeTransformer):
    """ Transforms the function body into a monadic expression """

    def visit_FunctionDef(self, node):
        def create_bind(stmts):
            l = len(stmts)
            s = stmts[0]
            if l == 1:
                return final_call(s)
            if l > 1:
                call = get_call(s)
                la = ast.Lambda(args=ast.arguments(args=[get_name(s)], defaults=[]),
                                body=create_bind(stmts[1:]))
                return func_call(name('bind'), [call, la])
            raise Exception('Empty statement for list comprehension')
        call = create_bind(node.body)
        newnode = ast.Return(call)
        ast.copy_location(newnode, node)
        ast.fix_missing_locations(newnode)
        node.body=[newnode]
        return node

# Helpers for assign, expr, return ast handlers

def get_name(stmt):
    def get_assign_name(a):
        a.targets[0].cxt=ast.Load()
        return a.targets[0]
    def get_expr_name(e):
        return name('_')
    # Algebra is like inversion of control
    return aer_algebra(get_assign_name, get_expr_name, class_error, stmt)

value_expressions = [ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Dict, ast.Set, ast.ListComp, ast.SetComp,
                     ast.DictComp, ast.Num, ast.Str, ast.Subscript, ast.List, ast.Tuple]

def is_value_expr(expr):
    return expr.__class__ in value_expressions

def get_assign_call(a):
    vclass = a.value.__class__
    if vclass is ast.Call:
        return a.value
    elif is_value_expr(a.value):
        return ast.Call(func=name('unit'), args=[a.value], keywords=[])
    else:
        raise TypeError("No call object is found")

def get_expr_call(e):
    vclass = e.value.__class__
    if vclass is ast.Call:
        return e.value
    else:
        raise TypeError("No call object is found")

def get_call(stmt):
    return aer_algebra(get_assign_call, get_expr_call, class_error, stmt)

def get_return_expr(stmt):
    def get_expr(r):
        return r.value
    return aer_algebra(class_error, class_error, get_expr, stmt)

def final_call(stmt):
    def return_call(s):
        return func_call(name('unit'), args=[get_return_expr(s)])
    return aer_algebra(get_assign_call, get_expr_call, return_call, stmt)

def class_error(s):
    raise Exception("Non assignment type {t}".format(t=s.__class__))

def aer_algebra(a, e, r, stmt):
    sc = stmt.__class__
    if sc == ast.Assign:
        return a(stmt)
    elif sc == ast.Expr:
        return e(stmt)
    elif sc == ast.Return:
        return r(stmt)
    else:
        raise TypeError("Unexpected statement {type}".format(type=sc))

# AST Helpers

def name(n):
    return ast.Name(id=n, ctx=ast.Load())

def name_store(n):
    return ast.Name(id=n, ctx=ast.Store())

def func_call(name, args):
    return ast.Call(func=name, args=args, keywords=[])

def alias(name):
    return ast.alias(name=name)

def at(name, str_idx):
    return ast.Subscript(value=name, slice=ast.Index(str_idx), ctx=ast.Load())

