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
