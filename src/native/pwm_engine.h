/* SPDX-License-Identifier: MIT */
#ifndef BLINKA_PWM_ENGINE_H
#define BLINKA_PWM_ENGINE_H
#include <stdint.h>

typedef struct pwm_engine pwm_engine;
/* Writer returns zero or a positive errno. Never called from Python threads. */
typedef int (*pwm_writer)(void *context, int value);

int pwm_start(pwm_engine **out, pwm_writer writer, void *context,
              unsigned frequency, unsigned duty);
int pwm_start_with_slice(pwm_engine **out, pwm_writer writer, void *context,
                        unsigned frequency, unsigned duty, int short_slice);
int pwm_configure(pwm_engine *engine, unsigned frequency, unsigned duty);
int pwm_check(pwm_engine *engine);
int pwm_stop(pwm_engine *engine);
void pwm_destroy(pwm_engine *engine);
uint64_t pwm_missed_cycles(pwm_engine *engine);
#endif
