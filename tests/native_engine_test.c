/* SPDX-License-Identifier: MIT
 * Tests the actual worker using a recording writer, never a GPIO descriptor.
 */
#include "pwm_engine.h"
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>

typedef struct {
    pthread_mutex_t lock;
    unsigned writes, highs, lows;
    int last, failure;
} recording;

static int record(void *context, int value) {
    recording *r = context;
    pthread_mutex_lock(&r->lock);
    r->writes++;
    if (value) r->highs++; else r->lows++;
    r->last = value;
    int failure = r->failure;
    pthread_mutex_unlock(&r->lock);
    return failure;
}

static void pause_ms(unsigned milliseconds) {
    struct timespec delay = {.tv_sec = milliseconds / 1000,
                             .tv_nsec = (milliseconds % 1000) * 1000000L};
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
}

static unsigned writes(recording *r) {
    pthread_mutex_lock(&r->lock);
    unsigned count = r->writes;
    pthread_mutex_unlock(&r->lock);
    return count;
}

int main(void) {
    recording first = {.lock = PTHREAD_MUTEX_INITIALIZER};
    recording second = {.lock = PTHREAD_MUTEX_INITIALIZER};
    pwm_engine *a = NULL, *b = NULL;
    assert(pwm_start(&a, record, &first, 0, 0) == EINVAL && a == NULL);
    assert(pwm_start(&a, record, &first, 50, 0) == 0);
    pause_ms(30);
    assert(writes(&first) == 1);  /* Steady low does not consume a timer loop. */
    assert(pwm_configure(a, 50, 65535) == 0);
    pause_ms(30);
    assert(writes(&first) == 2);
    assert(pwm_start(&b, record, &second, 500, 32768) == 0);
    assert(pwm_configure(a, 50, 32768) == 0);
    pause_ms(100);
    assert(pwm_configure(a, 100, 16384) == 0);
    assert(pwm_configure(a, 0, 0) == EINVAL);
    pause_ms(50);
    assert(pwm_check(a) == 0 && pwm_check(b) == 0);
    assert(writes(&first) > 4 && writes(&second) > 4);

    /* Forked children must fail without locking mutexes owned by vanished threads. */
    pid_t child = fork();
    assert(child >= 0);
    if (child == 0) {
        assert(pwm_check(a) == ECHILD);
        assert(pwm_stop(a) == ECHILD);
        pwm_destroy(a);
        pwm_destroy(b);
        _exit(0);
    }
    int child_status;
    assert(waitpid(child, &child_status, 0) == child);
    assert(WIFEXITED(child_status) && WEXITSTATUS(child_status) == 0);

    /* Check and stop report an asynchronous writer error and still join. */
    pthread_mutex_lock(&second.lock);
    second.failure = EIO;
    pthread_mutex_unlock(&second.lock);
    pause_ms(30);
    assert(pwm_check(b) == EIO);
    assert(pwm_stop(b) == EIO);
    assert(pwm_stop(a) == 0 && pwm_stop(a) == 0);
    assert(first.last == 0 && second.last == 0);
    assert(pwm_check(a) == EBADF);
    assert(pwm_configure(a, 500, 0) == EBADF);
    unsigned stopped_count = writes(&first);
    pause_ms(10);
    assert(writes(&first) == stopped_count);
    pwm_destroy(a);
    pwm_destroy(b);

    /* A one-second PWM period must not make deinit wait a second. */
    assert(pwm_start(&a, record, &first, 1, 32768) == 0);
    pause_ms(20);
    struct timespec before, after;
    clock_gettime(CLOCK_MONOTONIC, &before);
    assert(pwm_stop(a) == 0);
    clock_gettime(CLOCK_MONOTONIC, &after);
    double elapsed = after.tv_sec - before.tv_sec + (after.tv_nsec - before.tv_nsec) / 1e9;
    assert(elapsed < 0.25);
    pwm_destroy(a);
    pthread_mutex_destroy(&first.lock);
    pthread_mutex_destroy(&second.lock);
    puts("native scheduler: lifecycle, endpoints, concurrency, errors and fork passed");
    return 0;
}
