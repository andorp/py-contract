
""" A contract consits of a type check of a given variable """

import array
import types

# Category

## Category consists of
## - contract as an object
## - guarded functions as a morphism

# A contract that checks the parameter for a given type
def type_of(t):
    def contract(x):
        if not isinstance(x, t):
            raise TypeError('{type} is expected found {found}'.format(type=t, found=type(x)))
        return x
    return contract

## A special contract that does not checks the type of the
## parameter.
def any_t(x):
    return x

## A guarded function, expects a guarded input and returns a guarded output
def inc(x):
    x = int_t(x)
    return int_t(x + 1)


string_t = type_of(str)
unicode_t = type_of(unicode)
bool_t = type_of(bool)
int_t = type_of(int)
object_t = type_of(object)
func_t = type_of(types.FunctionType)

array_t = type_of(array.array)
list_t = type_of(list)
dict_t = type_of(dict)

## List functor acting on contract, if we have a morhishm as a guarded
## function, as the guarded function checks the input type of its elements
## It produces new objects and new morhisms
def list_of(c):
    def fmap(l):
        return map(c,list_t(l))
    return fmap

## Dict functor acting on contract, if we have a morhism as a guarded
## function, as the guard function checks the input type of its value elements
def dict_of(c):
    def fmap(d):
        dict_t(d)
        result = {}
        for k in d:
            result[k] = c(d[k])
        return result
    return fmap

# Maybe

## Free pointed set in category theory, Maybe in Haskell, Option in Scala
class Maybe:
    def getOrElse(self, x):
        if isinstance(self, Just):
            return self.x
        else:
            return x

    def flatten(self):
        return maybeFlatten(any_t)(self)

    def map(self,c):
        return maybe(c)(self)

class Nothing(Maybe):
    def __str__(self): return "Nothing"

class Just(Maybe):
    def __init__(self, x): self.x = x
    def __str__(self): return "(Just {x})".format(x=str(self.x))

nothing = Nothing()
just = lambda x: Just(x)

# Maybe functor

## Functor based on the Maybe data
def maybe(c):
    def fmap(m):
        if isinstance(m, Just):
            return Just(c(m.x))
        elif isinstance(m, Nothing):
            return m
        else:
            raise TypeError('Expected Nothing or Just(value)')
    return fmap

## One other morphism between contracts(object in our category)
def repeat(s):
    s = string_t(s)
    return string_t(s + s)

# Unit and flatten

def listOfUnit(c):
    def wrap(x):
        x = no_times(list_of)(c)(x)
        return once(list_of)(c)([x])
    return wrap

def maybeUnit(c):
    def wrap(x):
        x = no_times(maybe)(c)(x)
        return once(maybe)(c)(some(x))
    return wrap

def listOfFlatten(c):
    def flatten(llx):
        llx = twice(list_of)(c)(llx) # [[1], [1,4]]
        result = []
        for xs in llx:
            result = result + xs
        return once(list_of)(c)(result)
    return flatten

def maybeFlatten(c):
    def flatten(mmx):
        mmx = twice(maybe)(c)(mmx)
        result = mmx
        if isinstance(mmx, Just):
            result = result.x
        return once(maybe)(c)(result)
    return flatten

def maybe_test():
    print maybe(repeat)(nothing)
    print maybe(repeat)(just("Joe")).getOrElse("Jane")
    print maybe(repeat)(nothing).getOrElse("Jane")

def listOfFlatten_test():
    print listOfFlatten(int_t)([[1], [2,3]])

def maybeFlatten_test():
    print maybeFlatten(int_t)(just(just(3)))
    print just(just(4)).flatten()

def twice(functor):
    def apply(c):
        return functor(functor(c))
    return apply

def once(functor):
    return functor

def no_times(functor):
    def apply(c):
        return c
    return apply

# Monad

class Monad:
    def flatMap(self, c):
        return self.map(c).flatten()

Maybe.__bases__ += (Monad,)

def maybe_monad_test():
    xs = just(4)
    ys = nothing
    zs = just(5)
    r = xs.flatMap(lambda x:
        ys.flatMap(lambda y:
        zs.map(lambda z: (x * y) + z
        )))
    print r

# Product

## Given a list of contracts, creates a contract for
## a list whose elements satisfy the respective contracts.
def prodn(cs):
    # Checks if the argument is a list of contracts
    list_of(func_t)(cs)
    length = len(cs)
    def apply(args):
        list_t(args)
        if (len(args) != length):
            raise TypeError("Expected {length} arguments".format(length=length))
        result = []
        for i in range(0, length):
            result.append(cs[i](args[i]))
        return result
    return apply

def prodn_test():
    int_str_t = prodn([int_t, string_t])
    x = int_str_t([5, "hello"])
    print x

## Given a dict of contracts, creates a contract fo
## a dict whose elements satisfy the respective contracts
def prods(cs):
    # Checks if the argument is a dict of contracts
    dict_of(func_t)(cs)
    length = len(cs)
    def apply(args):
        dict_t(args)
        if (len(args) != length):
            raise TypeError("Expected {length} arguments".format(length=length))
        result = {}
        for k in cs:
            result[k] = cs[k](args[k])
        return result
    return apply

def prods_test():
    int_str_t = prods({'i': int_t, 's': string_t})
    x = int_str_t({'i': 5, 's': "hello"})
    print x

def prod_obj(cs):
    prod = prods(cs)
    def apply(args):
        object_t(args)
        args.__dict__.update(prod(args.__dict__))
        return args
    return apply

class ProdVal:
    def __init__(self):
        self.i = 5
        self.s = 'hello'

def prod_test():
    int_str_t = prod_obj({'i': int_t, 's': string_t})
    x = int_str_t(ProdVal())
    print x.__class__
    print x.__dict__

# Coproduct

## Given a list of contracts creates a new contract for a
## 2-element list where item 0 is an index and item 1
## is a value satisfying the contract at that index
## in the array
def coprodn(cs):
    list_of(func_t)(cs)
    length = len(cs)
    def apply(choice):
        list_t(choice)
        int_t(choice[0])
        if len(choice) != 2:
            raise TypeError("Expected [int_t, any_t]")
        if choice[0] >= length:
            raise TypeError("Tag out of range.")
        return [choice[0], cs[choice[0]](choice[1])]
    return apply

def coprodn_test():
    int_str_t = coprodn([int_t, string_t])
    x = int_str_t([0, 1])
    print x
    x = int_str_t([1, "hello"])
    print x

def coprods(cs):
    dict_of(func_t)(cs)
    def apply(choice):
        list_t(choice)
        string_t(choice[0])
        if len(choice) != 2:
            raise TypeError("Expected [string_t, any_t]")
        if choice[0] not in cs:
            raise TypeError("Unknown tag: {tag}".format(tag=choice[0]))
        return [choice[0], cs[choice[0]](choice[1])]
    return apply

def coprods_test():
    int_str_t = coprods({ 'i': int_t, 's': string_t })
    x = int_str_t(['i', 1])
    print x
    x = int_str_t(['s', "hello"])
    print x

## Alternative implementation of the maybe monad
def maybe_c(c):
    return coprods(
        { 'none': prods({})
        , 'some': c
        })
## maybe_c(int_t) accepts ['none', {}] or ['some', 4]

def maybe_c_test():
    x = maybe_c(int_t)(['none', {}])
    print x

# Pullback

## Given a list of function, returns a contract
## for those array where the elements all map to the
## some value under the given function, e.g. given
## [f,g], we get a contract for those [x, y] for which
## f(x) == g(y)
def pullbackn(fs):
    c = prodn(fs)
    length = len(fs)
    def pullback(args):
        list_t(args)
        result = c(args)
        result_l = len(result)
        for i in range(1, result_l):
            if result[i] != result[i - 1]:
                raise TypeError("Failed to match pullback contraint")
        return result
    return pullback
## Example of the multiplication of matrices, the pullback
## checks if the two matrix can be multiplied.
## Exercise

# Hom functor

## Creates a contract for a function whose inputs and output
## satisfy the given contracts
def hom(*arguments):
    arguments = list(arguments)
    before = prodn(list_of(func_t)(arguments[0:-1]))
    after = func_t(arguments[-1])
    def result(middle):
        def wrapped(*varArgs):
            before(list(varArgs))
            return after(middle(*varArgs))
        return wrapped
    return result

def repeat_i(i):
    print i
    return "{x}{x}".format(x=i)

repeat_h = hom(int_t, string_t)(repeat_i)

def hom_test():
    x = repeat_h(3)
    print x

# Monoid

def monoid(set, times, ident):
    return prods({
        't': func_t,
        '*': hom(set, set, set),
        '1': hom(set)
    })({
        't': set,
        '*': times,
        '1': ident
    })

def test_mon_assoc(mon, a, b, c):
    a = mon['t'](a)
    b = mon['t'](b)
    c = mon['t'](c)
    if mon['*'](a, mon['*'](b, c)) != \
       mon['*'](mon['*'](a, b), c):
       raise Exception("Not associative")

concat = monoid(
    string_t,
    lambda x, y: x + y,
    lambda: ""
    )

def str_monoid_test():
    x = concat['*']("Hello ", "World")
    print x

addition = monoid(
    int_t,
    lambda x, y: x + y,
    lambda: 0
    )

# Monads as monoids

## A monad is a monoid in the category whose
## objects are endofunctors, and whose morphism
## are natural transformations
def monad(functor, times, ident):
    def monad_t(t):
        func_t(functor)
        return prods({
                't': func_t,
                '*': hom(twice(functor)(t), functor(t)),
                ## Times is a natural transformation between functor twice and functor once
                ## Monoids use cartasian product as product,
                ## Monads use tensor product which is composition to combine the functors
                ## It is more general operation putting two things together, it is not necessary pairing
                '1': hom(no_times(functor)(t), functor(t))
            })({
                't': functor(t),
                '*': times(t),
                '1': ident(t)
            })
    return monad_t

listMonad = monad(list_of, listOfFlatten, listOfUnit)

def listMonad_test():
    l = listMonad(int_t)
    print l['1'](5)
    print l['*']([[2,3],[4]])

# UpTo Example

def upTo(x):
    int_t(x)
    result = []
    for i in range(0,x):
        result.append(i)
    return list_of(int_t)(result)

# in comprehension
# In Scala: for ( x <- upto(5); y <- upto(x); { yield(y); })
def upTo_test():
    print list_of(upTo)(upTo(5))
    print listMonad(int_t)['*'](list_of(upTo)(upTo(5)))

# Monoid homomorphism

def equalizer(fs):
    l = len(fs)
    if l < 1:
        raise TypeError("Equalizer can not be defined for empty set of functions")
    def eq(x):
        tuple = []
        for i in range(0, l):
            tuple.append(x)
        return pullbackn(fs)(tuple)[0]
    return eq

# Functions between homomorhism, preserves the structure
# of the monoid

def bit_t(b):
    if b == 0 or b == 1:
        return b
    else:
        raise TypeError('Expected a bit found {found}'.format(found=b))

# Constant Functor
K = hom(any_t, hom(any_t))(lambda x: lambda: x)

xor = hom(bit_t, bit_t, bit_t)(lambda x, y: bool(x) != bool(b))
xorMonoid = monoid(bit_t, xor, K(0))

add = hom(int_t, int_t, int_t)(lambda x, y: x + y)
addMonoid = monoid(int_t, add, K(0))

mul = hom(int_t, int_t, int_t)(lambda x, y: x * y)
mulMonoid = monoid(int_t, mul, K(1))

# Monoidal homomorhism
parity = hom(int_t, bit_t)(lambda x: x % 2)

# TODO: Check it
## Monoidal function
#def monFunc(m1, m2, f):
#    return {
#        't': hom(m1['t'], m2['t'])(f),
#        '*': equalizer([
#                lambda x, y: f(m1['*'](x, y)),
#                lambda x, y: m2['*'](f(x), f(y))
#            ]),
#        '1': equalizer([
#                lambda: f(m1['1']()),
#                m2['1']
#            ])
#    }

def monHom(before, after):
    def hom(middle):
        return {
            't': hom(before['t'], after['t'])(middle['t']),
            '*': hom(before['t'], before['t'], after['t'])(middle['*']),
            '1': hom(after['t'])(middle['1'])
        }
    return middle

# Partial orders as categories

def leq(pair):
    prodn([int_t, int_t])(pair)
    x = pair[0]
    y = pair[1]
    if (x > y):
        raise TypeError("{x} is greater than {y}".format(x=x, y=y))
    return pair

def leqHom(before, after):
    leq(before)
    leq(after)
    def compose(middle):
        leq(middle)
        if(middle[0] != before[1]):
            raise TypeError("Expected {x}".format(x=middle[0]))
        if(middle[1] != after[0]):
            raise TypeError("Expected {x}".format(x=middle[1]))
        return [before[0], after[1]]
    return compose

def leq_test():
    x = leqHom([3,5],[7,9])([5,7])
    print x

# Div category

def div(pair):
    prodn([int_t, int_t])(pair)
    x = pair[0]
    y = pair[1]
    if ((x / y) % 1 != 0):
        raise TypeError("{x} does not devide {y}".format(x=x, y=y))
    return pair

def divHom(before, after):
    div(before)
    div(after)
    def compose(middle):
        div(middle)
        if(middle[0] != before[1]):
            raise TypeError("Expected {x}".format(x=middle[0]))
        if(middle[1] != after[0]):
            raise TypeError("Expected {x}".format(x=middle[1]))
        return [before[0], after[1]]
    return compose

def div_test():
    x = divHom([3,6], [24, 96])([6, 24])
    print x

# Formality around the categories

def category(c, cHom):
    return prods({
        'c': func_t,
        'cHom': hom(c, c, c)
    })({
        'c': c,
        'cHom': cHom
    })

LEQ = category(leq, leqHom)
DIV = category(div, divHom)

def guardFunc(triple):
    return prodn([func_t, func_t, hom(triple[0], triple[1])])(triple)

def guardHom(before, after):
    before = guardFunc(before)
    after = guardFunc(after)
    def compose(mmiddle):
        middle = guardFunc(middle)
        def f(x):
            return [before[0], after[1], after[2](middle[2](before[2](x)))]
        return f
    return compose

GUARD = category(guardFunc, guardHom)

def mon(triple):
    src = prods({
        't': func_t,
        '*': hom(triple[0]['t'], triple[0]['t'], triple[0]['t']),
        '1': hom(triple[0]['t'])
    })(triple[0])
    tgt = prods({
        't': func_t,
        '*': hom(triple[1]['t'], triple[1]['t'], triple[1]['t']),
        '1': hom(triple[1]['t'])
    })(triple[1])
    mh = hom(triple[0]['t'], triple[1]['t'])(triple[2])
    return [src, tgt, mh]

def monHom(before, after):
    before = mon(before)
    after = mon(after)
    def compose(mmiddle):
        middle = mon(middle)
        def f(x):
            return [before[0], after[1], after[2](middle[2](before[2](x)))]
        return f
    return compose

MON = category(mon, monHom)

def addHom(before, after):
    int_t(before)
    int_t(after)
    def compose(middle):
        int_t(middle)
        return after + middle + before
    return compose

ADD = category(int_t, addHom)

def mulHom(before, after):
    int_t(before)
    int_t(after)
    def compose(middle):
        int_t(middle)
        return after * middle * before
    return compose

MUL = category(int_t, mulHom)

def fromMonoid(m):
    def compose(before, after):
        before = m['t'](before)
        after = m['t'](after)
        def f(middle):
            middle = m['t'](middle)
            return m['*'](after, m['*'](middle, before))
        return f
    return category(m['t'], compose)

# Monoidal functor

def lazy(c):
    return hom(c)

lazyLift = K

def lazyFlatten(lazyLazyX):
    return lazyLazyX()

lazyMonad = monad(lazy, lazyLift, lazyFlatten)

def lazyPhi(lazyProd):
    return map(lazyLift, list_t(lazyProd()))

# Lazyness and recursive data-types

# list_d(x) = maybe((x, list_d(x)))

#def list_d(c):
#    return coprods({
#        'nil':  prodn([]),
#        'head': prods(c, list_d(c))
#    })
# This does not work, as we have to calculate list_d
# recursively and the thing is going fill up the stack
# infinitely

def list_d(c):
    return coprods({
        'nil': prodn([]),
        'cons': prodn([
            c,
            lambda tail: list_d(c)(tail)
        ])
    })

def list_d_test():
    x = list_d(int_t)(['nil', []])
    print x
    x = list_d(int_t)(['cons', [1, ['nil', []]]])
    print x
    x = list_d(int_t)(['cons', [2, ['cons', [1, ['nil', []]]]]])
    print x

def stream(c):
    return coprods({
        'nil': prodn([]),
        'cons': prodn([
            c,
            lambda tail: lazy(stream(c))(tail)
        ])
    })

def stream_test():
    stm = stream(int_t)(['cons', [1, K(['nil', []])]])
    print stm
    print stm[1]
    print stm[1][1]()

# Continuation passing monad

## Another monoidal functor
##   continuation passing is a double negation by the Curry-Howard
## isomorphism

## CP A : (A -> Z) -> Z
def cp(c):
    return hom(hom(c, id), id)

def cpLift(x):
    return lambda k: k(x)

## Quadruple negation to double negation
def cpFlatten(cpCpX): # (((A -> Z) -> Z) -> Z) -> Z
    # k : X -> Z
    return lambda k: cpCpX(lambda l: l(k))

cpMonad = monad(cp, cpLift, cpFlatten)

def cpChi(k):
    return \
        (lambda l:
            lambda m:
                l(lambda c: k(lambda d: m(d(c)))))

def cpPhi(cpProd):
    prod = None
    def assign(p):
        prod = list_t(p)
    cpProd(assign)
    return map(cpLift, prod)

# Algebras and control flow

## An algebra for a functor F is a contract c together with a guarded function passing hom(F(c), c)

def algebra(F):
    def curry(c):
        return hom(F(c), c)
    return curry

def maybe_alg_f(mint):
    if mint[0] == 'none':
        return 0
    else:
        return mint[1]

maybe_alg = algebra(maybe_c)(int_t)(maybe_alg_f)

def maybe_alg_test():
    print maybe_alg(['some', 78])
    print maybe_alg(['none', {}])

def getOrElse(default):
    def maybe_alg_f(mint):
        if mint[0] == 'none':
            return default
        else:
            return mint[1]
    return hom(maybe_c(int_t), int_t)(maybe_alg_f)

def getOrElseTest():
    print getOrElse(15)(['some', 78])
    print getOrElse(15)(['none', {}])

def list_c(c):
    return coprods({
        'nil': prods({}),
        'cons': prodn([
            c,
            lambda tail: list_c(c)(tail)
        ])
    })

list_alg = algebra(list_c)

def list_alg_sum_f(lint):
    if lint[0] == 'nil':
        return 1
    else:
        return lint[1][0] * list_alg_sum_f(lint[1][1])

list_alg_sum = hom(list_c(int_t), int_t)(list_alg_sum_f)

def list_alg_sum_test():
    x = ['cons', [5, ['cons', [6, ['nil', {}]]]]]
    print list_alg_sum(x)

def list_alg_monoid(m):
    def alg(lm):
        if lm[0] == 'nil':
            return m['1']()
        else:
            return m['*'](lm[1][0], alg(lm[1][1]))
    return hom(list_c(m['t']), m['t'])(alg)

def list_alg_monoid_test():
    l = ['cons', [5, ['cons', [6, ['nil', {}]]]]]
    print list_alg_monoid(addMonoid)(l)
    print list_alg_monoid(mulMonoid)(l)



def tree(c):
    def subtree(branch):
        return tree(c)(branch)
    return coprods({
        'leaf': c,
        'node': prodn([subtree, subtree])
    })

tree_alg = algebra(tree)

def tree_alg_monoid(m):
    def alg(tm):
        if tm[0] == 'leaf':
            return tm[1]
        else:
            return m['*'](alg(tm[1][0]), alg(tm[1][1]))
    return tree_alg(m['t'])(alg)

def tree_algebra_monoid_test():
    t = ['node', [ ['leaf', 3], ['leaf', 4]]]
    print tree_alg_monoid(addMonoid)(t)
    print tree_alg_monoid(mulMonoid)(t)

## NOTE 'for' loops are algebras on Natural numbers as Natural number is a coproduct 1 -> N <- N
## NOTE idea 'while' loops are related to co-natural numbers, composing a stream basically

def main():
    maybe_test()
    listOfFlatten_test()
    maybeFlatten_test()
    maybe_monad_test()
    prodn_test()
    prods_test()
    coprodn_test()
    coprods_test()
    maybe_c_test()
    hom_test()
    str_monoid_test()
    listMonad_test()
    leq_test()
    div_test()
    list_d_test()
    stream_test()
    prod_test()
    maybe_alg_test()
    getOrElseTest()
    list_alg_sum_test()
    list_alg_monoid_test()
    tree_algebra_monoid_test()

if __name__ == "__main__":
    main()
