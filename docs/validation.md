# Validation and migration gates

No current Blinka backend should change until these gates are satisfied.

## Acceptance target

The migration target is performance on par with the existing Blinka backends
in the supported configurations, not perfect PWM or a hard realtime guarantee.
Use RPi.GPIO on earlier Pis and lgpio on Pi 5 as the measured references.
Compare actual frequency, pulse widths, late or omitted cycles, update response,
and resource use together under matched conditions and repeated captures.
Baseline imperfections do not excuse a material regression in the replacement.

Stricter waveform criteria, such as uninterrupted frequency changes or complete
outgoing pulses during every update, remain useful diagnostic targets. A failure
of such a criterion is not by itself a failure of baseline parity or the
CircuitPython API contract. Define baseline-derived acceptance thresholds before
new comparison runs; retain the original criteria and pass/fail results for
archived experiments. This clarification does not establish parity by itself or
relax behavioral compatibility, GPIO ownership, or cleanup requirements.

## Behavioral compatibility

Exercise defaults, duty 0/1/32767/65534/65535, fixed and variable frequency,
invalid arguments, independent outputs, context-manager exit, repeat deinit,
garbage collection, interpreter exit, signal exit, pin reuse, busy GPIOs,
permission failures, and GPIO driver failures. Explicit deinit reports output
errors. Abrupt process termination cannot promise a final low transition;
applications requiring a failsafe need appropriate circuitry. Software GPIO
requests close with their descriptors; hardware sysfs exports can remain active.

Use the actual Adafruit Motor Servo, ContinuousServo, DCMotor, and StepperMotor
classes and simpleio tone helpers. Verify type annotations/imports through a
test Blinka installation exporting the new class as `pwmio.PWMOut`.

Record Blinka extensions and existing behaviors that differ from CircuitPython,
particularly writable frequency without `variable_frequency=True`, float
arguments, `period`, and `enabled`. Make an explicit migration decision for each.

Check coexistence with gpiod digitalio, I2C, SPI, audio, NeoPixel output, and
Piomatter matrix refresh on distinct GPIOs. Measure both PWM pulse widths and
the other library's output under load; successful imports are not sufficient.
Test both startup orders, independent deinitialization, and same-process and
separate-process use. Select genuinely unused pins from the configured pinout:
Piomatter's Adafruit Matrix Bonnet pinout includes GPIO23, and Active3 includes
GPIO18. The current GPIO18/23 PWM-only captures are not coexistence tests.
Include pins sharing a hardware PWM channel, but expect independent frequencies
when the software engine is selected. Prevent two consumers driving the same
pin; do not silently steal a line from an overlay or another program.

## Timing comparisons

Use an external logic analyzer/scope for acceptance measurements. GPIO loopback
timestamps are a useful smoke test but are subject to interrupt latency and
buffer loss and cannot prove high-frequency waveform quality.

Compare RPi.GPIO and the draft on Pi 4, lgpio and the draft on Pi 5, using the
same pin, operating system, CPU governor, load, and measurement equipment.
Include 50 Hz servo pulses, 500 Hz, 1 kHz, 5 kHz, and 10 kHz, plus every higher
frequency actually used by supported library examples. The software engine rejects
frequencies above 10 kHz; document any resulting compatibility gap. The configured
hardware draft delegates frequency limits to the controller/driver and must be
qualified separately, including at frequencies above that software ceiling.

Measure actual frequency error, pulse-width error, min/median/p95/p99/max jitter,
duty/frequency update latency, CPU usage per output, skipped periods, and pin
release time. Include 1/2/4/8 concurrent outputs, uneven frequencies, duty
endpoints, tiny nonzero pulses, Python busy loops, I/O load, and CPU contention.
Set quantitative pass thresholds from existing backend measurements; do not
infer timing performance merely from accepting a frequency argument.

Separate setter return time from electrical application time. Use the same
public-API setter order in each comparison; combined diagnostic transitions
are not identical to sequential frequency and duty updates. Explicit settling
waits in a kernel prototype do not establish the native package's responsiveness,
and a quick queued update is not proof of immediate electrical application.

The default software engine uses a native thread per output and GPIO ioctl per edge.
The experimental `BLINKA_PWM_SHARED=1` engine shares a worker between outputs
with the same scheduling opt-in, but still performs separate GPIO ioctls. Compare
both engines with short-slice off and on, including independent retirement,
mixed frequencies, output error isolation, stopped-handle lifetime, concurrent
constructors, and fresh output construction in fork children. A slow ioctl can
delay the other outputs in a group; reduced CPU use alone is not acceptance.
System-call overhead may lose to RPi.GPIO's memory-mapped access. Measure this
before choosing whether non-PIO kernel PWM or another native engine is required.
The draft has no realtime scheduling priority and makes no hard realtime promise.

## Platform and packaging matrix

Test Pi 1/Zero (ARMv6), Pi 2/3/Zero 2 (32-bit and 64-bit where applicable), Pi 4,
Pi 5, and Compute Modules. Both test-pi4 and test-pi5 are ARM64; results on them
do not validate the other models. Verify controller labels and GPIO v2 support
on supported OS/kernel combinations, including kernels that renumber chips.

Test Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14. Python 3.9 needs an older
compatible gpiod release; verify pip's selection and API compatibility. ARMv6
wheel builds need separate attention; ARMv7 wheels cannot be installed on Pi 1
or original Zero. Verify wheels for both this extension and gpiod without a
compiler on a fresh virtual environment. Test package install/uninstall and
normal operation as a non-root user, without changing boot configuration.

## Accelerated engines

PIO PWM is out of scope, including selection through a kernel `pwm-pio` device.
Verify the package works without `/dev/pio*` and with other libraries consuming
PIO resources. It must not open PIO devices, claim state machines, load programs,
configure PIO transfers, or change another consumer's PIO state. Distinct-GPIO
NeoPixel/Piomatter coexistence tests are still required; avoiding PIO resource
allocation does not prove timing under their CPU load.

Evaluate configured non-PIO kernel PWM and pwm-gpio devices by discovery of
their device/driver/DT identity rather than hard-coded pwmchip numbers. Preserve
frequency/duty semantics and reject occupied channels. Test overlay availability,
privileged setup, reboot requirements, channel sharing, and pinmux restoration
before allowing automatic selection. Do not silently select an engine with a
smaller usable range or worse timing for a requested configuration.

The BCM/RP1 hardware draft still needs a focused physical gate: initial/repeated
export, ordinary 50/500-Hz and above-10-kHz waveforms, exact 0%/100% duty, period
shrinks and endpoint transitions, setter response, independent channels, and
shutdown LOW. Confirm that malformed, occupied, fanout, or unsupported configured
routes never fall through to software GPIO requests. `deinit()` releases a channel
but does not restore GPIO pinmux; validate and document that compatibility boundary
instead of treating the earlier software GPIO handoff tests as hardware evidence.
On RP1, inspect steady HIGH at high sample rate for full-duty notches, retain
shortened update-boundary pulses, and verify shutdown from inverse-zero HIGH.
Check the actual PWM clock against its device-tree assignment and leave the
separate cooling-fan provider untouched.
