/* SPDX-License-Identifier: MIT */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "pwm_engine.h"
#include "pwm_shared.h"

#define CAPSULE "adafruit_blinka_raspberry_pi_pwm.worker"
/* GPIO v2 stable userspace ABI: two aligned u64s, ioctl number 0x0f.
 * Defined here so builds do not depend on newer distribution kernel headers.
 * Reference: include/uapi/linux/gpio.h (Linux syscall-note exception).
 */
struct pwm_gpio_values { uint64_t bits, mask; } __attribute__((aligned(8)));
_Static_assert(sizeof(struct pwm_gpio_values) == 16, "GPIO v2 values ABI size");
#define PWM_SET_VALUES _IOWR(0xb4, 0x0f, struct pwm_gpio_values)
typedef struct { pwm_engine *engine; pwm_shared *shared; int fd; } worker;

static void destroy_worker(worker *w) {
    if (w->shared) pwm_shared_destroy(w->shared);
    else pwm_destroy(w->engine);
}

static int gpio_write(void *context, int value) {
    worker *w = context;
    /* Exactly one requested line: bit zero indexes the request, not the GPIO. */
    struct pwm_gpio_values values = { .bits = value ? 1 : 0, .mask = 1 };
    int result;
    do { result = ioctl(w->fd, PWM_SET_VALUES, &values); }
    while (result < 0 && errno == EINTR);
    return result < 0 ? errno : 0;
}

static PyObject *report(int result) {
    if (!result) Py_RETURN_NONE;
    if (result == ECHILD) {
        PyErr_SetString(PyExc_RuntimeError,
                        "PWM objects cannot be used after fork; create them in the child");
    } else {
        errno = result;
        PyErr_SetFromErrno(PyExc_OSError);
    }
    return NULL;
}

static void dispose(PyObject *capsule) {
    worker *w = PyCapsule_GetPointer(capsule, CAPSULE);
    if (!w) { PyErr_Clear(); return; }
    destroy_worker(w);
    close(w->fd);
    free(w);
}

static PyObject *start(PyObject *self, PyObject *args) {
    (void)self;
    int fd, short_slice = 0, shared = 0;
    unsigned frequency, duty;
    if (!PyArg_ParseTuple(args, "iII|pp", &fd, &frequency, &duty,
                         &short_slice, &shared)) return NULL;
    if (frequency < 1 || frequency > 10000 || duty > 65535) return report(EINVAL);
    worker *w = calloc(1, sizeof(*w));
    if (!w) return PyErr_NoMemory();
    w->fd = fcntl(fd, F_DUPFD_CLOEXEC, 0);
    if (w->fd < 0) { int saved = errno; free(w); return report(saved); }
    /* Verify the descriptor before launching a worker and start at a steady level. */
    int result = gpio_write(w, duty == 65535);
    if (!result) {
        if (shared) result = pwm_shared_start(&w->shared, gpio_write, w,
                                              frequency, duty, short_slice);
        else result = pwm_start_with_slice(&w->engine, gpio_write, w,
                                           frequency, duty, short_slice);
    }
    if (result) {
        /* Startup may already have driven high. Best effort low before release;
         * report the original failure even if this cleanup write also fails. */
        gpio_write(w, 0);
        close(w->fd);
        free(w);
        return report(result);
    }
    PyObject *capsule = PyCapsule_New(w, CAPSULE, dispose);
    if (!capsule) { destroy_worker(w); close(w->fd); free(w); }
    return capsule;
}

static PyObject *configure(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *capsule;
    unsigned frequency, duty;
    if (!PyArg_ParseTuple(args, "OII", &capsule, &frequency, &duty)) return NULL;
    worker *w = PyCapsule_GetPointer(capsule, CAPSULE);
    if (!w) return NULL;
    return report(w->shared ? pwm_shared_configure(w->shared, frequency, duty)
                           : pwm_configure(w->engine, frequency, duty));
}

static PyObject *check(PyObject *self, PyObject *capsule) {
    (void)self;
    worker *w = PyCapsule_GetPointer(capsule, CAPSULE);
    return w ? report(w->shared ? pwm_shared_check(w->shared) : pwm_check(w->engine)) : NULL;
}

static PyObject *stop(PyObject *self, PyObject *capsule) {
    (void)self;
    worker *w = PyCapsule_GetPointer(capsule, CAPSULE);
    return w ? report(w->shared ? pwm_shared_stop(w->shared) : pwm_stop(w->engine)) : NULL;
}

static PyMethodDef methods[] = {
    {"start", start, METH_VARARGS, "Start a native worker on a single-line gpiod v2 fd."},
    {"configure", configure, METH_VARARGS, "Queue frequency and duty for the next cycle."},
    {"check", check, METH_O, "Report any asynchronous output failure."},
    {"stop", stop, METH_O, "Join the worker and drive the line low."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef definition = {
    PyModuleDef_HEAD_INIT, .m_name = "_native", .m_doc = "Native GPIO v2 software PWM",
    .m_size = -1, .m_methods = methods
};
PyMODINIT_FUNC PyInit__native(void) { return PyModule_Create(&definition); }
