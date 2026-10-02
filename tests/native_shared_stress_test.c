/* SPDX-License-Identifier: MIT
 * Concurrent callers repeatedly attach/detach outputs in both scheduling
 * groups. Recording callbacks only; no hardware access. */
#include "pwm_shared.h"
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <time.h>

typedef struct { unsigned index, writes; int last; } client;
static int record(void *context, int value) {
    client *c = context;
    c->writes++;
    c->last = value;
    return 0;
}
static void *exercise(void *argument) {
    client *c = argument;
    for (unsigned i = 0; i < 50; i++) {
        pwm_shared *e = NULL;
        assert(pwm_shared_start(&e, record, c, 500 + c->index * 100,
                                32768, c->index % 2) == 0);
        assert(pwm_shared_configure(e, 500, i % 2 ? 65535 : 0) == 0);
        struct timespec delay = {.tv_nsec = 1000000};
        while (nanosleep(&delay, &delay) && errno == EINTR) {}
        assert(pwm_shared_check(e) == 0);
        assert(pwm_shared_stop(e) == 0 && c->last == 0);
        unsigned stopped = c->writes;
        assert(pwm_shared_stop(e) == 0 && c->writes == stopped);
        pwm_shared_destroy(e);
    }
    return NULL;
}
int main(void) {
    pthread_t threads[8];
    client clients[8] = {0};
    for (unsigned i = 0; i < 8; i++) {
        clients[i].index = i;
        assert(pthread_create(&threads[i], NULL, exercise, &clients[i]) == 0);
    }
    for (unsigned i = 0; i < 8; i++) {
        assert(pthread_join(threads[i], NULL) == 0);
        assert(clients[i].writes >= 50 && clients[i].last == 0);
    }
    puts("shared scheduler: 400 concurrent attach/update/stop lifetimes passed");
    return 0;
}
