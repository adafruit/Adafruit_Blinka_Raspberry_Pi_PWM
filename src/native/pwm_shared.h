/* SPDX-License-Identifier: MIT */
#ifndef PWM_SHARED_H
#define PWM_SHARED_H
#include "pwm_engine.h"

typedef struct pwm_shared pwm_shared;
int pwm_shared_start(pwm_shared **out, pwm_writer writer, void *context,
                     unsigned frequency, unsigned duty, int short_slice);
int pwm_shared_configure(pwm_shared *output, unsigned frequency, unsigned duty);
int pwm_shared_check(pwm_shared *output);
int pwm_shared_stop(pwm_shared *output);
void pwm_shared_destroy(pwm_shared *output);
uint64_t pwm_shared_missed_cycles(pwm_shared *output);
#endif
