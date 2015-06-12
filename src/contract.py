
""" A contract consits of a type check of a given variable """

import array

# Object of a contract category
def type_of(t):
    def check(x):
        if not isinstance(x, t):
            raise TypeError('{type} is expected found {found}'.format(type=t, found=type(x)))
        return x
    return check

def any_t(x):
    return x

string_t = type_of(str)
unicode_t = type_of(unicode)
bool_t = type_of(bool)
int_t = type_of(int)
object_t = type_of(object)

array_t = type_of(array.array)
list_t = type_of(list)
dict_t = type_of(dict)

# Example of a morphism, a guarded function, expects a guarded input and
# returns a guarded output
def inc(x):
    x = int_t(x)
    return int_t(x + 1)

# List functor acting on contract, if we have a morhishm as a guarded
# function, as the guarded function checks the input type of its elements
# It produces new objects and new morhisms
def list_of(c):
    def fmap(l):
        return map(c,list_t(l))
    return fmap

# Free pointed set in category theory, Maybe in Haskell, Option in Scala
class Maybe:
    def getOrElse(self, x):
        if isinstance(self, Just):
            return self.x
        else:
            return x

class Nothing(Maybe):
    def __str__(self): return "Nothing"

class Just(Maybe):
    def __init__(self, x): self.x = x
    def __str__(self): return "(Just {x})".format(x=str(self.x))

nothing = Nothing()
just = lambda x: Just(x)

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

def main():
    print maybe(repeat)(nothing)
    print maybe(repeat)(just("Joe")).getOrElse("Jane")
    print maybe(repeat)(nothing).getOrElse("Jane")

if __name__ == "__main__":
    main()
