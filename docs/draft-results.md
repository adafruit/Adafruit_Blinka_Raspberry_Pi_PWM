# Initial draft validation — October 1, 2026

| Environment | Interpreter | Result |
| --- | --- | --- |
| macOS development host | CPython 3.14 | 35 passed, 1 Linux-only test skipped |
| test-pi4, BCM2711, Linux ARM64 | CPython 3.13.5 | 36 passed |
| test-pi5, BCM2712/RP1, Linux ARM64 | CPython 3.13.5 | 36 passed |

Both Pi runs installed a wheel built from the source distribution into a fresh
virtual environment and tested the installed Python package and Linux extension.
They used gpiod 2.5.0. Native worker tests used a recording C writer; extension
descriptor tests used ordinary pipes to check failure paths and descriptor leaks.
No test in these runs drove or requested a physical GPIO line.

The C scheduler also passed a macOS build with `-fsanitize=address,undefined`
and `-Wall -Wextra -Werror`. Python lint and formatting checks passed. The
included Blinka integration patch passed `git apply --check` against the local
Blinka checkout. That checkout remains unmodified.

Read-only discovery found `/dev/gpiochip0` with `pinctrl-bcm2711` on Pi 4 and
`pinctrl-rp1` on Pi 5. Both expose `/dev/gpiochip4` as a symlink to gpiochip0;
the discovery code now resolves aliases before counting controllers. Regression
tests also ensure genuinely distinct matching controllers remain ambiguous.

The real Adafruit Motor 3.5.0 Servo and DCMotor classes were exercised against
the public PWMOut API with a recording Python engine. This verifies interface
use and computed duty values, not physical motor/servo behavior.

Test environments retained for later evaluation:

- Pi 4: `/tmp/blinka-pwm-draft.PV2BaT/venv`
- Pi 5: `/tmp/blinka-pwm-draft.5VVpY8/venv`

Pending: physical GPIO output and cleanup, loopback/scope measurements, timing
and CPU comparisons with RPi.GPIO/lgpio, other Pi generations/architectures,
Python 3.9–3.12, library coverage beyond Servo/DCMotor, wheel distribution,
and accelerated backends. This record covers the initial development runs;
see the repository's GitHub Actions page for subsequent CI results.
See [the validation gates](validation.md).

## Startup cleanup regression

After fixing startup failure cleanup, the macOS suite passed 40 tests with one
Linux-only test skipped. Five new cases compile the production extension and
scheduler with test-only replacements for GPIO ioctl and thread creation.
GPIO commands are recorded in an ordinary pipe; thread creation returns EAGAIN.
The checks cover initial low, partial duty, and full-high duty, a failed cleanup
write, and a failed initial write. They verify a low command is attempted before
closing the duplicated descriptor and the original error is preserved even if
cleanup also fails. These tests do not request or drive physical GPIOs.

## Pi 3B+ 32-bit validation

Commit `15e784a` passed all 41 tests on `test-pi3`, a Raspberry Pi 3 Model B Plus
Rev 1.3 running Raspbian GNU/Linux 13 (Trixie), kernel
`6.18.50+rpt-rpi-v7`, and CPython 3.13.5 with a 32-bit interpreter (`armv7l`).

The package was built from its source distribution into a
`cp313-cp313-linux_armv7l` wheel and installed in a fresh virtual environment.
Tests imported the installed Python package and production Linux extension,
not an editable source checkout. The environment used Adafruit Motor 3.5.0 and
the official gpiod 2.5.0 bindings, installed from an ARMv7 wheel on piwheels.
All five injected startup-failure regressions passed on this platform too.

Read-only discovery found `/dev/gpiochip0`, label `pinctrl-bcm2835`, exposing
54 lines. The test user already belongs to the `gpio` group. No test requested
or drove a physical GPIO, so these results establish 32-bit build/API coverage,
not PWM waveform quality or timing performance.

The retained test environment is `/tmp/blinka-pwm-pi3.ohoO6y/venv`.

## First Pi 4 physical waveform comparisons

The separate bench host `test2-pi4` (Pi 4 Model B Rev 1.4) passed all 41 tests
with CPython 3.13.5, 64-bit Linux, Debian 13 (Trixie), kernel
`6.18.50+rpt-rpi-v8`, and gpiod 2.5.0. The source distribution from snapshot
`cfa911b` built and installed successfully in an isolated virtual environment.
GPIO18 was confirmed unclaimed before physical testing. The rack-mounted
`test-pi4` was not used for these waveform captures.

Hardware: Saleae Logic 8, Logic 2 version 2.4.46, digital channel 0 connected
to BCM GPIO18 (header pin 12), with a common ground. Sampling was 10 MSa/s
(100 ns quantization); no glitch filter was enabled. Captures were saved as
native `.sal` files and raw digital binary exports in the local measurement
directory. Analyzer clock accuracy was not independently calibrated.

Each output ran for three seconds, bracketed by 0.2-second low intervals.
Statistics use complete rising-to-rising cycles, trimming 50 ms from each end
of the active interval. All recorded outputs finished low with at least 0.19 s
of stable low tail. These captures test stopping after explicitly setting zero
duty; they do not yet prove deinitialization directly from high duty or every
failure path on real GPIOs. There was no deliberate CPU load. The governor read
after the initial capture was `ondemand`; settings were not changed for testing.

The baseline used Blinka's actual `rpi_gpio_pwmout.py` wrapper from commit
`beb49bf`, with a pin object exposing `id=18`, and Debian's RPi.GPIO 0.7.1a4
(`python3-rpi.gpio` package 0.7.1~a4-1.2). Both backends were configured with
duty 32768: the existing wrapper rounds this to 50%, while the draft uses the
16-bit fraction directly (approximately 50.0008%). Backends ran sequentially,
never simultaneously on the pin.

| Requested Hz | Backend | Complete cycles | Mean Hz | Mean duty % | Period stddev, µs | High-width min–max, µs |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | RPi.GPIO wrapper | 143 | 49.709 | 50.000 | 1.175 | 10057.0–10067.6 |
| 50 | Draft | 144 | 49.998 | 49.982 | 2.407 | 9983.1–10004.5 |
| 500 | RPi.GPIO wrapper | 1360 | 469.658 | 50.028 | 12.995 | 1022.7–1093.7 |
| 500 | Draft, repeat | 1450 | 499.983 | 49.915 | 1.761 | 987.4–999.7 |
| 5000 | RPi.GPIO wrapper | 9413 | 3246.227 | 50.104 | 11.032 | 107.4–162.7 |
| 5000 | Draft | 14500 | 4999.755 | 48.628 | 0.237 | 60.6–110.5 |

A preceding independent draft capture at 500 Hz measured 499.984 Hz and
49.916% duty across 1450 complete cycles, consistent with the repeat's means.

In these short runs, the draft's mean frequency is substantially closer to the
request. That is not equivalent to uniformly better jitter: at 50 Hz its period
standard deviation is higher than the baseline, although the baseline has a
larger systematic period error. At 5 kHz, the draft maintains its period but
shows significant pulse-width variation and mean duty bias: high pulses range
down to 60.6 µs against a roughly 100 µs target. Frequency alone therefore
cannot establish waveform quality or drop-in suitability.

CPU statistics collected during these runs include initialization and cleanup,
so they are not a steady-state CPU benchmark. Required follow-up includes longer
repeated captures, CPU/I/O load, multiple outputs, more duty fractions and
frequencies, direct deinit/endpoint tests, and comparison on Pi 5 and older
boards. No current Blinka backend should be replaced based on these results.

Retained bench virtual environment: `/tmp/blinka-pwm-pi4-scope.45yK7d/venv`.
