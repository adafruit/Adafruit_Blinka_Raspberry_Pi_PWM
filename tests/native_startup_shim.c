/* SPDX-License-Identifier: MIT
 * Test-only syscall replacements: record GPIO commands in an ordinary pipe
 * and fail thread creation or worker timing setup. Production sources unchanged.
 */
#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <unistd.h>

struct pwm_gpio_values { uint64_t bits, mask; } __attribute__((aligned(8)));

int ioctl(int fd, unsigned long request, ...) {
    (void)request;
    va_list args;
    va_start(args, request);
    struct pwm_gpio_values *values = va_arg(args, struct pwm_gpio_values *);
    char level = values->bits ? '1' : '0';
    va_end(args);
    if (write(fd, &level, 1) != 1) return -1;
    if (level == '1' && getenv("PWM_TEST_INITIAL_FAILURE")) {
        errno = EPERM;
        return -1;
    }
    if (level == '0' && getenv("PWM_TEST_LOW_FAILURE")) {
        errno = EIO;
        return -1;
    }
    return 0;
}

/* The build macro renames the header declaration; declare the real function
 * explicitly so the timing-failure cases can launch an actual worker. */
#undef pthread_create
extern int pthread_create(pthread_t *, const pthread_attr_t *,
                          void *(*)(void *), void *);

int pwm_test_prctl(int option, ...) {
    (void)option;
    errno = EACCES;
    return -1;
}

int pwm_test_pthread_create(pthread_t *thread, const pthread_attr_t *attributes,
                   void *(*entry)(void *), void *argument) {
    if (getenv("PWM_TEST_TIMER_FAILURE")) {
        return pthread_create(thread, attributes, entry, argument);
    }
    return EAGAIN;
}
