#import "SemanticBridge.h"
#import <NaturalLanguage/NaturalLanguage.h>

static NLEmbedding *FrenchEmbedding(void) {
    static NLEmbedding *embedding;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ embedding = [NLEmbedding sentenceEmbeddingForLanguage:NLLanguageFrench]; });
    return embedding;
}
static PyObject *Available(PyObject *self, PyObject *args) {
    return PyBool_FromLong(FrenchEmbedding() != nil);
}
static PyObject *Revision(PyObject *self, PyObject *args) {
    if (!FrenchEmbedding()) Py_RETURN_NONE;
    return PyLong_FromUnsignedLong(FrenchEmbedding().revision);
}
static PyObject *Vector(PyObject *self, PyObject *args) {
    const char *value;
    if (!PyArg_ParseTuple(args, "s", &value)) return NULL;
    @autoreleasepool {
        NSArray<NSNumber *> *vector = [FrenchEmbedding() vectorForString:[NSString stringWithUTF8String:value]];
        if (!vector) Py_RETURN_NONE;
        PyObject *result = PyList_New(vector.count);
        if (!result) return NULL;
        for (NSUInteger index = 0; index < vector.count; index++) {
            PyObject *number = PyFloat_FromDouble(vector[index].doubleValue);
            if (!number) { Py_DECREF(result); return NULL; }
            PyList_SET_ITEM(result, index, number);
        }
        return result;
    }
}
static PyMethodDef Methods[] = {
    {"available", Available, METH_NOARGS, "Empreintes de phrases françaises installées."},
    {"revision", Revision, METH_NOARGS, "Révision des empreintes installées."},
    {"vector", Vector, METH_VARARGS, "Vecteur local, sans téléchargement de modèle."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef Definition = { PyModuleDef_HEAD_INIT, "_rc_semantics", NULL, -1, Methods };
PyMODINIT_FUNC PyInit__rc_semantics(void) { return PyModule_Create(&Definition); }
