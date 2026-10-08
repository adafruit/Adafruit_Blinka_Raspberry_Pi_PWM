/* SPDX-License-Identifier: MIT
 * TEST ONLY. Compile unchanged native sources with ioctl/pthread_cond_timedwait
 * aliases; this translation unit calls the real functions. Not installed or
 * used by setup.py. Records describe instrumentation, not production timing.
 */
#undef ioctl
#undef pthread_cond_timedwait
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

enum { TRACE_LIMIT = 131072 };
typedef struct {
    atomic_int ready;
    char kind;
    int fd, level, result;
    long tid;
    uint64_t begin, end, deadline, cpu;
} sample;
static sample *samples;
static atomic_size_t count;
static atomic_int clock_error;
static FILE *trace_file;
static int init_error;
static pid_t owner;
static _Thread_local long cached_tid;

struct gpio_values { uint64_t bits, mask; } __attribute__((aligned(8)));
#define SET_VALUES _IOWR(0xb4, 0x0f, struct gpio_values)

static uint64_t clock_ns(clockid_t id) {
    struct timespec ts;
    if (clock_gettime(id, &ts)) {
        int expected = 0;
        atomic_compare_exchange_strong_explicit(&clock_error, &expected, errno,
                                               memory_order_relaxed, memory_order_relaxed);
        return 0;
    }
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

__attribute__((constructor)) static void trace_init(void) {
    owner = getpid();
    const char *path = getenv("PWM_TRACE_PATH");
    if (!path || !*path) { init_error = EINVAL; return; }
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) { init_error = errno; return; }
    trace_file = fdopen(fd, "w");
    if (!trace_file) { init_error = errno; close(fd); return; }
    samples = calloc(TRACE_LIMIT, sizeof(*samples));
    if (!samples) { init_error = ENOMEM; return; }
    /* Fault in pages before any GPIO request/worker. No allocations/logging in
     * either wrapper. This is not a promise against paging or preemption. */
    for (size_t i = 0; i < TRACE_LIMIT; i++) atomic_init(&samples[i].ready, 0);
    atomic_init(&count, 0);
}

int pwm_trace_status(void) {
    if (getpid() != owner) return ECHILD;
    return init_error;
}

static void record(char kind, int fd, int level, int result, uint64_t begin,
                   uint64_t end, uint64_t deadline, uint64_t cpu) {
    size_t index = atomic_fetch_add_explicit(&count, 1, memory_order_relaxed);
    if (index >= TRACE_LIMIT) return;
    sample *s = &samples[index];
    s->kind = kind; s->fd = fd; s->level = level; s->result = result;
    s->tid = cached_tid; s->begin = begin; s->end = end;
    s->deadline = deadline; s->cpu = cpu;
    atomic_store_explicit(&s->ready, 1, memory_order_release);
}

int pwm_trace_ioctl(int fd, unsigned long request, ...) {
    int saved = errno;
    int status = pwm_trace_status();
    if (status) { errno = status; return -1; }
    /* Only module.c's one known pointer-valued ioctl is renamed. Do not try to
     * forward arbitrary integer/no-argument ioctl varargs. */
    if (request != SET_VALUES) { errno = EINVAL; return -1; }
    va_list args;
    va_start(args, request);
    struct gpio_values *values = va_arg(args, struct gpio_values *);
    va_end(args);
    if (!cached_tid) cached_tid = syscall(SYS_gettid);
    uint64_t cpu_before = clock_ns(CLOCK_THREAD_CPUTIME_ID);
    uint64_t begin = clock_ns(CLOCK_MONOTONIC);
    errno = saved;
    int result = ioctl(fd, request, values);
    int after_errno = errno;
    uint64_t end = clock_ns(CLOCK_MONOTONIC);
    uint64_t cpu = clock_ns(CLOCK_THREAD_CPUTIME_ID) - cpu_before;
    record('I', fd, values->bits & 1, result < 0 ? after_errno : 0,
           begin, end, 0, cpu);
    errno = after_errno;
    return result;
}

int pwm_trace_wait(pthread_cond_t *cond, pthread_mutex_t *lock,
                   const struct timespec *deadline) {
    int saved = errno;
    int status = pwm_trace_status();
    if (status) return status;
    if (!cached_tid) cached_tid = syscall(SYS_gettid);
    uint64_t cpu_before = clock_ns(CLOCK_THREAD_CPUTIME_ID);
    uint64_t begin = clock_ns(CLOCK_MONOTONIC);
    errno = saved;
    int result = pthread_cond_timedwait(cond, lock, deadline);
    int after_errno = errno;
    uint64_t end = clock_ns(CLOCK_MONOTONIC);
    uint64_t cpu = clock_ns(CLOCK_THREAD_CPUTIME_ID) - cpu_before;
    record('W', -1, -1, result, begin, end,
           (uint64_t)deadline->tv_sec * 1000000000ULL + deadline->tv_nsec, cpu);
    errno = after_errno;
    return result;
}

__attribute__((destructor)) static void trace_finish(void) {
    if (getpid() != owner || !trace_file) return;
    size_t attempted = samples ? atomic_load_explicit(&count, memory_order_relaxed) : 0;
    size_t kept = attempted < TRACE_LIMIT ? attempted : TRACE_LIMIT;
    fprintf(trace_file, "seq,kind,tid,fd,level,result,begin_ns,end_ns,deadline_ns,cpu_ns\n");
    size_t written = 0;
    for (size_t i = 0; i < kept; i++) {
        sample *s = &samples[i];
        if (!atomic_load_explicit(&s->ready, memory_order_acquire)) continue;
        fprintf(trace_file, "%zu,%c,%ld,%d,%d,%d,%llu,%llu,%llu,%llu\n", i,
                s->kind, s->tid, s->fd, s->level, s->result,
                (unsigned long long)s->begin, (unsigned long long)s->end,
                (unsigned long long)s->deadline, (unsigned long long)s->cpu);
        written++;
    }
    int failed = ferror(trace_file);
    if (fclose(trace_file)) failed = 1;
    fprintf(stderr, "PWM_TRACE attempted=%zu written=%zu dropped=%zu init_error=%d io_error=%d clock_error=%d\n",
            attempted, written, attempted - written, init_error, failed,
            atomic_load_explicit(&clock_error, memory_order_relaxed));
    /* Process exit reclaims memory. Never free it here: abnormal termination
     * might still have a worker publishing into it. Normal runs deinit first. */
}
