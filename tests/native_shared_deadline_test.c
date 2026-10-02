/* SPDX-License-Identifier: MIT
 * Deterministic state-transition tests of the production shared scheduler.
 * No thread, sleep, GPIO or Python calls. */
#define clock_gettime pwm_test_clock_gettime
#include "../src/native/pwm_shared.c"
#include <assert.h>
#include <stdio.h>

static uint64_t clock_ns;
int pwm_test_clock_gettime(clockid_t clock, struct timespec *ts) {
    assert(clock == CLOCK_MONOTONIC);
    ts->tv_sec = (time_t)(clock_ns / 1000000000ULL);
    ts->tv_nsec = (long)(clock_ns % 1000000000ULL);
    return 0;
}
static unsigned highs, lows;
static int record(void *context, int level) {
    (void)context;
    if (level) highs++; else lows++;
    return 0;
}
static void step(pwm_shared *e, uint64_t timestamp) {
    clock_ns = timestamp;
    advance(e, timestamp);
}
int main(void) {
    pwm_shared e = {.writer = record, .frequency = 1000, .duty = 32768,
                    .phase = BOUNDARY, .level = -1};
    step(&e, 3750000);
    assert(e.missed == 3 && e.start == 3000000 && e.deadline == 4000000);
    assert(highs == 0 && lows == 1 && e.phase == BOUNDARY);
    step(&e, 4000000);
    assert(highs == 1 && e.phase == FALLING && e.deadline == 4500008);
    /* Pending changes cannot truncate the currently active high pulse. */
    e.frequency = 500;
    e.duty = 16384;
    e.sequence++;
    step(&e, 4800000);
    assert(e.active_frequency == 1000 && e.phase == BOUNDARY);
    assert(e.deadline == 5000000 && lows == 2);
    step(&e, 5000000);
    assert(e.active_frequency == 500 && e.period == 2000000);
    assert(e.phase == FALLING && e.deadline == 5500008);
    step(&e, 6000000);
    assert(e.phase == BOUNDARY && e.deadline == 7000000);
    step(&e, 10750000);
    assert(e.missed == 4 && e.start == 9000000 && e.deadline == 11000000);
    assert(e.phase == BOUNDARY && highs == 2);  /* No replay/catch-up burst. */
    e.duty = 65535;
    e.sequence++;
    step(&e, 11000000);
    assert(e.phase == CONSTANT && e.deadline == UINT64_MAX && e.level == 1);
    e.duty = 0;
    e.sequence++;
    step(&e, 12000000);
    assert(e.phase == CONSTANT && e.level == 0);
    e.duty = 32768;
    e.frequency = 50;
    e.sequence++;
    step(&e, 13000000);
    assert(e.start == 13000000 && e.period == 20000000 && e.phase == FALLING);
    puts("shared deadlines: skips, boundaries, endpoints and restart passed");
    return 0;
}
