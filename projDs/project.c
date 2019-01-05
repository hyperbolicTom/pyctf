#include <Python.h>
#include <arrayobject.h>

static char Doc[] =
    "Simple module to help accelerate dot products using threads.";

static char Doc_projectHD[] =
    "r = projectHD(h, D) --- h is a vector, D is a list of matrices.\n\
The result is a 2d array containing h dotted with each matrix in D as rows.";

static PyObject *projectHD_wrap(PyObject *self, PyObject *args)
{
    int i, j, k, m, n, nD, nsamp, stride;
    double s, *rp, *hp, *a;
    npy_intp dim[2];
    PyObject *oh, *oD, *od;
    PyArrayObject *h, **d, *r;

    if (!PyArg_ParseTuple(args, "OO", &oh, &oD)) {
        return NULL;
    }

    h = (PyArrayObject *)PyArray_ContiguousFromAny(oh, NPY_DOUBLE, 1, 1);
    if (h == NULL) {
        return NULL;
    }
    n = PyArray_DIM(h, 0);
    hp = PyArray_DATA(h);

    if (!PyList_Check(oD)) {
        Py_DECREF(h);
        return NULL;
    }
    nD = PyList_GET_SIZE(oD);

    d = (PyArrayObject **)malloc(sizeof(PyArrayObject *) * nD);
    if (d == NULL) {
        Py_DECREF(h);
        return NULL;
    }
    for (i = 0; i < nD; i++) {
        od = PyList_GetItem(oD, i);
        d[i] = (PyArrayObject *)PyArray_ContiguousFromAny(od, NPY_DOUBLE, 2, 2);
    }

    nsamp = PyArray_DIM(d[0], 1);

    dim[0] = nD;
    dim[1] = nsamp;
    r = (PyArrayObject *)PyArray_SimpleNew(2, dim, NPY_DOUBLE);
    if (r == NULL) {
        goto done;
    }
    rp = (double *)PyArray_DATA(r);

    Py_BEGIN_ALLOW_THREADS

    for (i = 0; i < nD; i++) {
        a = PyArray_DATA(d[i]);
        stride = PyArray_STRIDE(d[i], 0) / sizeof(double);

        for (j = 0; j < nsamp; j++) {
            m = j;
            s = 0.;
            for (k = 0; k < n; k++) {
                s += hp[k] * a[m];
                m += stride;
            }
            *rp++ = s;
        }
    }

    Py_END_ALLOW_THREADS

done:
    for (i = 0; i < nD; i++) {
        Py_DECREF(d[i]);
    }
    free(d);
    Py_DECREF(h);
    if (r == NULL) {
        return NULL;
    }
    return PyArray_Return(r);
}

static PyMethodDef Methods[] = {
    { "projectHD", projectHD_wrap, METH_VARARGS, Doc_projectHD },
    { NULL, NULL, 0, NULL }
};

#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "project",
    Doc,
    -1,
    Methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit_project(void)
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

PyMODINIT_FUNC initproject(void)
{
    Py_InitModule3("project", Methods, Doc);
    import_array();
}

#endif
