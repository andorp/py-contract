
""" A contract consits of a type check of a given variable """

import array

# Category consists of
# - contract as an object
# - morphism as a guarded functions

# A contract that checks the parameter for a given type
def type_of(t):
    def contract(x):
        if not isinstance(x, t):
            raise TypeError('{type} is expected found {found}'.format(type=t, found=type(x)))
        return x
    return contract

# A special contract that does not checks the type of the
# parameter.
def any_t(x):
    return x

# A guarded function, expects a guarded input and returns a guarded output
def inc(x):
    x = int_t(x)
    return int_t(x + 1)


string_t = type_of(str)
unicode_t = type_of(unicode)
bool_t = type_of(bool)
int_t = type_of(int)
object_t = type_of(object)

array_t = type_of(array.array)
list_t = type_of(list)
dict_t = type_of(dict)

# List functor acting on contract, if we have a morhishm as a guarded
# function, as the guarded function checks the input type of its elements
# It produces new objects and new morhisms
def list_of(c):
    def fmap(l):
        return map(c,list_t(l))
    return fmap

# Maybe

# Free pointed set in category theory, Maybe in Haskell, Option in Scala
class Maybe:
    def getOrElse(self, x):
        if isinstance(self, Just):
            return self.x
        else:
            return x

    def flatten(self):
        return maybeFlatten(any_t)(self)

class Nothing(Maybe):
    def __str__(self): return "Nothing"

class Just(Maybe):
    def __init__(self, x): self.x = x
    def __str__(self): return "(Just {x})".format(x=str(self.x))

nothing = Nothing()
just = lambda x: Just(x)

# Maybe functor

# Functor based on the Maybe data
def maybe(c):
    def fmap(m):
        if isinstance(m, Just):
            return Just(c(m.x))
        elif isinstance(m, Nothing):
            return m
        else:
            raise TypeError('Expected Nothing or Just(value)')
    return fmap

# One other morphism between contracts(object in our category)
def repeat(s):
    s = string_t(s)
    return string_t(s + s)

## Unit and flatten

def listOfUnit(c):
    def wrap(x):
        x = c(x)
        return list_of(c)([x])
    return wrap

def maybeUnit(c):
    def wrap(x):
        x = c(x)
        return maybe(c)(some(x))
    return wrap

def listOfFlatten(c):
    def flatten(llx):
        llx = list_of(list_of(c))(llx) # [[1], [1,4]]
        result = []
        for xs in llx:
            result = result + xs
        return list_of(c)(result)
    return flatten

def maybeFlatten(c):
    def flatten(mmx):
        mmx = maybe(maybe(c))(mmx)
        result = mmx
        if isinstance(mmx, Just):
            result = result.x
        return result
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

def noTimes(functor):
    def apply(c):
        return c
    return apply

def main():
    maybe_test()
    listOfFlatten_test()
    maybeFlatten_test()

if __name__ == "__main__":
    main()
