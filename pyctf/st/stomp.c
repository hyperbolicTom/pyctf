#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <fftw3.h>
#include <arrayobject.h>
#include <omp.h>

/* This is the Fourier Transform of a Gaussian. */

static double gauss(int n, int m)
{
    return exp(-2. * M_PI * M_PI * m * m / (n * n));
}

/* Stockwell transform of the real array data. The len argument is the
number of time points, and it need not be a power of two. The lo and hi
arguments specify the range of frequencies to return, in Hz. If they are
both zero, they default to lo = 0 and hi = len / 2. The result is
returned in the complex array result, which must be preallocated, with
n rows and len columns, where n is hi - lo + 1. For the default values of
lo and hi, n is len / 2 + 1. */

static void st(int len, int lo, int hi, double *data, double *result)
{
        fftw_plan p1, p2;
        fftw_complex *H;
#pragma omp parallel shared(p2, H)
    {
        int a, i, k, n, l2, tid;
        double s, *p;
        double *g;
        fftw_complex *h, *G;

        tid = omp_get_thread_num();

#pragma omp critical
    {
        h = fftw_malloc(sizeof(fftw_complex) * len);
        G = fftw_malloc(sizeof(fftw_complex) * len);
        g = (double *)malloc(sizeof(double) * len);
    }

        /* Set up the fftw plans. */

#pragma omp master
    {
        H = fftw_malloc(sizeof(fftw_complex) * len);

        p1 = fftw_plan_dft_1d(len, h, H, FFTW_FORWARD, FFTW_MEASURE);
        p2 = fftw_plan_dft_1d(len, G, h, FFTW_BACKWARD, FFTW_MEASURE);

        /* Convert the input to complex. Also compute the mean. */

        s = 0.;
        memset(h, 0, sizeof(fftw_complex) * len);
        for (i = 0; i < len; i++) {
            h[i][0] = data[i];
            s += data[i];
        }
        s /= len;

        /* FFT. */

        fftw_execute(p1); /* h -> H */

        /* Hilbert transform. The upper half-circle gets multiplied by
        two, and the lower half-circle gets set to zero.  The real axis
        is left alone. */

        l2 = (len + 1) / 2;
        for (i = 1; i < l2; i++) {
            H[i][0] *= 2.;
            H[i][1] *= 2.;
        }
        l2 = len / 2 + 1;
        for (i = l2; i < len; i++) {
            H[i][0] = 0.;
            H[i][1] = 0.;
        }

        /* Fill in rows of the result.
        The row for lo == 0 contains the mean. */

        if (lo == 0) {
            p = result;
            for (i = 0; i < len; i++) {
                *p++ = s;
                *p++ = 0.;
            }
        }
    }
#pragma omp barrier

        a = lo;
        if (a == 0) {
            a++;
        }

        /* Subsequent rows contain the inverse FFT of the spectrum
        multiplied with the FFT of scaled gaussians. */

#pragma omp for
        for (n = a; n <= hi; n++) {

            /* Scale the FFT of the gaussian. Negative frequencies
            wrap around. */

            g[0] = gauss(n, 0);
            l2 = len / 2 + 1;
            for (i = 1; i < l2; i++) {
                g[i] = g[len - i] = gauss(n, i);
            }

            for (i = 0; i < len; i++) {
                s = g[i];
                k = n + i;
                if (k >= len) k -= len;
                G[i][0] = H[k][0] * s;
                G[i][1] = H[k][1] * s;
            }

            /* Inverse FFT the result to get the next row. */

            fftw_execute_dft(p2, G, h); /* G -> h */

            p = &result[len * 2 * (n - lo)];
            for (i = 0; i < len; i++) {
                *p++ = h[i][0] / len;
                *p++ = h[i][1] / len;
            }
        }

#pragma omp master
    {
        fftw_destroy_plan(p1);
        fftw_destroy_plan(p2);
        fftw_free(H);
    }
#pragma omp critical
    {
        fftw_free(h);
        fftw_free(G);
        free(g);
    }
    }
}

/* Python wrapper code. */

static char Doc_st[] =
"st(x[, lo, hi]) returns the 2d, complex Stockwell transform of the real\n\
array x. If lo and hi are specified, only those frequencies (rows) are\n\
returned; lo and hi default to 0 and n/2, resp., where n is the length of x.";

static PyObject *st_wrap(PyObject *self, PyObject *args)
{
    int n;
    int lo = 0;
    int hi = 0;
    npy_intp dim[2];
    PyObject *o;
    PyArrayObject *a, *r;

    if (!PyArg_ParseTuple(args, "O|ii", &o, &lo, &hi)) {
        return NULL;
    }

    a = (PyArrayObject *)PyArray_ContiguousFromAny(o, NPY_DOUBLE, 1, 1);
    if (a == NULL) {
        return NULL;
    }
    n = PyArray_DIM(a, 0);

    if (lo == 0 && hi == 0) {
        hi = n / 2;
    }

    dim[0] = hi - lo + 1;
    dim[1] = n;
    r = (PyArrayObject *)PyArray_SimpleNew(2, dim, NPY_CDOUBLE);
    if (r == NULL) {
        Py_DECREF(a);
        return NULL;
    }

    st(n, lo, hi, (double *)PyArray_DATA(a), (double *)PyArray_DATA(r));

    Py_DECREF(a);
    return PyArray_Return(r);
}

static char Doc_stomp[] =
"Stockwell transform of 1D time-series data using OpenMP.";

static PyMethodDef Methods[] = {
    { "st", st_wrap, METH_VARARGS, Doc_st },
    { NULL, NULL, 0, NULL }
};

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "stomp",
    Doc_stomp,
    -1,
    Methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit_stomp(void)
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

PyMODINIT_FUNC initstomp()
{
    Py_InitModule3("stomp", Methods, Doc_stomp);
    import_array();
}

#endif
