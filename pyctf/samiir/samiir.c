/* SAM filtering wrapper code. */

#include <Python.h>
#include <arrayobject.h>
#include "filters.h"

#define SIG_ORDER 4

typedef struct {
    int type;
    IIRSPEC iirspec;            // used for type IIR
    double *gain;               // used for type FFT
    int n;                      // length of gain array
} FILTER;

#define FILTER_TYPE_IIR 1
#define FILTER_TYPE_FFT 2

#if PY_MAJOR_VERSION >= 3
static void free_filter(PyObject *filter)
{
    FILTER *f = (FILTER *)PyCapsule_GetPointer(filter, NULL);
#else
static void free_filter(void *filter)
{
    FILTER *f = (FILTER *)filter;
#endif

    if (f->type == FILTER_TYPE_FFT) {
        free(f->gain);
    }
    free(f);
}

static char Doc_mkiir[] =
"filter = mkiir(lo, hi, srate) returns filter parameters (an opaque object)\n\
for an IIR filter with the specified parameters. lo, hi, and srate are all\n\
in Hz. If hi is 0, make a high-pass filter at lo Hz. If lo is 0, make a\n\
low-pass filter at hi Hz. If 0 < lo < hi, make a band-pass filter from lo\n\
to hi Hz, and if 0 < hi < lo, make a band-reject filter.";

static PyObject *mkiir_wrap(PyObject *self, PyObject *args)
{
    double lo, hi, srate;
    double bw, bwfreq, freq, h1, gain;
    PyObject *o;
    FILTER *handle;
    IIRSPEC *filter;

    if (!PyArg_ParseTuple(args, "ddd:mkiir", &lo, &hi, &srate)) {
        return NULL;
    }

    handle = (FILTER *)malloc(sizeof(FILTER));
    handle->type = FILTER_TYPE_IIR;
    filter = &handle->iirspec;
    filter->enable = 1;
    filter->rate = srate;

    if (hi > 0. && lo > 0. && lo < hi) {
        filter->type = BANDPASS;
        filter->order = SIG_ORDER;
        filter->fl = lo;
        filter->fh = hi;
    } else if (hi > 0. && lo > 0. && lo > hi) {
        filter->type = BANDREJECT;
        filter->order = SIG_ORDER;
        filter->fl = hi;
        filter->fh = lo;
    } else if (lo > 0. && hi == 0.) {
        filter->type = HIGHPASS;
        filter->order = 2 * SIG_ORDER;
        filter->fl = lo;
        filter->fh = srate / 2.;
    } else if (lo == 0. && hi > 0.) {
        filter->type = LOWPASS;
        filter->order = 2 * SIG_ORDER;
        filter->fl = 0;
        filter->fh = hi;
    }
    bw = filter->fh - filter->fl;

    // compute filter coefficients
    if (mkiir(filter) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "mkiir() failed");
        free(handle);
        return NULL;
    }

    // compute effective bandwidth of data filter in steps of 1 milliHz
    for (freq = bwfreq = 0.; freq < srate / 4.; freq += 0.001) {
        h1 = response(filter, srate, freq);
        if (h1 > M_SQRT2) {
            PyErr_SetString(PyExc_RuntimeError, "mkiir() failed: IIR filter is unstable for this sample rate");
            free(handle);
            return NULL;
        }
        bwfreq += 0.001 * (h1 * h1);
    }

    // test filter for low gain
    gain = bwfreq / bw;
    if (gain < M_SQRT1_2) {
        fprintf(stderr, "nominal filter bandwidth=%f\n", bwfreq);
        PyErr_SetString(PyExc_RuntimeError, "IIR filter gain too low");
        free(handle);
        return NULL;
    }

#if PY_MAJOR_VERSION >= 3
    o = PyCapsule_New(handle, NULL, free_filter);
#else
    o = PyCObject_FromVoidPtr(handle, free_filter);
#endif
    return o;
}

static char Doc_mkfft[] =
"filter = mkfft(lo, hi, srate, N) returns filter parameters (an opaque object)\n\
for an N-point FFT filter with the specified parameters. lo, hi, and srate are\n\
all in Hz. If hi is 0, make a high-pass filter at lo Hz. If lo is 0, make a\n\
low-pass filter at hi Hz. If 0 < lo < hi, make a band-pass filter from lo\n\
to hi Hz, and if 0 < hi < lo, make a band-reject filter.";

static PyObject *mkfft_wrap(PyObject *self, PyObject *args)
{
    int type, len;
    double lo, hi, srate, bwfreq, t;
    PyObject *o;
    FILTER *handle;
    double *filter;

    if (!PyArg_ParseTuple(args, "dddi:mkfft", &lo, &hi, &srate, &len)) {
        return NULL;
    }

    handle = (FILTER *)malloc(sizeof(FILTER));
    handle->type = FILTER_TYPE_FFT;
    if ((filter = (double *)malloc(len * sizeof(double))) == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "malloc() failed");
        return NULL;
    }
    handle->gain = filter;
    handle->n = len;

    if (hi > 0. && lo > 0. && lo < hi) {
        type = BANDPASS;
    } else if (hi > 0. && lo > 0. && lo > hi) {
        type = BANDREJECT;
        t = lo;
        lo = hi;
        hi = t;
    } else if (lo > 0. && hi == 0.) {
        type = HIGHPASS;
    } else if (lo == 0. && hi > 0.) {
        type = LOWPASS;
    }
    Butterworth(handle->gain, len, lo, hi, srate, type, MAXORDER, &bwfreq);

#if PY_MAJOR_VERSION >= 3
    o = PyCapsule_New(handle, NULL, free_filter);
#else
    o = PyCObject_FromVoidPtr(handle, free_filter);
#endif
    return o;
}

static char Doc_dofilt[] =
"out = dofilt(in, filter) returns a filtered version of the array in.\n\
filter should be the opaque object returned by mkiir() or mkfft().";

static PyObject *dofilt_wrap(PyObject *self, PyObject *args)
{
    int n;
    npy_intp dim[1];
    PyObject *ao, *fo;
    PyArrayObject *a, *r;
    FILTER *handle;
    IIRSPEC *filter;

    if (!PyArg_ParseTuple(args, "OO:dofilt", &ao, &fo)) {
        return NULL;
    }

#if PY_MAJOR_VERSION >= 3
    if (!PyCapsule_CheckExact(fo)) {
#else
    if (!PyCObject_Check(fo)) {
#endif
        PyErr_SetString(PyExc_TypeError, "second argument must be a filter object");
        return NULL;
    }
#if PY_MAJOR_VERSION >= 3
    handle = (FILTER *)PyCapsule_GetPointer(fo, NULL);
#else
    handle = (FILTER *)PyCObject_AsVoidPtr(fo);
#endif

    a = (PyArrayObject *)PyArray_ContiguousFromAny(ao, NPY_DOUBLE, 1, 1);
    if (a == NULL) {
        return NULL;
    }
    n = PyArray_DIM(a, 0);

    dim[0] = n;
    r = (PyArrayObject *)PyArray_SimpleNew(1, dim, NPY_DOUBLE);
    if (r == NULL) {
        Py_DECREF(a);
        return NULL;
    }

    if (handle->type == FILTER_TYPE_IIR) {
        filter = (IIRSPEC *)&handle->iirspec;
        if (bdiir((double *)PyArray_DATA(a), (double *)PyArray_DATA(r), n, filter) < 0) {
            PyErr_SetString(PyExc_RuntimeError, "bdiir() failed");  // because it allocates memory,
            Py_DECREF(a);                                           // which it shouldn't
            Py_DECREF(r);
            return NULL;
        }
    } else {
        // sanity check -- len must match filter
        if (n != handle->n) {
            PyErr_SetString(PyExc_RuntimeError, "filter length mismatch");
            Py_DECREF(a);
            Py_DECREF(r);
            return NULL;
        }
        FFTfilter((double *)PyArray_DATA(a), (double *)PyArray_DATA(r), handle->gain, n);
    }

    Py_DECREF(a);
    return PyArray_Return(r);
}

static char Doc_getiir[] =
"num, den = getiir(filter) returns the filter coefficients.\n";

static PyObject *getiir_wrap(PyObject *self, PyObject *args)
{
    int i, j;
    char *errs;
    double *x, *y;
    npy_intp dim[1];
    PyObject *fo, *tup;
    PyArrayObject *a, *b;
    FILTER *handle;
    IIRSPEC *filter;

    if (!PyArg_ParseTuple(args, "O:getiir", &fo)) {
        return NULL;
    }

    errs = "argument must be a filter object from mkiir()";
#if PY_MAJOR_VERSION >= 3
    if (!PyCapsule_CheckExact(fo)) {
#else
    if (!PyCObject_Check(fo)) {
#endif
        PyErr_SetString(PyExc_TypeError, errs);
        return NULL;
    }
#if PY_MAJOR_VERSION >= 3
    handle = (FILTER *)PyCapsule_GetPointer(fo, NULL);
#else
    handle = (FILTER *)PyCObject_AsVoidPtr(fo);
#endif
    if (handle->type != FILTER_TYPE_IIR) {
        PyErr_SetString(PyExc_TypeError, errs);
        return NULL;
    }
    filter = &handle->iirspec;

    // create return arrays

    dim[0] = filter->NC;
    a = (PyArrayObject *)PyArray_SimpleNew(1, dim, NPY_DOUBLE);
    if (a == NULL) {
        return NULL;
    }
    b = (PyArrayObject *)PyArray_SimpleNew(1, dim, NPY_DOUBLE);
    if (b == NULL) {
        Py_DECREF(a);
        return NULL;
    }

    // fill them in in reverse order

    x = (double *)PyArray_DATA(a);
    y = (double *)PyArray_DATA(b);
    for (i = filter->NC - 1, j = 0; i >= 0; i--, j++) {
        x[j] = filter->num[i];
        y[j] = filter->den[i];
    }

    // return a pair of arrays

    tup = PyTuple_New(2);
    PyTuple_SetItem(tup, 0, (PyObject *)a);
    PyTuple_SetItem(tup, 1, (PyObject *)b);
    return tup;
}

static char Doc_getfft[] =
"gain = getfft(filter) returns the FFT filter gains.\n";

static PyObject *getfft_wrap(PyObject *self, PyObject *args)
{
    int i;
    char *errs;
    double *x;
    npy_intp dim[1];
    PyObject *fo;
    PyArrayObject *a;
    FILTER *handle;
    double *gain;

    if (!PyArg_ParseTuple(args, "O:getfft", &fo)) {
        return NULL;
    }

    errs = "argument must be a filter object from mkfft()";
#if PY_MAJOR_VERSION >= 3
    if (!PyCapsule_CheckExact(fo)) {
#else
    if (!PyCObject_Check(fo)) {
#endif
        PyErr_SetString(PyExc_TypeError, errs);
        return NULL;
    }
#if PY_MAJOR_VERSION >= 3
    handle = (FILTER *)PyCapsule_GetPointer(fo, NULL);
#else
    handle = (FILTER *)PyCObject_AsVoidPtr(fo);
#endif
    if (handle->type != FILTER_TYPE_FFT) {
        PyErr_SetString(PyExc_TypeError, errs);
        return NULL;
    }
    gain = handle->gain;

    // create return array

    dim[0] = handle->n;
    a = (PyArrayObject *)PyArray_SimpleNew(1, dim, NPY_DOUBLE);
    if (a == NULL) {
        return NULL;
    }

    // fill it

    x = (double *)PyArray_DATA(a);
    for (i = 0; i < handle->n; i++) {
        x[i] = gain[i];
    }

    // return the array

    return PyArray_Return(a);
}

static char Doc_samiir[] =
"Time-series filters. First call either mkfft() or mkiir() to create\n\
an FFT-based filter or an IIR filter respectively, then use dofilt()\n\
to filter a 1D array of data.";

static PyMethodDef Methods[] = {
    { "mkiir", mkiir_wrap, METH_VARARGS, Doc_mkiir },
    { "mkfft", mkfft_wrap, METH_VARARGS, Doc_mkfft },
    { "dofilt", dofilt_wrap, METH_VARARGS, Doc_dofilt },
    { "getiir", getiir_wrap, METH_VARARGS, Doc_getiir },
    { "getfft", getfft_wrap, METH_VARARGS, Doc_getfft },
    { NULL, NULL, 0, NULL }
};

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "samiir",
    Doc_samiir,
    -1,
    Methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit_samiir(void)
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

PyMODINIT_FUNC initsamiir(void)
{
    Py_InitModule3("samiir", Methods, Doc_samiir);
    import_array();
}

#endif
