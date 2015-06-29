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

def monadic(monad_name):
    """ Decorator to apply a NodeTransformer to a single function """
    def wrapper(func):
        # uncompile function
        unc = uncompile(func.func_code)

        # convert to ast and apply visitor
        tree = parse_snippet(*unc)
        MonadicFunctionDef(monad_name).visit(tree)
        MonadicListComp().visit(tree)
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
    """ Import the necessary functions to create monad abstractions """

    def __init__(self, monad_name):
        self.monad_name = monad_name

    def visit_FunctionDef(self, node):
        monad_any_t = func_call(name(self.monad_name), [name('any_t')])

        ## from monad_name, any_t, flat_map import contract
        import_ = ast.ImportFrom(module="contract",
                                 names=map(alias, ["any_t", "flat_map", "unit", self.monad_name]))
        ast.fix_missing_locations(import_)

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

        node.body = [import_, bind, unit] + node.body
        return node

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
