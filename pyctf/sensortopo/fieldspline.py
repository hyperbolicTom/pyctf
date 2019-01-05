"Create and interpolate a 2D spline."

from numpy import *
from ._fieldspline import setPQ, interior, interpolate

def k(s, t):
    "basis function for the spline"
    x = s * s + t * t
    x = where(x < 1e-6, 1., x)
    return x * log(x)

def quadterms(x, y):
    "polynomial terms up to order 2"
    return array([1., x, y, x * x, x * y, y * y])

"""
def interpolate(x, y, X, Y):
    "apply the spline coefficients at a point"
    u = dot(P, k(x - X, y - Y))
    u += dot(Q, quadterms(x, y))
    return u
"""

def make_spline(x, y, z):
    "create the spline"

    # global P, Q

    m = len(x)
    if len(y) != m or len(z) != m:
        raise AssertionError('incompatible dimensions in make_spline')
    n = m + 6

    # coeffs are solution x to ax = b where b is z + 6 zeros,
    # a has an upper left block of k() terms, and quadterms
    # in the right and bottom bands.
    a = zeros((n, n))
    b = zeros((n,))
    b[0:m] = z
    for i in range(m):
        a[i,0:m] = k(x[i] - x, y[i] - y)
        a[i,m:n] = quadterms(x[i], y[i])
        a[m:n,i] = a[i,m:n]
    PQ = linalg.solve(a, b)

    # save the coeffs
    #P = PQ[0:m]
    #Q = PQ[m:n]
    setPQ(PQ)
