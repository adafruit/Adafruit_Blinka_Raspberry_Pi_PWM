/* SPDX-License-Identifier: MIT
 * Original draft implementation: one native worker per output. No Python API
 * or GIL in the waveform loop. Deadlines use CLOCK_MONOTONIC; missed cycles
 * are skipped rather than replayed as a burst of GPIO writes.
 */
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#include "pwm_engine.h"
#include <errno.h>
#include <pthread.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

struct pwm_engine {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    pthread_t thread;
    pid_t owner;
    pwm_writer writer;
    void *context;
    unsigned frequency, duty;
    uint64_t sequence, missed;
    int stopping, joined, error;
};

static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

/* lock is held on entry and return; configuration wakes do not truncate pulses. */
static void wait_until(pwm_engine *e, uint64_t deadline) {
    while (!e->stopping && !e->error) {
        uint64_t now = now_ns();
        if (now >= deadline) return;
        struct timespec ts;
#ifdef __APPLE__
        /* Allows testing the scheduler on macOS; the GPIO extension is Linux-only. */
        uint64_t relative = deadline - now;
        ts.tv_sec = (time_t)(relative / 1000000000ULL);
        ts.tv_nsec = (long)(relative % 1000000000ULL);
        int result = pthread_cond_timedwait_relative_np(&e->changed, &e->lock, &ts);
#else
        ts.tv_sec = (time_t)(deadline / 1000000000ULL);
        ts.tv_nsec = (long)(deadline % 1000000000ULL);
        int result = pthread_cond_timedwait(&e->changed, &e->lock, &ts);
#endif
        if (result != 0 && result != ETIMEDOUT) e->error = result;
    }
}

static void write_value(pwm_engine *e, int value) {
    int result = e->writer(e->context, value);
    if (result && !e->error) e->error = result;
}

static void *run(void *argument) {
    pwm_engine *e = argument;
    pthread_mutex_lock(&e->lock);
    uint64_t start = now_ns();
    while (!e->stopping && !e->error) {
        unsigned frequency = e->frequency;
        unsigned duty = e->duty;
        uint64_t sequence = e->sequence;
        if (duty == 0 || duty == 65535) {
            write_value(e, duty != 0);
            while (!e->stopping && !e->error && sequence == e->sequence) {
                int result = pthread_cond_wait(&e->changed, &e->lock);
                if (result) e->error = result;
            }
            start = now_ns();
            continue;
        }
        uint64_t period = (1000000000ULL + frequency / 2) / frequency;
        uint64_t high = (period * duty + 32767) / 65535;
        uint64_t end = start + period;
        uint64_t now = now_ns();
        if (now >= end) {
            uint64_t skipped = (now - start) / period;
            e->missed += skipped;
            start += skipped * period;
            end = start + period;
        }
        /* A late worker never emits a high pulse whose falling deadline passed. */
        if (now_ns() < start + high) {
            write_value(e, 1);
            wait_until(e, start + high);
        }
        write_value(e, 0);
        wait_until(e, end);
        start = end;
        /* Let callers acquire the lock even when every deadline is already late. */
        pthread_mutex_unlock(&e->lock);
        pthread_mutex_lock(&e->lock);
    }
    /* Best effort on failure; report the original failure to the caller. */
    write_value(e, 0);
    pthread_mutex_unlock(&e->lock);
    return NULL;
}

static int validate(unsigned frequency, unsigned duty) {
    return (frequency < 1 || frequency > 10000 || duty > 65535) ? EINVAL : 0;
}

int pwm_start(pwm_engine **out, pwm_writer writer, void *context,
              unsigned frequency, unsigned duty) {
    *out = NULL;
    int result = validate(frequency, duty);
    if (result) return result;
    pwm_engine *e = calloc(1, sizeof(*e));
    if (!e) return ENOMEM;
    e->owner = getpid();
    e->writer = writer;
    e->context = context;
    e->frequency = frequency;
    e->duty = duty;
    result = pthread_mutex_init(&e->lock, NULL);
    if (result) { free(e); return result; }
    pthread_condattr_t attributes;
    result = pthread_condattr_init(&attributes);
    if (result) { pthread_mutex_destroy(&e->lock); free(e); return result; }
#ifndef __APPLE__
    result = pthread_condattr_setclock(&attributes, CLOCK_MONOTONIC);
#endif
    if (!result) result = pthread_cond_init(&e->changed, &attributes);
    pthread_condattr_destroy(&attributes);
    if (result) { pthread_mutex_destroy(&e->lock); free(e); return result; }
    result = pthread_create(&e->thread, NULL, run, e);
    if (result) {
        pthread_cond_destroy(&e->changed);
        pthread_mutex_destroy(&e->lock);
        free(e);
        return result;
    }
    *out = e;
    return 0;
}

int pwm_configure(pwm_engine *e, unsigned frequency, unsigned duty) {
    if (e->owner != getpid()) return ECHILD;
    int result = validate(frequency, duty);
    if (result) return result;
    pthread_mutex_lock(&e->lock);
    result = e->error ? e->error : (e->stopping ? EBADF : 0);
    if (!result) {
        e->frequency = frequency;
        e->duty = duty;
        e->sequence++;
        pthread_cond_signal(&e->changed);
    }
    pthread_mutex_unlock(&e->lock);
    return result;
}

int pwm_check(pwm_engine *e) {
    if (e->owner != getpid()) return ECHILD;
    pthread_mutex_lock(&e->lock);
    int result = e->error ? e->error : (e->stopping ? EBADF : 0);
    pthread_mutex_unlock(&e->lock);
    return result;
}

int pwm_stop(pwm_engine *e) {
    if (e->owner != getpid()) return ECHILD;
    if (!e->joined) {
        pthread_mutex_lock(&e->lock);
        e->stopping = 1;
        pthread_cond_signal(&e->changed);
        pthread_mutex_unlock(&e->lock);
        int result = pthread_join(e->thread, NULL);
        if (result) return result;
        e->joined = 1;
    }
    return e->error;
}

void pwm_destroy(pwm_engine *e) {
    if (!e) return;
    if (e->owner == getpid()) {
        pwm_stop(e);
        pthread_cond_destroy(&e->changed);
        pthread_mutex_destroy(&e->lock);
    }
    /* In a fork child the worker and lock owners no longer exist. */
    free(e);
}

uint64_t pwm_missed_cycles(pwm_engine *e) {
    if (e->owner != getpid()) return 0;
    pthread_mutex_lock(&e->lock);
    uint64_t missed = e->missed;
    pthread_mutex_unlock(&e->lock);
    return missed;
}
