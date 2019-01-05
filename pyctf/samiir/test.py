from samiir import *

print("make")
f = mkiir(10, 20, 600)
print("dofilt")
x = dofilt(range(1000), f)
print("del")
del x

print("make")
f = mkfft(10, 20, 600, 1000)
print("dofilt")
x = dofilt(range(1000), f)
print("del")
del x

