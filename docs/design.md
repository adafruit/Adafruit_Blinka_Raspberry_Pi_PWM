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
- Linux workers set their own timer slack to 1 ns to avoid the default timer
  coalescing allowance distorting short pulses. Caller threads are unchanged;
  no sudo, real-time priority, or busy-waiting is required. Timing setup failure
  is reported during construction, with best-effort low cleanup.
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

An experimental scheduling opt-in is available before constructing outputs:

```sh
BLINKA_PWM_SHORT_SLICE=1 python your_program.py
```

Only the exact value `1` enables it; the default is off. On supported Linux
kernels (custom normal-policy slices are documented since 6.12), each new PWM
worker requests a 100 µs slice via `sched_getattr`/`sched_setattr`. The caller's
settings, inherited nice value, flags, utilization hints, and CPU affinity are
unchanged. Non-`SCHED_OTHER` workers are left alone. Unsupported/denied syscall
requests silently retain the inherited setup; GPIO PWM remains available on
older kernels. It needs no daemon, `chrt` executable, sudo, or real-time policy.
This is a latency optimization, not a timing guarantee, and remains opt-in
pending longer loaded-system and other-board evaluation. The constructor's
CircuitPython-compatible signature is unchanged.

A second experimental opt-in selects the shared non-PIO scheduler:

```sh
BLINKA_PWM_SHARED=1 python your_program.py
# Combine with BLINKA_PWM_SHORT_SLICE=1 to evaluate the 100 us slice too.
```

The exact value `1` enables it, read when each output is constructed. Both
options remain off by default; the existing per-output engine is retained for
comparisons. Shared outputs use one worker per short-slice setting per process
(normally one worker, at most two healthy groups if the environment changes).
Each group inherits its first constructor's worker scheduling settings; later
outputs do not change those settings. GPIO requests, periods, pending updates,
missed-cycle counts and asynchronous writer errors remain per output. Due falls
are serviced before other rises, successful unchanged levels avoid redundant
ioctls, and missed cycles are skipped. Updates still apply at the next cycle
boundary; steady endpoints can change immediately when the worker wakes.

Stopping one output removes it under the worker lock and attempts low without
stopping the survivors. The last active output wakes and joins its worker;
stopped handles keep their metadata alive until destruction. Forked handles
remain unusable, but a child can construct fresh outputs with a fresh registry.
A writer failure attempts low and disables only that output; worker timing/wait
failures affect the whole group. Each ioctl is still synchronous and per GPIO:
a delayed write can delay other outputs, and this is not batched or phase-locked
GPIO output. Measurements must establish whether reduced worker overhead helps
without worsening pulse-width tails. The opt-in is not a migration decision.

The target is Pi 1 through Pi 5, including Compute Modules, with Python 3.9+ on
a Linux kernel supporting GPIO character-device v2 (5.10+). Older kernels and
unrecognized GPIO controller labels are not supported by this draft. Blinka's
extra `period` and `enabled` properties are not implemented yet; the public
CircuitPython `PWMOut` surface is the initial compatibility target.

## Portability boundary

The native scheduler uses generic POSIX timing/threading and the extension's
writer uses the Linux GPIO character-device v2 ABI. Timer slack and the optional
normal-policy slice are Linux mechanisms, not Pi-specific mechanisms. No BCM/RP1
register access, DMA or PIO is used. Raspberry Pi-specific behavior is in the
Python adapter: recognized controller labels, BCM numbering and Blinka pin
identity conversion. Keeping that adapter separate allows future board adapters;
it does not currently make other SBCs supported.

Candidate future targets are boards selecting Blinka's generic `sysfs_pwmout`,
including Banana Pi, Coral and ODROID families. That backend controls Linux PWM
devices through `/sys/class/pwm` and board-defined `pwmOuts`; it is not sysfs GPIO
bit-banging. Preserve usable non-PIO kernel PWM rather than automatically replace
it with userspace software timing. A GPIO-v2 software fallback could add outputs
where suitable lines are available. Each board needs explicit GPIO controller/
line mapping, permissions/pinmux/ownership checks and waveform validation.
Its `(pwmchip, channel)` mapping is not a `(gpiochip, line)` mapping. GPIOs claimed
by an existing PWM driver must not be stolen for software output. Neither wider
platform selection nor a kernel-PWM engine is implemented in this draft.

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

Keep the arbitrary-pin, non-PIO software engine. PIO PWM is excluded from the
planned backends, including kernel `pwm-pio` acceleration. The package must not open
PIO devices, claim state machines, load PIO programs, or configure PIO transfers.
This avoids consuming the resources used by Pi 5 NeoPixel and Piomatter drivers;
it does not establish coexistence on shared GPIOs or eliminate CPU-load effects.

The current [NeoPixel implementation](https://github.com/adafruit/Adafruit_Blinka_Raspberry_Pi5_Neopixel/blob/main/src/main.cpp)
opens PIO0 and claims a state machine and program space. The current
[Piomatter implementation](https://github.com/adafruit/Adafruit_Blinka_Raspberry_Pi5_Piomatter/blob/main/src/include/piomatter/piomatter.h)
also claims a state machine on PIO0 and loads a 32-instruction program. Its
[bundled RP1 interface](https://github.com/adafruit/Adafruit_Blinka_Raspberry_Pi5_Piomatter/blob/main/src/piolib/include/rp1_pio_if.h)
defines 32 instruction slots and four state machines: spare state machines alone
do not imply space for a separate PWM program. These are source observations,
not completed mixed-library hardware tests. Avoiding PIO leaves those resources
to other libraries; coexistence on distinct GPIOs still needs validation.

Evaluate the experimental shared native software scheduler for multi-output performance.
[lgpio v0.2.2's transmit worker](https://github.com/joan2937/lg/blob/v0.2.2/lgPthTx.c)
services a list of PWM records in one thread using absolute monotonic sleeps;
PWM edges use individual writes, unlike its grouped waveform path. This is a
reference architecture, not code incorporated into this draft or proof that a
shared scheduler will improve our jitter. Preserve independent frequencies,
interruptible updates/shutdown, per-output error reporting, and missed-period
skipping when evaluating such a change.

Evaluate non-PIO kernel hardware PWM and `pwm-gpio` as possible additional
engines behind the same interface.
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
