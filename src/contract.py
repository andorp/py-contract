
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
    def apply(args):
        dict_t(args)
        result = {}
        for k in cs:
            result[k] = cs[k](args[k])
        return result
    return apply

def prods_test():
    int_str_t = prods({'i': int_t, 's': string_t})
    x = int_str_t({'i': 5, 's': "hello"})
    print x

def main():
    maybe_test()
    listOfFlatten_test()
    maybeFlatten_test()
    maybe_monad_test()
    prodn_test()
    prods_test()

if __name__ == "__main__":
    main()
