/*
 * This file is part of python-corosync. Python-corosync is free software
 * that is made available under the MIT license. Consult the file "LICENSE"
 * that is distributed together with this file for the exact licensing terms.
 *
 * Python-corosync is copyright (c) 2008 by the python-corosync authors. See
 * the file "AUTHORS" for a complete overview.
 */

#include <stdlib.h>
#include <string.h>
#include <sys/uio.h>

#include <Python.h>
#include <corosync/cpg.h>


#define RETURN_ON_ERROR(code, function) \
    do if (code != CPG_OK) \
    { \
	PyErr_Format(py_cpg_error, "%s(): returned error %d", function, code); \
	return NULL; \
    } while (0)

#define RETURN_IF_NULL(value) \
    do if (value == NULL) { return NULL; } while (0)

#define RETURN_VOID_IF_NULL(value) \
    do if (value == NULL) { return; } while (0)


/*
 * Global variables
 */

static PyObject *py_cpg_error;

typedef struct
{
    cpg_handle_t handle;
    PyObject *callbacks;
} py_cpg_callbacks_t;

static py_cpg_callbacks_t *py_cpg_callbacks = NULL;
static int py_cpg_nr_callbacks = 0;
static int py_cpg_alloc_callbacks = 0;
static const int py_cpg_start_callbacks = 10;


/*
 * Callback mapping utility functions.
 */

static int
py_cpg_init_callbacks()
{
    py_cpg_callbacks = calloc(py_cpg_start_callbacks,
			      sizeof (py_cpg_callbacks_t));
    if (py_cpg_callbacks == NULL)
    {
	PyErr_NoMemory();
	return -1;
    }
    py_cpg_alloc_callbacks = py_cpg_start_callbacks;
    return 0;
}

static int
py_cpg_add_callbacks(cpg_handle_t handle, PyObject *callbacks)
{
    if (py_cpg_nr_callbacks == py_cpg_alloc_callbacks)
    {
	py_cpg_callbacks = realloc(py_cpg_callbacks, py_cpg_alloc_callbacks * 2
				   * sizeof (py_cpg_callbacks_t));
	if (py_cpg_callbacks == NULL)
	{
	    PyErr_NoMemory();
	    return -1;
	}
	py_cpg_alloc_callbacks *= 2;
    }

    py_cpg_callbacks[py_cpg_nr_callbacks].handle = handle;
    py_cpg_callbacks[py_cpg_nr_callbacks].callbacks = callbacks;
    py_cpg_nr_callbacks += 1;

    return 0;
}

static void
py_cpg_remove_callbacks(cpg_handle_t handle)
{
    int i;

    for (i=0; i<py_cpg_nr_callbacks; i++)
    {
	if (py_cpg_callbacks[i].handle == handle)
	{
	    memmove(py_cpg_callbacks + i, py_cpg_callbacks + i + 1,
		    (py_cpg_nr_callbacks - i) * sizeof (py_cpg_callbacks_t));
	    py_cpg_nr_callbacks -= 1;
	    break;
	}
    }
}

static PyObject *
py_cpg_find_callbacks(cpg_handle_t handle)
{
    int i;

    for (i=0; i<py_cpg_nr_callbacks; i++)
    {
	if (py_cpg_callbacks[i].handle == handle)
	    return py_cpg_callbacks[i].callbacks;
    }
    return NULL;
}


/*
 * OpenAIS callbacks
 */

static void
py_cpg_deliver_fn(cpg_handle_t handle, struct cpg_name *group_name,
		  uint32_t nodeid, uint32_t pid, void *msg, int msg_len)
{
    PyObject *Pcallbacks, *Pname, *Paddr, *Pmessage, *Pmethod, *Pret;

    Pcallbacks = py_cpg_find_callbacks(handle);
    RETURN_VOID_IF_NULL(Pcallbacks);

    Pname = PyString_FromStringAndSize(group_name->value, group_name->length);
    RETURN_VOID_IF_NULL(Pname);

    Paddr = PyTuple_New(3);
    RETURN_VOID_IF_NULL(Paddr);
    PyTuple_SET_ITEM(Paddr, 0, PyInt_FromLong(nodeid));
    PyTuple_SET_ITEM(Paddr, 1, PyInt_FromLong(pid));
    PyTuple_SET_ITEM(Paddr, 2, PyInt_FromLong(0));

    Pmessage = PyString_FromStringAndSize(msg, msg_len);
    RETURN_VOID_IF_NULL(Pmessage);

    Pmethod = PyString_FromString("_deliver_fn");
    RETURN_VOID_IF_NULL(Pmethod);
    
    Pret = PyObject_CallMethodObjArgs(Pcallbacks, Pmethod, Pname, Paddr,
				      Pmessage, NULL);
    if (Pret == NULL)
	return;

    Py_DECREF(Pname);
    Py_DECREF(Paddr);
    Py_DECREF(Pmessage);
    Py_DECREF(Pmethod);
    Py_DECREF(Pret);
}

static void
py_cpg_confchg_fn(cpg_handle_t handle, struct cpg_name *group_name,
		  struct cpg_address *member_list, int member_list_entries,
		  struct cpg_address *left_list, int left_list_entries,
		  struct cpg_address *joined_list, int joined_list_entries)
{
    int i;
    PyObject *Pcallbacks, *Pname, *Pmembers, *Paddr, *Pleft, *Pjoined,
	     *Pmethod, *Pret;

    Pcallbacks = py_cpg_find_callbacks(handle);
    RETURN_VOID_IF_NULL(Pcallbacks);

    Pname = PyString_FromStringAndSize(group_name->value, group_name->length);
    RETURN_VOID_IF_NULL(Pname);

    Pmembers = PyList_New(member_list_entries);
    RETURN_VOID_IF_NULL(Pmembers);
    for (i=0; i<member_list_entries; i++)
    {
	Paddr = PyTuple_New(3);
	RETURN_VOID_IF_NULL(Paddr);
	PyTuple_SET_ITEM(Paddr, 0, PyInt_FromLong(member_list[i].nodeid));
	PyTuple_SET_ITEM(Paddr, 1, PyInt_FromLong(member_list[i].pid));
	PyTuple_SET_ITEM(Paddr, 2, PyInt_FromLong(member_list[i].reason));
	PyList_SET_ITEM(Pmembers, i, Paddr);
    }

    Pleft = PyList_New(left_list_entries);
    RETURN_VOID_IF_NULL(Pleft);
    for (i=0; i<left_list_entries; i++)
    {
	Paddr = PyTuple_New(3);
	RETURN_VOID_IF_NULL(Paddr);
	PyTuple_SET_ITEM(Paddr, 0, PyInt_FromLong(left_list[i].nodeid));
	PyTuple_SET_ITEM(Paddr, 1, PyInt_FromLong(left_list[i].pid));
	PyTuple_SET_ITEM(Paddr, 2, PyInt_FromLong(left_list[i].reason));
	PyList_SET_ITEM(Pleft, i, Paddr);
    }

    Pjoined = PyList_New(joined_list_entries);
    RETURN_VOID_IF_NULL(Pjoined);
    for (i=0; i<joined_list_entries; i++)
    {
	Paddr = PyTuple_New(3);
	RETURN_VOID_IF_NULL(Paddr);
	PyTuple_SET_ITEM(Paddr, 0, PyInt_FromLong(joined_list[i].nodeid));
	PyTuple_SET_ITEM(Paddr, 1, PyInt_FromLong(joined_list[i].pid));
	PyTuple_SET_ITEM(Paddr, 2, PyInt_FromLong(joined_list[i].reason));
	PyList_SET_ITEM(Pjoined, i, Paddr);
    }

    Pmethod = PyString_FromString("_confchg_fn");
    RETURN_VOID_IF_NULL(Pmethod);

    Pret = PyObject_CallMethodObjArgs(Pcallbacks, Pmethod, Pname, Pmembers,
				      Pleft, Pjoined, NULL);
    if (Pret == NULL)
	return;

    Py_DECREF(Pname);
    Py_DECREF(Pmembers);
    Py_DECREF(Pleft);
    Py_DECREF(Pjoined);
    Py_DECREF(Pmethod);
    Py_DECREF(Pret);
}

static void
py_cpg_groups_get_fn(cpg_handle_t handle, uint32_t group_num,
		    uint32_t group_total, struct cpg_name *group_name,
		    struct cpg_address *member_list, int member_list_entries)
{
    /* empty for now */
}

/*
 * Methods
 */

static PyObject *
py_cpg_initialize(PyObject *self, PyObject *args)
{
    int ret;
    cpg_handle_t handle;
    cpg_callbacks_t callbacks;
    PyObject *Phandle, *Pcallbacks;
    
    if (!PyArg_ParseTuple(args, "O", &Pcallbacks))
	return NULL;

    callbacks.cpg_deliver_fn = py_cpg_deliver_fn;
    callbacks.cpg_confchg_fn = py_cpg_confchg_fn;
    callbacks.cpg_groups_get_fn = py_cpg_groups_get_fn;

    ret = cpg_initialize(&handle, &callbacks);
    RETURN_ON_ERROR(ret, "cpg_initialize");

    ret = py_cpg_add_callbacks(handle, Pcallbacks);
    if (ret == -1)
	return NULL;

    Phandle = PyLong_FromLong(handle);
    return Phandle;
}

static PyObject *
py_cpg_finalize(PyObject *self, PyObject *args)
{
    int ret;
    cpg_handle_t handle;

    if (!PyArg_ParseTuple(args, "l", &handle))
	return NULL;

    ret = cpg_finalize(handle);
    RETURN_ON_ERROR(ret, "cpg_finalize");

    py_cpg_remove_callbacks(handle);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
py_cpg_join(PyObject *self, PyObject *args)
{
    char *name;
    int length, ret;
    cpg_handle_t handle;
    struct cpg_name group_name;

    if (!PyArg_ParseTuple(args, "ls#", &handle, &name, &length))
	return NULL;

    if (length > CPG_MAX_NAME_LENGTH)
    {
	PyErr_Format(py_cpg_error, "Group name too long (%d, max length = %d)",
		     length, CPG_MAX_NAME_LENGTH);
	return NULL;
    }
    group_name.length = length;
    memcpy(group_name.value, name, length);
    
    ret = cpg_join(handle, &group_name);
    RETURN_ON_ERROR(ret, "cpg_join");

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
py_cpg_leave(PyObject *self, PyObject *args)
{
    char *name;
    int length, ret;
    cpg_handle_t handle;
    struct cpg_name group_name;

    if (!PyArg_ParseTuple(args, "ls#", &handle, &name, &length))
	return NULL;

    if (length > CPG_MAX_NAME_LENGTH)
    {
	PyErr_Format(py_cpg_error, "Group name too long (%d, max length = %d)",
		     length, CPG_MAX_NAME_LENGTH);
	return NULL;
    }
    group_name.length = length;
    memcpy(group_name.value, name, length);
    
    ret = cpg_leave(handle, &group_name);
    RETURN_ON_ERROR(ret, "cpg_leave");

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
py_cpg_dispatch(PyObject *self, PyObject *args)
{
    int ret;
    cpg_handle_t handle;
    cs_dispatch_flags_t dispatch;

    if (!PyArg_ParseTuple(args, "li", &handle, &dispatch))
	return NULL;

    ret = cpg_dispatch(handle, dispatch);
    RETURN_ON_ERROR(ret, "cpg_dispach");

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
py_cpg_fd_get(PyObject *self, PyObject *args)
{
    int fd, ret;
    cpg_handle_t handle;
    PyObject *Phandle;

    if (!PyArg_ParseTuple(args, "l", &handle))
	return NULL;

    ret = cpg_fd_get(handle, &fd);
    RETURN_ON_ERROR(ret, "cpg_fd_get");

    Phandle = PyInt_FromLong(fd);
    return Phandle;
}

static PyObject *
py_cpg_mcast_joined(PyObject *self, PyObject *args)
{
    int ret;
    void *data;
    size_t length;
    cpg_handle_t handle;
    cpg_guarantee_t guarantee;
    struct iovec iov;

    if (!PyArg_ParseTuple(args, "lis#", &handle, &guarantee, &data, &length))
	return NULL;

    iov.iov_base = data;
    iov.iov_len = length;

    ret = cpg_mcast_joined(handle, guarantee, &iov, 1);
    RETURN_ON_ERROR(ret, "cpg_mcast_joined");

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
py_cpg_membership_get(PyObject *self, PyObject *args)
{
    cpg_handle_t handle;
    struct cpg_name group_name;
    const int maxaddrs = 100;
    int naddrs = maxaddrs, i, ret;
    struct cpg_address addrs[maxaddrs];
    PyObject *Pname, *Paddr, *Paddrs, *Presult;

    if (!PyArg_ParseTuple(args, "l", &handle))
	return NULL;

    ret = cpg_membership_get(handle, &group_name, addrs, &naddrs);
    RETURN_ON_ERROR(ret, "cpg_membership_get");

    Pname = PyString_FromStringAndSize(group_name.value, group_name.length);
    RETURN_IF_NULL(Pname);

    Paddrs = PyList_New(naddrs);
    RETURN_IF_NULL(Paddrs);
    for (i=0; i<naddrs; i++)
    {
	Paddr = PyTuple_New(3);
	RETURN_IF_NULL(Paddr);
	PyTuple_SET_ITEM(Paddr, 0, PyInt_FromLong(addrs[i].nodeid));
	PyTuple_SET_ITEM(Paddr, 1, PyInt_FromLong(addrs[i].pid));
	PyTuple_SET_ITEM(Paddr, 2, PyInt_FromLong(addrs[i].reason));
	PyList_SET_ITEM(Paddrs, i, Paddr);
    }

    Presult = PyTuple_New(2);
    RETURN_IF_NULL(Presult);
    PyTuple_SET_ITEM(Presult, 0, Pname);
    PyTuple_SET_ITEM(Presult, 1, Paddrs);
    return Presult;
}

/*
 * Constants and methods.
 */

typedef struct
{
    const char *name;
    int value;
} py_cpg_constant_t;

static py_cpg_constant_t py_cpg_constants[] =
{
    { "REASON_JOIN", CPG_REASON_JOIN },
    { "REASON_LEAVE", CPG_REASON_LEAVE },
    { "REASON_NODEUP", CPG_REASON_NODEUP },
    { "REASON_NODEDOWN", CPG_REASON_NODEDOWN },
    { "DISPATCH_ONE", CPG_DISPATCH_ONE },
    { "DISPATCH_ALL", CPG_DISPATCH_ALL },
    { "DISPATCH_BLOCKING", CPG_DISPATCH_BLOCKING },
    { "TYPE_UNORDERED", CPG_TYPE_UNORDERED },
    { "TYPE_FIFO", CPG_TYPE_FIFO },
    { "TYPE_AGREED", CPG_TYPE_AGREED },
    { "TYPE_SAFE", CPG_TYPE_SAFE },
    { NULL, 0 }
};

typedef struct
{
    int code;
    const char *name;
} py_cpg_error_t;

static PyMethodDef py_cpg_methods[] = 
{
    { "initialize", (PyCFunction) py_cpg_initialize, METH_VARARGS },
    { "finalize", (PyCFunction) py_cpg_finalize, METH_VARARGS },
    { "join", (PyCFunction) py_cpg_join, METH_VARARGS },
    { "leave", (PyCFunction) py_cpg_leave, METH_VARARGS },
    { "fd_get", (PyCFunction) py_cpg_fd_get, METH_VARARGS },
    { "membership_get", (PyCFunction) py_cpg_membership_get, METH_VARARGS },
    { "dispatch", (PyCFunction) py_cpg_dispatch, METH_VARARGS },
    { "mcast_joined", (PyCFunction) py_cpg_mcast_joined, METH_VARARGS },
    { NULL, NULL }
};


/*
 * Module initialization function
 */

void
init_cpg(void)
{
    int i;
    PyObject *Pmodule, *Pdict;

    Pmodule = Py_InitModule("_cpg", py_cpg_methods);
    Pdict = PyModule_GetDict(Pmodule);

    py_cpg_init_callbacks();

    py_cpg_error = PyErr_NewException("corosync._cpg.Error", NULL, NULL);
    PyDict_SetItemString(Pdict, "Error", py_cpg_error);

    for (i=0; py_cpg_constants[i].name != NULL; i++)
    {
	PyDict_SetItemString(Pdict, py_cpg_constants[i].name,
			     PyInt_FromLong(py_cpg_constants[i].value));
    }
}
