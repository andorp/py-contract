
from contract import just, nothing, try_ok, try_error
from ast import *
from uncompile import monadic

def l_to_n(n):
    return range(0, n)

@monadic("listMonad")
def f():
    xs = [ y for x in l_to_n(5) 
             for y in l_to_n(x)
         ]
    print xs

def div(x, y):
    if y == 0:
        return nothing
    else:
        return just(x / y)

@monadic("maybeMonad")
def g(z):
    xs = [ y for x in just(4)
             for y in div(x, z)
         ]
    print xs

def try_div(x, y):
    if y == 0:
        return try_error("divisor was zero")
    else:
        return try_ok(x / y)

@monadic("try_monad")
def h(z):
    xs = [ y for x in try_ok(4)
             for y in try_div(x, z)
         ]
    print xs

def main():
    f()
    g(2)
    g(0)
    h(2)
    h(0)

if __name__ == "__main__":
    main()