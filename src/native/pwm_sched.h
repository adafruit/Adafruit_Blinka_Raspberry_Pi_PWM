/* SPDX-License-Identifier: MIT
 * Known Linux sched_getattr/setattr ABI prefix, independent of kernel headers.
 * Extra fields in future kernels are deliberately not passed back to setters.
 */
#ifndef BLINKA_PWM_SCHED_H
#define BLINKA_PWM_SCHED_H
#include <stdint.h>

struct pwm_sched_attr {
    uint32_t size, policy;
    uint64_t flags;
    int32_t nice;
    uint32_t priority;
    uint64_t runtime, deadline, period;
    uint32_t util_min, util_max;
};
_Static_assert(sizeof(struct pwm_sched_attr) == 56, "Linux sched_attr ABI size");
#endif
