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
and accelerated backends. The CI workflow is provided but has not run on GitHub.
See [the validation gates](validation.md).
