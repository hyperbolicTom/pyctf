#include <Python.h>
#include <arrayobject.h>

int interior(double, double, int, double *, double *);
double interpolate(double, double, double *, double *, int);

/* Coefficients for the spline. */

static double *PQ = NULL;

static char Doc_setPQ[] =
"setPQ(PQ) saves the spline coefficients for interpolate().";

static PyObject *setPQ_wrap(PyObject *self, PyObject *args)
{
    int i, n;
    double x, *xp;
    PyObject *xo;
    PyArrayObject *xa;

    if (!PyArg_ParseTuple(args, "O", &xo)) {
        return NULL;
    }

    xa = (PyArrayObject *)PyArray_ContiguousFromAny(xo, NPY_DOUBLE, 1, 1);
    if (xa == NULL || PyArray_NDIM(xa) != 1) {
        goto fail;
    }

    n = PyArray_DIM(xa, 0);

    if (PQ) free(PQ);
    PQ = (double *)malloc(sizeof(double) * n);

    xp = (double *)PyArray_DATA(xa);
    for (i = 0; i < n; i++) {
        PQ[i] = *xp++;
    }

    Py_DECREF(xa);
    Py_INCREF(Py_None);
    return Py_None;
fail:
    Py_XDECREF(xa);
    return NULL;
}

static char Doc_interior[] =
"interior(x, y, X, Y) returns true if (x, y) is inside the boundary\n\
defined by the X and Y vectors (last point must equal first point).";

static PyObject *interior_wrap(PyObject *self, PyObject *args)
{
    int i, n;
    double x, y;
    PyObject *xo, *yo, *ro;
    PyArrayObject *xa, *ya;

    if (!PyArg_ParseTuple(args, "ddOO", &x, &y, &xo, &yo)) {
        return NULL;
    }

    xa = ya = NULL;

    xa = (PyArrayObject *)PyArray_ContiguousFromAny(xo, NPY_DOUBLE, 1, 1);
    if (xa == NULL || PyArray_NDIM(xa) != 1) {
        goto fail;
    }
    ya = (PyArrayObject *)PyArray_ContiguousFromAny(yo, NPY_DOUBLE, 1, 1);
    if (ya == NULL || PyArray_NDIM(ya) != 1) {
        goto fail;
    }

    n = PyArray_DIM(xa, 0);
    if (PyArray_DIM(ya, 0) != n) {
        goto fail;
    }

    i = interior(x, y, n, (double *)PyArray_DATA(xa), (double *)PyArray_DATA(ya));

    Py_DECREF(xa);
    Py_DECREF(ya);
    if (i) {
        ro = Py_True;
    } else {
        ro = Py_False;
    }
    Py_INCREF(ro);
    return ro;
fail:
    Py_XDECREF(xa);
    Py_XDECREF(ya);
    return NULL;
}

#define bMIN(x, y) (x < y ? x : y)
#define bMAX(x, y) (x > y ? x : y)

/* Is a given point in the interior of the boundary? */

int interior(double x, double y, int n, double *X, double *Y)
{
    int p1, p2, counter;
    double xinters;

    /* Scan the boundary list. */

    p1 = 0;
    p2 = 1;
    counter = 0;
    while (p2 < n) {
        if (y >  bMIN(Y[p1], Y[p2]) &&
            y <= bMAX(Y[p1], Y[p2]) &&
            x <= bMAX(X[p1], X[p2]) &&
            Y[p1] != Y[p2]) {
            xinters = (y - Y[p1]) * (X[p2] - X[p1]) / (Y[p2] - Y[p1]) + X[p1];
            if (X[p1] == X[p2] || x <= xinters) {
                counter++;
            }
        }
        p1++;
        p2++;
    }

    return counter & 1;
}

static char Doc_interpolate[] =
"interpolate(x, y, X, Y) returns an interpolated value at (x, y) for\n\
the spline created by make_spline(), which must have been called.";

static PyObject *interpolate_wrap(PyObject *self, PyObject *args)
{
    int n;
    double x, y, v;
    PyObject *xo, *yo;
    PyArrayObject *xa, *ya;

    if (!PyArg_ParseTuple(args, "ddOO", &x, &y, &xo, &yo)) {
        return NULL;
    }

    xa = ya = NULL;

    xa = (PyArrayObject *)PyArray_ContiguousFromAny(xo, NPY_DOUBLE, 1, 1);
    if (xa == NULL || PyArray_NDIM(xa) != 1) {
        goto fail;
    }
    ya = (PyArrayObject *)PyArray_ContiguousFromAny(yo, NPY_DOUBLE, 1, 1);
    if (ya == NULL || PyArray_NDIM(ya) != 1) {
        goto fail;
    }

    n = PyArray_DIM(xa, 0);
    if (PyArray_DIM(ya, 0) != n) {
        goto fail;
    }

    v = interpolate(x, y, (double *)PyArray_DATA(xa), (double *)PyArray_DATA(ya), n);

    Py_DECREF(xa);
    Py_DECREF(ya);

    return Py_BuildValue("d", v);
fail:
    Py_XDECREF(xa);
    Py_XDECREF(ya);
    return NULL;
}

/* Basis function for the spline. */

static double k(double s, double t)
{
    double x;

    x = s * s + t * t;
    if (x < 1e-6) {
        return 0.;
    }
//    return x * x * log10(x);
    return x * log(x);
}

/* Interpolate. */

double interpolate(double x, double y, double *X, double *Y, int n)
{
    int i;
    double u;

    u = 0.;
    for (i = 0; i < n; i++) {
        u += PQ[i] * k(x - X[i], y - Y[i]);
    }
    u += PQ[n];
    u += PQ[n+1] * x;
    u += PQ[n+2] * y;
    u += PQ[n+3] * x * x;
    u += PQ[n+4] * x * y;
    u += PQ[n+5] * y * y;

    return u;
}

static char Doc_spline[] =
"Functions in this module are used to create 2D spline\n\
topographs of MEG data; see fieldspline.py and sensortopo.py.";

static PyMethodDef Methods[] = {
    { "setPQ", setPQ_wrap, METH_VARARGS, Doc_setPQ },
    { "interior", interior_wrap, METH_VARARGS, Doc_interior },
    { "interpolate", interpolate_wrap, METH_VARARGS, Doc_interpolate },
    { NULL, NULL, 0, NULL }
};

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_fieldspline",
    Doc_spline,
    -1,
    Methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit__fieldspline(void)
{
    PyObject *m;

    m = PyModule_Create(&moduledef);
    if (m == NULL) {
        return NULL;
    }

    import_array();

    return m;
}

#else

void init_fieldspline()
{
    Py_InitModule3("_fieldspline", Methods, Doc_spline);
    import_array();
}

#endif
