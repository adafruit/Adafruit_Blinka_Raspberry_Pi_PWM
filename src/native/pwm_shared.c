/* SPDX-License-Identifier: MIT
 * Experimental non-PIO scheduler. One worker services all active outputs using
 * the same short-slice opt-in. Each output retains its own GPIO request, phase,
 * pending configuration and error. No Python calls, GIL or busy-waiting.
 */
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#ifdef __linux__
#define _GNU_SOURCE
#endif
#include "pwm_shared.h"
#include <errno.h>
#include <pthread.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#ifdef __linux__
#include "pwm_sched.h"
#include <sched.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#endif

typedef struct scheduler scheduler;
enum phase { BOUNDARY, FALLING, CONSTANT };
struct pwm_shared {
    scheduler *group;
    struct pwm_shared *next;
    pid_t owner;
    pwm_writer writer;
    void *context;
    unsigned frequency, duty, active_frequency, active_duty;
    uint64_t sequence, applied, start, period, high, deadline, missed;
    enum phase phase;
    int level, stopped, error;
};
struct scheduler {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    pthread_t thread;
    scheduler *next;
    pwm_shared *outputs;
    unsigned references;
    int short_slice, ready, stopping, error;
};

/* Registry serializes creation and final worker joins, but is never acquired by
 * the waveform thread. Stopped handles retain their group until destruction.
 * Fork children abandon the inherited registry without touching worker locks. */
static pthread_mutex_t registry_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_once_t fork_once = PTHREAD_ONCE_INIT;
static scheduler *groups;
static int fork_error;
static void fork_prepare(void) { pthread_mutex_lock(&registry_lock); }
static void fork_parent(void) { pthread_mutex_unlock(&registry_lock); }
static void fork_child(void) {
    groups = NULL;
    pthread_mutex_unlock(&registry_lock);
}
static void install_fork_handlers(void) {
    fork_error = pthread_atfork(fork_prepare, fork_parent, fork_child);
}

static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static void request_short_slice(void) {
#if defined(__linux__) && defined(SYS_sched_getattr) && defined(SYS_sched_setattr)
    struct pwm_sched_attr attributes = { .size = sizeof(attributes) };
    if (syscall(SYS_sched_getattr, 0, &attributes,
                (unsigned int)sizeof(attributes), 0U) < 0) return;
    if (attributes.policy != SCHED_OTHER) return;
    attributes.size = sizeof(attributes);
    attributes.runtime = 100000;
    (void)syscall(SYS_sched_setattr, 0, &attributes, 0U);
#endif
}

/* Only call with the group lock held. Cache successful levels, not failed
 * writes. Cleanup always attempts low, preserving the first output error. */
static void write_value(pwm_shared *e, int value, int force) {
    if (!force && e->level == value) return;
    int result = e->writer(e->context, value);
    if (result) {
        if (!e->error) e->error = result;
    } else e->level = value;
}

static void advance(pwm_shared *e, uint64_t now) {
    if (e->phase == FALLING) {
        write_value(e, 0, 0);
        e->phase = BOUNDARY;
        e->deadline = e->start + e->period;
        return;
    }
    if (e->phase == CONSTANT) e->start = now;
    else e->start = e->deadline;
    e->active_frequency = e->frequency;
    e->active_duty = e->duty;
    e->applied = e->sequence;
    if (e->active_duty == 0 || e->active_duty == 65535) {
        write_value(e, e->active_duty != 0, 0);
        e->phase = CONSTANT;
        e->deadline = UINT64_MAX;
        return;
    }
    e->period = (1000000000ULL + e->active_frequency / 2) / e->active_frequency;
    e->high = (e->period * e->active_duty + 32767) / 65535;
    if (now >= e->start + e->period) {
        uint64_t skipped = (now - e->start) / e->period;
        e->missed += skipped;
        e->start += skipped * e->period;
    }
    /* Do not replay missed cycles or raise a pulse whose fall is already due. */
    if (now_ns() < e->start + e->high) {
        write_value(e, 1, 0);
        e->phase = FALLING;
        e->deadline = e->start + e->high;
    } else {
        write_value(e, 0, 0);
        e->phase = BOUNDARY;
        e->deadline = e->start + e->period;
    }
}

static int wait_until(scheduler *g, uint64_t deadline) {
    if (deadline == UINT64_MAX) return pthread_cond_wait(&g->changed, &g->lock);
    uint64_t now = now_ns();
    if (now >= deadline) return 0;
    struct timespec ts;
#ifdef __APPLE__
    uint64_t relative = deadline - now;
    ts.tv_sec = (time_t)(relative / 1000000000ULL);
    ts.tv_nsec = (long)(relative % 1000000000ULL);
    return pthread_cond_timedwait_relative_np(&g->changed, &g->lock, &ts);
#else
    ts.tv_sec = (time_t)(deadline / 1000000000ULL);
    ts.tv_nsec = (long)(deadline % 1000000000ULL);
    return pthread_cond_timedwait(&g->changed, &g->lock, &ts);
#endif
}

static void *run(void *argument) {
    scheduler *g = argument;
    pthread_mutex_lock(&g->lock);
#ifdef __linux__
    if (prctl(PR_SET_TIMERSLACK, 1UL, 0UL, 0UL, 0UL) < 0) g->error = errno;
#endif
    if (!g->error && g->short_slice) request_short_slice();
    g->ready = 1;
    pthread_cond_broadcast(&g->changed);
    while (!g->stopping && !g->error) {
        /* Service due falls before rises on other outputs. Use fresh time for
         * each output: a preceding GPIO ioctl may itself have been delayed. */
        for (pwm_shared *e = g->outputs; e; e = e->next) {
            if (!e->error && e->phase == FALLING && e->deadline <= now_ns()) {
                advance(e, now_ns());
                if (e->error) write_value(e, 0, 1);
            }
        }
        uint64_t next = UINT64_MAX;
        for (pwm_shared *e = g->outputs; e; e = e->next) {
            if (e->error) continue;
            if (e->phase == CONSTANT && e->sequence != e->applied)
                e->deadline = now_ns();
            if (e->deadline <= now_ns()) {
                advance(e, now_ns());
                if (e->error) write_value(e, 0, 1);
            }
            if (!e->error && e->deadline < next) next = e->deadline;
        }
        /* Hand control back to callers even if all deadlines are late. Recompute
         * before waiting so a configuration/stop signal cannot be lost here. */
        pthread_mutex_unlock(&g->lock);
        pthread_mutex_lock(&g->lock);
        if (g->stopping) break;
        next = UINT64_MAX;
        for (pwm_shared *e = g->outputs; e; e = e->next) {
            if (e->error) continue;
            uint64_t due = (e->phase == CONSTANT && e->sequence != e->applied)
                ? now_ns() : e->deadline;
            if (due < next) next = due;
        }
        int result = wait_until(g, next);
        if (result && result != ETIMEDOUT) g->error = result;
    }
    if (g->error) {
        for (pwm_shared *e = g->outputs; e; e = e->next) {
            if (!e->error) e->error = g->error;
            write_value(e, 0, 1);
        }
    }
    pthread_mutex_unlock(&g->lock);
    return NULL;
}

static int validate(unsigned frequency, unsigned duty) {
    return frequency < 1 || frequency > 10000 || duty > 65535 ? EINVAL : 0;
}
static void free_group(scheduler *g) {
    pthread_cond_destroy(&g->changed);
    pthread_mutex_destroy(&g->lock);
    free(g);
}

int pwm_shared_start(pwm_shared **out, pwm_writer writer, void *context,
                     unsigned frequency, unsigned duty, int short_slice) {
    *out = NULL;
    int result = validate(frequency, duty);
    if (result) return result;
    result = pthread_once(&fork_once, install_fork_handlers);
    if (result || fork_error) return result ? result : fork_error;
    pwm_shared *e = calloc(1, sizeof(*e));
    if (!e) return ENOMEM;
    e->owner = getpid();
    e->writer = writer;
    e->context = context;
    e->frequency = frequency;
    e->duty = duty;
    e->phase = CONSTANT;
    e->applied = UINT64_MAX;
    e->level = -1;
    pthread_mutex_lock(&registry_lock);
    scheduler *g = groups;
    while (g) {
        pthread_mutex_lock(&g->lock);
        int available = !g->error && g->short_slice == !!short_slice;
        if (available) break;
        pthread_mutex_unlock(&g->lock);
        g = g->next;
    }
    if (g) {
        e->group = g;
        e->next = g->outputs;
        g->outputs = e;
        g->references++;
        pthread_cond_signal(&g->changed);
        pthread_mutex_unlock(&g->lock);
    } else {
        g = calloc(1, sizeof(*g));
        if (!g) { result = ENOMEM; goto failure; }
        result = pthread_mutex_init(&g->lock, NULL);
        if (result) { free(g); goto failure; }
        pthread_condattr_t attributes;
        result = pthread_condattr_init(&attributes);
        if (result) { pthread_mutex_destroy(&g->lock); free(g); goto failure; }
#ifndef __APPLE__
        result = pthread_condattr_setclock(&attributes, CLOCK_MONOTONIC);
#endif
        if (!result) result = pthread_cond_init(&g->changed, &attributes);
        pthread_condattr_destroy(&attributes);
        if (result) { pthread_mutex_destroy(&g->lock); free(g); goto failure; }
        e->group = g;
        g->outputs = e;
        g->references = 1;
        g->short_slice = !!short_slice;
        result = pthread_create(&g->thread, NULL, run, g);
        if (result) { free_group(g); goto failure; }
        pthread_mutex_lock(&g->lock);
        while (!g->ready) {
            result = pthread_cond_wait(&g->changed, &g->lock);
            if (result) break;
        }
        if (!result) result = g->error ? g->error : e->error;
        if (result) {
            g->stopping = 1;
            pthread_cond_signal(&g->changed);
        }
        pthread_mutex_unlock(&g->lock);
        if (result) {
            pthread_join(g->thread, NULL);
            free_group(g);
            goto failure;
        }
        g->next = groups;
        groups = g;
    }
    pthread_mutex_unlock(&registry_lock);
    *out = e;
    return 0;
failure:
    pthread_mutex_unlock(&registry_lock);
    free(e);
    return result;
}

int pwm_shared_configure(pwm_shared *e, unsigned frequency, unsigned duty) {
    if (e->owner != getpid()) return ECHILD;
    int result = validate(frequency, duty);
    if (result) return result;
    scheduler *g = e->group;
    pthread_mutex_lock(&g->lock);
    result = e->error ? e->error : (e->stopped ? EBADF : 0);
    if (!result) {
        e->frequency = frequency;
        e->duty = duty;
        e->sequence++;
        pthread_cond_signal(&g->changed);
    }
    pthread_mutex_unlock(&g->lock);
    return result;
}

int pwm_shared_check(pwm_shared *e) {
    if (e->owner != getpid()) return ECHILD;
    scheduler *g = e->group;
    pthread_mutex_lock(&g->lock);
    int result = e->error ? e->error : (e->stopped ? EBADF : 0);
    pthread_mutex_unlock(&g->lock);
    return result;
}

int pwm_shared_stop(pwm_shared *e) {
    if (e->owner != getpid()) return ECHILD;
    pthread_mutex_lock(&registry_lock);
    scheduler *g = e->group;
    pthread_mutex_lock(&g->lock);
    int last = 0;
    if (!e->stopped) {
        write_value(e, 0, 1);
        e->stopped = 1;
        pwm_shared **link = &g->outputs;
        while (*link != e) link = &(*link)->next;
        *link = e->next;
        if (!g->outputs) { g->stopping = 1; last = 1; }
        pthread_cond_signal(&g->changed);
    }
    int result = e->error;
    pthread_mutex_unlock(&g->lock);
    if (last) {
        int joined = pthread_join(g->thread, NULL);
        if (!result) result = joined;
        scheduler **link = &groups;
        while (*link != g) link = &(*link)->next;
        *link = g->next;
    }
    pthread_mutex_unlock(&registry_lock);
    return result;
}

void pwm_shared_destroy(pwm_shared *e) {
    if (!e) return;
    if (e->owner == getpid()) {
        pwm_shared_stop(e);
        pthread_mutex_lock(&registry_lock);
        scheduler *g = e->group;
        if (--g->references == 0) free_group(g);
        pthread_mutex_unlock(&registry_lock);
    }
    free(e);
}

uint64_t pwm_shared_missed_cycles(pwm_shared *e) {
    if (e->owner != getpid()) return 0;
    pthread_mutex_lock(&e->group->lock);
    uint64_t missed = e->missed;
    pthread_mutex_unlock(&e->group->lock);
    return missed;
}
