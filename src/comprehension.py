
from contract import listMonad
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

def main():
    f()

if __name__ == "__main__":
    main()