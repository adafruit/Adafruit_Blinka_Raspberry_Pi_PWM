/* SPDX-License-Identifier: MIT
 * Exercise the production engine with injected scheduling syscalls, never GPIO.
 */
#define _GNU_SOURCE
#include "pwm_engine.h"
#ifdef PWM_TEST_SHARED
#include "pwm_shared.h"
#define pwm_engine pwm_shared
#define pwm_start_with_slice pwm_shared_start
#define pwm_stop pwm_shared_stop
#define pwm_destroy pwm_shared_destroy
#endif
#include "pwm_sched.h"
#include <assert.h>
#include <errno.h>
#include <sched.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

static const char *scenario;
static unsigned gets, sets, writes;
static int last;

long syscall(long number, ...) {
    va_list args;
    va_start(args, number);
    assert(va_arg(args, int) == 0);  /* Only the calling worker, never a process ID. */
    struct pwm_sched_attr *attributes = va_arg(args, struct pwm_sched_attr *);
    if (number == SYS_sched_getattr) {
        gets++;
        assert(va_arg(args, unsigned int) == sizeof(*attributes));
        assert(va_arg(args, unsigned int) == 0);
        va_end(args);
        if (!strcmp(scenario, "get-unsupported") || !strcmp(scenario, "get-denied")) {
            errno = !strcmp(scenario, "get-denied") ? EPERM : ENOSYS;
            return -1;
        }
        *attributes = (struct pwm_sched_attr){
            .size = !strcmp(scenario, "future-abi") ? 128 : sizeof(*attributes),
            .policy = !strcmp(scenario, "non-normal") ? SCHED_FIFO : SCHED_OTHER,
            .flags = 1, .nice = 7, .priority = 0, .runtime = 2100000,
            .util_min = 123, .util_max = 456};
        return 0;
    }
    assert(number == SYS_sched_setattr);
    sets++;
    assert(va_arg(args, unsigned int) == 0);
    va_end(args);
    assert(attributes->size == sizeof(*attributes));
    assert(attributes->policy == SCHED_OTHER && attributes->nice == 7);
    assert(attributes->flags == 1 && attributes->priority == 0);
    assert(attributes->runtime == 100000);
    assert(attributes->util_min == 123 && attributes->util_max == 456);
    if (!strcmp(scenario, "set-unsupported") || !strcmp(scenario, "set-denied")) {
        errno = !strcmp(scenario, "set-denied") ? EPERM : EINVAL;
        return -1;
    }
    return 0;
}

static int record(void *context, int value) {
    (void)context;
    writes++;
    last = value;
    return 0;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    scenario = argv[1];
    pwm_engine *engine = NULL;
    assert(pwm_start_with_slice(&engine, record, NULL, 500, 0,
                                strcmp(scenario, "disabled") != 0) == 0);
    assert(pwm_stop(engine) == 0);
    pwm_destroy(engine);
    assert(writes > 0 && last == 0);
    if (!strcmp(scenario, "disabled")) {
        assert(gets == 0 && sets == 0);
    } else {
        assert(gets == 1);
        int skipped = !strncmp(scenario, "get-", 4) || !strcmp(scenario, "non-normal");
        assert(sets == (skipped ? 0U : 1U));
    }
    puts("optional worker slice: preserved settings and safe fallback passed");
    return 0;
}
