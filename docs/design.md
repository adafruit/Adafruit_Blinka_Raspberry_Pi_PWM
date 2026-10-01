# Implementation and compatibility notes

Experimental implementation of CircuitPython's `pwmio.PWMOut` for Raspberry Pi.
The public interface accepts Blinka pins, preserves arbitrary-GPIO software PWM,
and is intended to support existing CircuitPython libraries without changes.
This draft is for evaluation before any Blinka backend replacement.

## Current implementation

- CircuitPython constructor, 16-bit duty cycle, fixed or variable frequency,
  context managers, and explicit/idempotent `deinit()`.
- Native C worker per output, using monotonic absolute deadlines and no Python
  calls or GIL in the waveform loop. Missed periods are skipped, not replayed.
- GPIO character-device v2 output; official `gpiod` Python bindings own the
  single-line request and the worker uses its file descriptor directly.
- Controller discovery by label (`pinctrl-bcm2835`, `pinctrl-bcm2711`,
  `pinctrl-rp1`), independent of changing `gpiochip` numbers.
- Constant low/high for duty cycles 0/65535 without a repeating timer.
- Kernel line ownership, worker error reporting, cleanup, and fork detection.
- No overlays, reboot, daemon, SWIG, or direct SoC register access for this engine.

The software engine configures 1–10000 Hz. This is **not a verified usable
frequency range or a performance guarantee**. Linux scheduling and GPIO ioctl
latency affect actual frequency, pulse width, and jitter. At high frequencies,
late edges can shorten or eliminate pulses. There is no guarantee of 16-bit
physical timing resolution. Matching or exceeding RPi.GPIO/lgpio is an acceptance
criterion that still needs measurements, especially on Pi 1/Zero.

The target is Pi 1 through Pi 5, including Compute Modules, with Python 3.9+ on
a Linux kernel supporting GPIO character-device v2 (5.10+). Older kernels and
unrecognized GPIO controller labels are not supported by this draft. Blinka's
extra `period` and `enabled` properties are not implemented yet; the public
CircuitPython `PWMOut` surface is the initial compatibility target.

## Install from this draft

On a Raspberry Pi, in a virtual environment:

```sh
python3 -m pip install .
```

Until prebuilt wheels are published, the source build needs a C compiler and
matching Python development headers (`python3-dev build-essential` for the
distribution's Python on Raspberry Pi OS). `gpiod` is a compiled dependency too;
its wheel coverage must be checked for each supported architecture/interpreter.
There are currently no published wheels or PyPI release for this draft.

Normal operation requires permission to access the GPIO character devices.
Raspberry Pi OS normally grants this through the `gpio` group. Installing the
package does not edit system permissions. GPIOs already claimed by a kernel
driver, overlay, or another character-device consumer cannot be used.

## Use with existing CircuitPython libraries

```python
import board
from adafruit_blinka_raspberry_pi_pwm import PWMOut
from adafruit_motor import servo

with PWMOut(board.D18, frequency=50) as pwm:
    motor = servo.Servo(pwm)
    motor.angle = 90
    # Keep this context alive for as long as output is needed.
    input("Press Enter to stop PWM")
```

BCM GPIO integers are also accepted (`PWMOut(18, frequency=50)`). They are GPIO
numbers, not physical header pin numbers. A Blinka Pin with `(chip, offset)` as
its `id` is supported when the chip is a recognized Raspberry Pi controller.

`frequency` is writable only with `variable_frequency=True`, as specified by
CircuitPython. The existing Blinka implementations are more permissive; testing
must identify applications relying on that difference before migration. Duty
and frequency changes are queued for the next cycle boundary. At 1 Hz, that may
take up to one second. Deinitialization interrupts waits immediately, joins the
worker, drives low, and releases the line; it does not wait for a complete cycle.

The implementation does not import Blinka, avoiding a circular dependency.
Blinka can expose this class directly as `pwmio.PWMOut`; see
[the draft integration patch](blinka-integration.patch). Blinka is not
modified or switched by installing this package. Existing RPi.GPIO pins may
bypass character-device ownership, so never drive a pin through two backends
simultaneously. Create PWM objects after starting multiprocessing children;
existing objects cannot be used in a forked child.

## Tests

```sh
python3 -m pip install -e '.[test]'
python3 -m pytest
```

API tests exercise actual `adafruit_motor.servo.Servo` and `DCMotor` classes
with a recording backend, plus validation, lifecycle, discovery, and error paths.
The production native scheduler is compiled and exercised with a C recording
writer; these tests do not touch GPIOs. Linux tests also build/use the production
extension to check invalid descriptor cleanup. Native scheduler tests can run
on macOS; the GPIO extension itself is Linux-only.

For deliberate hardware testing, `examples/pwm_loopback.py` drives one GPIO and
records edges on a second GPIO joined by a jumper. See
[the hardware validation plan](validation.md) for measurements and migration
gates. The full CircuitPython ecosystem has not been validated by these tests.
ServoKit drives an external PCA9685, so it is not a direct test of Pi GPIO PWM.

Initial checks passed on the development Mac (35 tests) and both ARM64 test
Pis (36 tests each), including Linux extension builds and read-only controller
discovery. These runs did not drive GPIOs or measure waveform performance.
See [the recorded draft results](draft-results.md).

## Next engines and release gates

Keep the arbitrary-pin software engine available. Evaluate kernel hardware PWM,
`pwm-gpio`, and Pi 5 RP1 PIO as additional engines behind the same interface.
Already-configured overlays should be reused; automatic setup, permissions,
resource sharing, and cleanup need a separate design. Acceleration must preserve
API behavior, ownership, independent frequencies, and requested pin coverage.

Before changing Blinka: measure against RPi.GPIO on Pi 4 and lgpio on Pi 5,
test older Pi generations, verify Python 3.9 through current CPython, ship usable
ARM64/ARMv7/ARMv6 wheels, and complete the validation gates. This package does
not address NeoPixel, PulseIn, or other timing APIs.

## Source and licensing

This draft is original MIT-licensed code. RPi.GPIO's `soft_pwm.c` was considered
as a reference direction but has not been copied or vendored. The implementation
uses the documented Linux GPIO v2 syscall ABI. `gpiod` is a separate dependency
with its own license. Any future reused sources must retain their attribution
and appropriate license notices.
