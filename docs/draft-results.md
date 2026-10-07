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

## Worker timer-slack fix and loaded Pi 4 evaluation

Investigation of the first 5 kHz capture found 724 highs below 80 µs across
14,500 complete cycles, approximately one every 4 ms. The bench process's
default timer slack was 50,000 ns; the kernel configuration has `CONFIG_HZ=250`.
Linux's [timer-slack allowance](https://www.man7.org/linux/man-pages/man2/PR_SET_TIMERSLACK.2const.html)
permits coalescing of timed waits, including `pthread_cond_timedwait`, and is
inherited by new threads. A default/reduced/restored/reduced experiment found
725/14,500 and 719/14,500 highs below 80 µs with 50,000 ns slack, versus none
across the two 14,500-cycle captures with 1 ns slack. This isolates timer slack
as the cause of the recurring distortion; the exact kernel wakeup source behind
its 4 ms periodicity was not traced.

The resulting native worker patch sets its own allowance to 1 ns, leaving the
caller unchanged. Construction waits for worker timing setup and reports its
failure synchronously, with best-effort low cleanup. No real-time priority,
busy-waiting, sudo, global timer setting, or governor change is used.

The patched source distribution built and installed in the retained bench
virtual environment, and all 44 Linux tests passed. Regression tests check the
actual worker's timer slack, an unchanged caller setting deliberately set to
250,000 ns, and three injected timing-setup failure paths, including cleanup
failure preserving the original error and duplicated-descriptor closure.
The Mac suite passed 40 tests with four Linux-only cases skipped; the native
scheduler also passed address/undefined-behavior sanitizers. Lint, formatting,
and warning-as-error documentation builds passed.

The following physical captures use that installed patch, **without a caller
timer-slack override**. Caller slack remained 50,000 ns before and after every
run. Hardware, sample rate, capture duration, trimming, and RPi.GPIO baseline
are the same as above. Loaded runs add four independent Python CPU burners,
started before PWM construction and verified alive through the active interval.
These contend for the Pi's four cores; they perform no disk I/O or GPIO access.
Each burner has a bounded lifetime and is terminated/joined after the capture.

| Requested Hz / duty | Backend / load | Cycles | Mean Hz | Mean duty % | Longest period, µs | High-width min–max, µs |
| --- | --- | --- | --- | --- | --- | --- |
| 5000 / 50% | Patched, idle | 14498 | 5000.593 | 49.523 | 220.5 | 81.5–110.7 |
| 5000 / 50% | Patched, CPU load | 14403 | 4967.799 | 49.267 | 4200.5 | 79.1–3127.3 |
| 5000 / 50% | Patched, CPU load repeat | 14478 | 4993.844 | 49.455 | 4079.1 | 20.6–204.4 |
| 5000 / 50% | RPi.GPIO, CPU load | 9233 | 3184.647 | 49.996 | 365.9 | 126.8–165.9 |
| 500 / 50% | Patched, idle | 1449 | 500.047 | 49.915 | 2007.1 | 990.8–1003.1 |
| 500 / 50% | Patched, CPU load | 1441 | 497.284 | 49.685 | 5999.3 | 985.1–1001.5 |
| 50 / ~7.5% | Patched, idle | 144 | 50.002 | 7.480 | 20004.4 | 1494.6–1500.9 |
| 50 / ~7.5% | Patched, CPU load | 143 | 49.657 | 7.445 | 39997.2 | 1489.3–1500.1 |
| 5000 / 25% | Patched, idle | 14499 | 5000.266 | 24.503 | 211.0 | 39.6–63.7 |
| 5000 / 75% | Patched, idle | 14499 | 5000.256 | 74.609 | 202.5 | 148.2–161.8 |

The servo-like runs use duty 4915, requesting approximately 1500 µs highs;
no servo was connected or exercised. Quarter/three-quarter duty values are
16384/49151. A small duty bias and occasional outliers remain even at idle.
The patched idle 5 kHz/50% capture has no highs below 80 µs. Each loaded 5 kHz
capture has one such high, not the earlier approximately 5% recurring pattern.

**The loaded waveform acceptance gate has not passed.** Absolute deadlines
maintain good average frequency, but scheduling delays still produce long gaps,
skipped pulses, and sometimes stretched highs. The loaded 500 Hz capture has
four periods longer than 3 ms, and the servo-like loaded capture has a roughly
40 ms period instead of 20 ms. RPi.GPIO's loaded 5 kHz run is substantially
slower than requested but has much smaller worst-case period/pulse excursions
in this short comparison. The draft therefore cannot yet be claimed to match
or exceed the existing backend's waveform quality under load.

All ten patched/baseline captures ended low with more than 0.22 s of quiet tail
after explicitly commanding zero duty and then deinitializing. No load/PWM test
process remained running afterward. Raw captures are retained locally in
`work/pwm-measurements/patched-*` and `rpi-gpio-5000hz-cpuload`; these large
measurement artifacts are not checked into the package repository.

Next: investigate/bound loaded-system scheduling excursions and evaluate
acceleration if needed, then longer repeated captures and waveform coverage on
Pi 5, Pi 3B+, and Zero. These results do not justify replacing Blinka's backend.

## Loaded-system scheduling investigation

Further five-second captures change the interpretation of the preceding short
comparison: **RPi.GPIO also exhibits millisecond-scale gaps under CPU load.**
Its repeated 5 kHz-request capture measured 3184.816 Hz, with one period over
1 ms across 15,603 complete cycles and a longest period of 4308.9 µs. The
earlier 365.9 µs maximum was an observed result of one short run, not a bound.

Both backends' actual native threads used `SCHED_OTHER`, nice 0, and affinity
to CPUs 0–3. RPi.GPIO is not using a privileged priority on this bench. The
[RPi.GPIO scheduler source](https://sources.debian.org/src/rpi.gpio/0.7.1~a4-1/source/soft_pwm.c/)
uses relative sleeps after direct GPIO writes. The draft uses absolute deadlines
and skips elapsed periods instead of replaying them. Consequently, delays slow
the original's waveform, whereas the draft preserves phase and can omit or
shorten pulses when it resumes late. Both can stretch highs while not running.

A separate diagnostic shared library compiled the current production scheduler
with a timed-wait wrapper and a recording GPIO writer using the same v2 ioctl.
It did not replace the installed package. It recorded wall time around writes
and waits, thread CPU time across waits, and their requested deadlines into a
preallocated buffer; CSV output occurred only after the worker was joined.
Instrumentation adds overhead, so its waveform is not a performance benchmark.

With four unrestricted CPU burners, the instrumented worker had ten waits more
than 1 ms late in the approximate steady-state window. Its worst wait returned
4983.484 µs after its deadline while consuming only 7.759 µs of thread CPU time.
Matching all 24,843 commanded highs to analyzer rising edges linked that wait
to the physical 5199.4 µs rising-edge gap. The longest GPIO ioctl in the same
window was 164.723 µs; no millisecond-scale write was recorded. This localizes
the major delays to blocked/off-CPU timed waits rather than slow GPIO writes.
Exact timer-expiry versus runnable-queue latency was not traced: kernel tracing
was unavailable to the test user and scheduler wait accounting was disabled.

As a controlled contention check, keeping PWM on CPU3 and all four burners on
CPUs0–2 reduced the instrumented worker's worst wait lateness to 599.093 µs,
with no waits over 1 ms late. The uninstrumented package's longest period was
403.1 µs under the same arrangement. This supports CPU contention/scheduling
as the dominant cause. It is not an equivalent full-four-core stress test or a
portable solution for a single-core Zero. A matched-edge-rate capture requesting
3185 Hz from the draft still had a 4396.8 µs maximum period, so the discrepancy
is not explained solely by the draft's higher actual edge rate at a 5 kHz request.

### Temporary shorter normal-policy time slice

The bench default normal-policy slice was 2,100,000 ns. A diagnostic command
`chrt -o -T 100000 -p 0 WORKER_TID` requested a 100 µs slice for only the test
PWM thread before starting the waveform. It succeeded as the regular `pi`
user without sudo. Policy remained `SCHED_OTHER`, nice remained 0, all four
cores remained available, and the caller retained its 2.1 ms slice. Burners
were unrestricted on all four CPUs; no core was reserved. The
[custom normal-policy slice interface](https://man7.org/linux/man-pages/man1/chrt.1.html)
is documented for Linux 6.12 onward; the bench uses 6.18.50.

| Five-second loaded capture | Worker slice | Complete cycles | Mean Hz | Periods >1 ms | Longest period, µs |
| --- | --- | --- | --- | --- | --- |
| Patched, initial investigation | Default | 24355 | 4970.485 | 9 | 4396.9 |
| Patched, short-slice first | 100 µs | 24499 | 5000.045 | 0 | 205.7 |
| Patched, fresh default restored | Default | 23583 | 4817.998 | 45 | 4399.6 |
| Patched, short-slice repeat | 100 µs | 24459 | 4991.865 | 2 | 4211.4 |
| RPi.GPIO, repeat | Default | 15603 | 3184.816 | 1 | 4308.9 |

These small samples show a promising reduction, **not elimination** of large
gaps or proof of parity with RPi.GPIO. Short-slice 500 Hz and servo-like 50 Hz
captures had no periods over 150% of their targets: maxima were 2061.0 µs and
20014.7 µs respectively. Pulse-width jitter remained: high ranges were
940.7–1193.4 µs at 500 Hz/50% and 1485.3–1589.2 µs at 50 Hz/~1500 µs.

No production scheduler change was made during this investigation. A candidate
next improvement is a best-effort worker-only short slice on supported kernels,
preserving the inherited policy/nice value and falling back safely elsewhere.
It cannot be sold as a hard timing guarantee or a replacement for evaluating
kernel/hardware-assisted PWM where tighter timing is needed. Older-kernel,
other-board, multi-output, power/CPU-cost, and longer-run validation remain open.

Diagnostic sources and captures are retained outside the repository in
`work/pwm-measurements`; remote instrumentation is in
`/tmp/blinka-pwm-sched-probe.0BcF11`. All captures ended low, all temporary
workers exited, and a fresh process retained the default timer slack and slice.

## Opt-in short slice and longer loaded captures

The draft now implements a default-off, best-effort short-slice option selected
by `BLINKA_PWM_SHORT_SLICE=1` when an output is constructed. Only the PWM worker
requests a 100 µs normal-policy slice; inherited policy/nice values are preserved,
and unsupported or denied requests fall back to normal scheduling. This does not
enable real-time priority, reserve a CPU, or change the public PWMOut constructor.
See [the design](design.md) for the interface and limitations.

The installed build passed all 57 tests on the Pi 4, including mocked unsupported,
denied, non-normal-policy, and future-ABI scheduling paths. The local macOS run
passed 45 tests with 12 Linux-only tests skipped. Every enabled hardware capture
observed a 100,000 ns worker slice and the caller's unchanged 2,100,000 ns slice.

**The following longer comparison is thermally confounded and is not an
acceptance result.** The bench had no fan. Temperature snapshots reached
84.724°C; firmware flags progressed from zero to `0x80008` and later `0xe0008`.
According to the [Raspberry Pi firmware flag definitions](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled),
these record an active soft temperature limit and historical frequency capping
and throttling. Before/after readings are not a continuous trace, so they do not
establish when each event occurred within a capture. Cool, repeated tests are
required before comparing backends or choosing a default. The measurements are
retained as observations of this stressed, changing thermal environment.

Each case used four unrestricted CPU burners on all four cores, no affinity or
privileged-priority override, and a 20-second commanded waveform. GPIO18 used
Saleae channel 0; newly connected GPIO23 used channel 1, both with common ground.
Digital sampling remained 10 MS/s with no glitch filter. GPIO18 had two rounds
with reversed backend order; GPIO23 had one round. Each analysis trimmed 50 ms
from each end of the waveform. The table combines the two GPIO18 rounds; GPIO23
has only one capture per backend. CPU cost is the PWM process's active-interval
user plus system CPU time as a percentage of one core, excluding the burners.

| GPIO / requested Hz | Backend | Mean Hz | Long gaps | Longest period, µs | PWM CPU, % of one core |
| --- | --- | --- | --- | --- | --- |
| 18 / 5000 | RPi.GPIO | 3185.500 | 10 | 4075.6 | 3.94 |
| 18 / 5000 | Draft, opt-in off | 4946.987 | 149 | 6016.2 | 9.74 |
| 18 / 5000 | Draft, opt-in on | 4993.547 | 27 | 4201.8 | 9.42 |
| 18 / 500 | RPi.GPIO | 472.429 | 1 | 5308.7 | 0.75 |
| 18 / 500 | Draft, opt-in off | 499.258 | 15 | 6000.9 | 1.17 |
| 18 / 500 | Draft, opt-in on | 500.012 | 0 | 2103.9 | 1.14 |
| 18 / 50 | RPi.GPIO | 49.704 | 0 | 23569.2 | 0.08 |
| 18 / 50 | Draft, opt-in off | 49.749 | 10 | 40000.5 | 0.13 |
| 18 / 50 | Draft, opt-in on | 50.001 | 0 | 20019.9 | 0.13 |
| 23 / 5000 | RPi.GPIO | 3169.663 | 4 | 5515.7 | 4.44 |
| 23 / 5000 | Draft, opt-in off | 4988.012 | 17 | 4053.1 | 11.23 |
| 23 / 5000 | Draft, opt-in on | 4990.621 | 28 | 4218.2 | 11.18 |

Here a long gap is a complete rising-edge period exceeding 150% of that
capture's median period, not 150% of the requested period. This separates rare
interruptions from RPi.GPIO's systematic slowing. It is not a count of precisely
identified missing pulses. GPIO18's observed gap counts improve with the opt-in;
GPIO23's single round does not show a consistent improvement. Thermal conditions
and limited repetitions prevent attributing that difference to the pin itself.
All backends still exhibited millisecond-scale excursions at 5 kHz. The draft's
greater actual edge rate also comes with a greater observed CPU cost.

Half-duty captures requested 32768. At 50 Hz the request was 4915: the existing
Blinka wrapper rounds this to **7%** for RPi.GPIO, whereas the draft requests
approximately 7.5% (1500 µs highs). These are not identical effective duty values;
no physical servo was connected. Pulse-width tails also remain important: for
example, GPIO18's enabled 5 kHz highs ranged from 19.5 to 3956.8 µs, despite a
nominal 100 µs request. Average frequency is not sufficient evidence of waveform
quality or CircuitPython peripheral compatibility.

GPIO23 successfully produced PWM without requiring a hardware-PWM-capable pin.
A preliminary three-second enabled 500 Hz idle capture measured 500.025 Hz with
no long gaps and highs of 998.3–1010.3 µs. This is functional single-output
coverage, not simultaneous two-output validation. All 21 loaded captures ended
low with at least 0.21 s of quiet tail; both GPIO lines were unclaimed afterward,
and no PWM/load processes remained. Raw captures and metadata remain outside the
package repository in `work/pwm-measurements/long20-*`.

Next: add cooling and repeat under consistent thermal conditions. The measurement
harness now rejects starts above 65°C or with any firmware limiting/history flags,
and rejects saved results ending above 75°C or with any such flags. These are
conservative bench acceptance limits, not hardware safety limits. Starting with
clear history allows the final flags to detect transient limiting; a flagged run
requires a reboot before another accepted comparison. Rejected captures are
preserved, and the harness exits unsuccessfully to stop an unattended sequence.
The option remains off by default; multi-output, older kernels, Pi 5, Pi 3B+, and
Zero waveform coverage are still outstanding.

## Cooled, repeated loaded comparisons

After the thermally confounded batch, the bench was powered off and fitted with
an [Adafruit 3082 heatsink](https://www.adafruit.com/product/3082) and airflow from
an [Adafruit 3368 5V fan](https://www.adafruit.com/product/3368). The temporary Fan
SHIM was removed, freeing GPIO18; the fan uses only power and ground. Rebooting
cleared firmware history. The isolated environment was rebuilt from the same
opt-in draft source archive, with gpiod 2.5.0. The baseline again used Debian's
RPi.GPIO 0.7.1a4 and the identical Blinka wrapper, not another RPi.GPIO copy.
All 57 no-hardware regression tests passed in the rebuilt Pi environment.

All **24 twenty-second, four-burner captures passed the thermal checks**.
Before/after snapshots ranged from 34.076 to 52.095°C, and every firmware reading
remained `throttled=0x0`. These are endpoint readings plus persistent firmware
history, not a continuous temperature trace. GPIO18 was tested at 5000, 500,
and 50 Hz; GPIO23 was tested at 5000 Hz. Every combination had two rounds,
ordered RPi.GPIO/off/on then on/off/RPi.GPIO. The same requested duties, sampling,
steady-state trimming, gap definition, and CPU accounting described above apply.
No affinity, real-time priority, governor, or kernel configuration was changed.

| GPIO / requested Hz | Backend | Mean Hz | Long gaps | Longest period, µs | High range, µs | PWM CPU, % of one core |
| --- | --- | --- | --- | --- | --- | --- |
| 18 / 5000 | RPi.GPIO | 3181.804 | 47 | 5401.7 | 109.8–5244.0 | 3.90 |
| 18 / 5000 | Draft, opt-in off | 4989.903 | 30 | 5807.2 | 1.0–5804.8 | 9.54 |
| 18 / 5000 | Draft, opt-in on | 4999.627 | 1 | 1058.7 | 40.9–1056.4 | 9.60 |
| 23 / 5000 | RPi.GPIO | 3185.903 | 9 | 4243.9 | 118.7–4085.5 | 3.88 |
| 23 / 5000 | Draft, opt-in off | 4975.731 | 52 | 5798.5 | 35.7–5132.2 | 9.43 |
| 23 / 5000 | Draft, opt-in on | 4995.289 | 18 | 4211.7 | 2.3–4029.4 | 9.69 |
| 18 / 500 | RPi.GPIO | 472.864 | 1 | 5884.5 | 1010.1–4826.7 | 0.68 |
| 18 / 500 | Draft, opt-in off | 500.038 | 0 | 2442.9 | 560.7–1809.0 | 1.07 |
| 18 / 500 | Draft, opt-in on | 500.035 | 0 | 2065.6 | 937.3–1085.7 | 1.06 |
| 18 / 50 | RPi.GPIO | 49.687 | 0 | 24073.1 | 1442.2–1565.2 | 0.074 |
| 18 / 50 | Draft, opt-in off | 49.722 | 11 | 40002.5 | 1388.6–1561.4 | 0.112 |
| 18 / 50 | Draft, opt-in on | 49.998 | 0 | 20015.1 | 1485.8–1500.7 | 0.111 |

Each row combines approximately 39.8 analyzed seconds from two captures. Mean
frequency and duty are derived from combined cycle durations, rather than an
unweighted average of the per-run values; gap counts sum the per-run counts.
Gap counts per wall-time window must also be interpreted alongside the different
actual edge rates: the draft generated roughly 199,000 cycles in each 5 kHz row,
versus roughly 127,000 for RPi.GPIO. At 50 Hz, RPi.GPIO's effective request remains
7%, versus the draft's approximately 7.5%, so the nominal high widths differ.

The opt-in reduced long-gap counts relative to the draft's default slice in
both pins' 5 kHz samples and removed the observed 50 Hz skipped periods. At
500 Hz, neither draft mode had long gaps, but the default mode still had five
highs outside ±20% of its nominal 1000 µs width; the opt-in had none. Thus a
period-only test would overlook relevant pulse-width distortion. Average duty
with the opt-in was 49.513% on GPIO18 at 5 kHz, 49.525% on GPIO23 at 5 kHz,
49.942% at 500 Hz, and 7.495% at 50 Hz. A small high-frequency duty bias remains.

**The opt-in is still not a hard timing guarantee or a proven drop-in replacement
across Raspberry Pi models.** GPIO23's enabled 5 kHz runs had 17 and 1 long gaps,
including a 4211.7 µs period and a 2.3 µs high. GPIO18's corresponding counts were
0 and 1. The variation does not establish a pin-specific cause, and GPIO23 did
not beat RPi.GPIO's gap count in these samples. The draft sustains a higher actual
frequency but uses roughly 9.6% of one core at 5 kHz, versus roughly 3.9% for the
slower baseline. Lower-frequency results are encouraging, but neither these
short repetitions nor average frequency alone establish peripheral compatibility.

All captures ended low with at least 0.21 s of quiet tail. After the batch both
GPIOs were unclaimed, no PWM/load processes remained, and a fresh process retained
normal policy, 50,000 ns timer slack, and a 2,100,000 ns slice. A preliminary
three-second GPIO18/500 Hz idle smoke capture also passed after cooling was added.
Captures and metadata are retained in `work/pwm-measurements/cooled20-*` outside
the package repository; the rebuilt remote environment is
`/tmp/blinka-pwm-cooled.7d40hB` and will not survive another clearing of `/tmp`.

The option remains **off by default**. Next validation should exercise simultaneous
outputs and additional Raspberry Pi models, including older kernels that must
use the safe scheduling fallback. This single-output Pi 4 evidence does not
justify switching Blinka's backend yet.

## Simultaneous outputs on the cooled Pi 4

The next batch drove GPIO18/channel0 and GPIO23/channel1 together, using the
same build, cooling, 10 MS/s sampling, and four unrestricted CPU burners. Eighteen
20-second captures covered two outputs at 5000 Hz, two at 500 Hz, and a mixed
50 Hz/500 Hz pair. Each profile/backend combination had two rounds in reversed
backend order. Matching-frequency runs requested duty 32768 on both pins; the
mixed case requested duty 4915 on GPIO18 and 32768 on GPIO23. Output starts were
sequential, not phase-synchronized; no synchronized-phase guarantee is claimed.
Each output was independently analyzed with the same 50 ms end trimming and
long-gap definition. Three additional 20-second captures stopped and deinitialized
GPIO18 halfway through while GPIO23 continued. All **21 captures passed thermal
checks**: snapshots ranged from 34.076 to 51.121°C and all firmware flags were zero.

In the following table paired values are **GPIO18 / GPIO23**, combining the two
full-duration rounds; CPU cost includes both workers as a percentage of one core.

| Requested Hz, 18 / 23 | Backend | Mean Hz, 18 / 23 | Long gaps, 18 / 23 | Longest period, µs, 18 / 23 | Combined PWM CPU, % |
| --- | --- | --- | --- | --- | --- |
| 5000 / 5000 | RPi.GPIO | 3183.764 / 3185.661 | 24 / 7 | 4351.0 / 4303.9 | 7.79 |
| 5000 / 5000 | Draft, opt-in off | 4799.181 / 4964.846 | 404 / 86 | 5600.8 / 4879.6 | 18.61 |
| 5000 / 5000 | Draft, opt-in on | 4995.670 / 4995.972 | 39 / 38 | 4200.5 / 4203.5 | 19.05 |
| 500 / 500 | RPi.GPIO | 471.512 / 471.612 | 24 / 19 | 7162.2 / 7157.9 | 1.12 |
| 500 / 500 | Draft, opt-in off | 498.727 / 499.204 | 50 / 31 | 4873.2 / 4867.7 | 2.14 |
| 500 / 500 | Draft, opt-in on | 499.983 / 499.405 | 0 / 12 | 2031.9 / 10004.2 | 2.18 |
| 50 / 500 | RPi.GPIO | 49.696 / 472.451 | 0 / 7 | 23999.6 / 8263.8 | 0.76 |
| 50 / 500 | Draft, opt-in off | 49.721 / 498.622 | 11 / 54 | 40003.3 / 4927.4 | 1.17 |
| 50 / 500 | Draft, opt-in on | 49.998 / 499.978 | 0 / 0 | 20119.1 / 2139.1 | 1.17 |

Functionally, both outputs operated at matching and different frequencies. In
enabled runs both workers had 100,000 ns slices while the caller retained
2,100,000 ns. A three-second idle 500 Hz smoke test measured approximately
500.008 Hz on both pins with no long gaps. In the independent-release cases,
GPIO18 was deinitialized at about 10.000 seconds and remained low for more than
10.21 seconds of capture tail; GPIO23 continued to the 20-second endpoint and
then had a normal 0.21–0.30 second low tail. This verifies independent shutdown,
not reuse of a released pin or dynamically changing a surviving output's frequency.

**Multi-output timing is not uniformly better than the original.** The opt-in
reduced the draft's gap counts and preserved near-requested average rates, but
dual 5 kHz had more long gaps than RPi.GPIO in these samples. The worse channel
switched between the enabled 5 kHz repeats (counts 33/0 then 6/38), reinforcing
that the preceding observations do not identify a fixed pin-specific cause.
Enabled 5 kHz highs ranged from 2.6–3752.0 µs on GPIO18 and 18.1–2678.1 µs on
GPIO23, against nominal 100 µs requests. At dual 500 Hz, GPIO23 had a 10004.2 µs
period and an 8993.7 µs high in one enabled run; the repeat had no long gaps.
That enabled worst period exceeds the baseline's observed worst period.

The mixed-frequency enabled runs had no long gaps, but pulse widths still varied:
GPIO18's nominal approximately 1500 µs highs ranged from 1384.2 to 1710.0 µs;
GPIO23's nominal 1000 µs highs ranged from 864.1 to 1150.6 µs. The original's
GPIO18 duty remains quantized to 7%, so its pulse-width target is different.
No physical servo or motor was attached. Independent-release runs also had
scheduling excursions; passing the lifetime check does not establish waveform
quality during or around deinitialization.

Every channel ended low with at least 0.21 seconds of quiet tail. Afterward both
GPIOs were unclaimed, no PWM/load processes remained, and a fresh process retained
normal policy and 50,000 ns timer slack. Sources and captures are outside the
package repository in `work/pwm-measurements/capture_multi_pwm.py` and `dual20-*`;
the shared generated control program has local no-hardware checks for two-output
lifecycle, constructor failure, active-wait failure, and thermal rejection.
Production code was unchanged during this batch. The short-slice option remains
off by default, and the loaded waveform acceptance gate is still open. Next:
physical Pi 5 captures, followed by wider board/kernel and output-update coverage.

## Loaded Pi 5 comparisons

The same runtime source archive was built in an isolated environment on a Pi 5
Model B Rev 1.0, with CPython 3.13.5 ARM64, kernel 6.12.75+rpt-rpi-2712, and
gpiod 2.5.0. All **57 no-hardware regression tests passed**. Default discovery
selected the `pinctrl-rp1` controller without a fixed gpiochip index. The baseline
used Debian's python3-lgpio/liblgpio1 0.2.2-1~rpt1+trixie (module reports
`lgpio.py_0.2.2.0`), with unmodified Blinka `lgpio_pin.py` and `lgpio_pwmout.py`
from commit `beb49bf8ea9305dacbd14b08525f234eda563c02`. No Blinka backend was
changed. Production PWM code was unchanged from the cooled Pi 4 batch.

The analyzer was moved to GPIO18/channel0 and GPIO23/channel1 with common ground.
Sampling remained 10 MS/s, with the same trimming, long-gap definition, duties,
and active-interval CPU accounting. Four unrestricted CPU burners provided load.
The governor remained `ondemand`; no affinity or real-time priority was applied.
Enabled draft workers recorded 100,000 ns slices while the caller retained
2,100,000 ns. Neither the draft nor these tests used PIO.

All **30 twenty-second loaded captures passed thermal checks**: before/after
snapshots ranged from 46.300 to 63.350°C, with `throttled=0x0` throughout those
readings. Eighteen single-output captures provided two rounds per frequency and
backend, in reversed backend order. Nine simultaneous-output captures provided
**only one round per profile/backend**, not repeated dual-output evidence. Three
more captures stopped GPIO18 halfway through while GPIO23 continued.

Single-output rows below combine two captures, approximately 39.8 analyzed
seconds each. Means are weighted by combined cycle durations; gap counts sum.
CPU percentages describe the PWM process as a fraction of one core, excluding
the separate load processes.

| GPIO18 requested Hz | Backend | Mean Hz | Long gaps | Longest period, µs | High range, µs | PWM CPU, % |
| --- | --- | --- | --- | --- | --- | --- |
| 5000 | lgpio | 5000.000 | 50 | 4759.5 | 3.8–4752.1 | 6.88 |
| 5000 | Draft, opt-in off | 4980.651 | 85 | 4800.4 | 0.7–4709.0 | 7.31 |
| 5000 | Draft, opt-in on | 4998.190 | 7 | 3987.6 | 13.4–3904.5 | 7.35 |
| 500 | lgpio | 500.001 | 18 | 5953.4 | 3.8–4000.5 | 0.728 |
| 500 | Draft, opt-in off | 498.568 | 29 | 6001.6 | 961.5–3600.8 | 0.780 |
| 500 | Draft, opt-in on | 500.000 | 0 | 2058.2 | 942.0–1147.2 | 0.792 |
| 50 | lgpio | 49.995 | 0 | 24001.1 | 4.7–4000.9 | 0.075 |
| 50 | Draft, opt-in off | 49.849 | 6 | 40004.7 | 1402.2–1521.0 | 0.081 |
| 50 | Draft, opt-in on | 50.000 | 0 | 20038.6 | 1463.2–1511.1 | 0.081 |

At 50 Hz the baseline converts duty 4915 to integer 7%, targeting 1400 µs,
whereas the draft targets approximately 1500 µs. lgpio's near-requested mean
frequency and zero long gaps do not imply correct pulse widths: the observed
high range still included approximately 5 µs and 4 ms pulses. The draft opt-in
improved these particular single-output samples, but 5 kHz still had millisecond
excursions. This is not a hard timing bound or a peripheral compatibility result.

The simultaneous-output table gives **GPIO18 / GPIO23** values from one
20-second capture per row. Matching-frequency requests used duty 32768 on both
pins; the mixed profile used duty 4915 on GPIO18. Starts were sequential, with
no promised phase relationship. CPU includes the whole PWM process.

| Requested Hz, 18 / 23 | Backend | Mean Hz, 18 / 23 | Long gaps, 18 / 23 | Longest period, µs, 18 / 23 | Combined PWM CPU, % |
| --- | --- | --- | --- | --- | --- |
| 5000 / 5000 | lgpio | 5000.002 / 5000.002 | 27 / 27 | 5155.6 / 5155.5 | 7.44 |
| 5000 / 5000 | Draft, opt-in off | 4974.471 / 4895.212 | 32 / 113 | 4198.4 / 4208.0 | 14.38 |
| 5000 / 5000 | Draft, opt-in on | 4998.846 / 4999.097 | 4 / 3 | 4200.1 / 3794.1 | 10.96 |
| 500 / 500 | lgpio | 500.000 / 500.000 | 8 / 8 | 5950.2 / 5950.1 | 0.787 |
| 500 / 500 | Draft, opt-in off | 498.543 / 498.744 | 15 / 13 | 5997.7 / 5997.5 | 1.538 |
| 500 / 500 | Draft, opt-in on | 500.000 / 500.000 | 0 / 0 | 2060.0 / 2008.4 | 1.184 |
| 50 / 500 | lgpio | 50.000 / 500.000 | 0 / 17 | 20049.0 / 5957.1 | 0.765 |
| 50 / 500 | Draft, opt-in off | 49.849 / 498.392 | 3 / 16 | 40008.1 / 5998.0 | 0.860 |
| 50 / 500 | Draft, opt-in on | 50.000 / 500.000 | 0 / 0 | 20008.3 / 2892.9 | 0.843 |

**Pulse-width acceptance remains open even when periods look good.** Enabled
dual 500 Hz included a 2004.5 µs GPIO18 high against a nominal 1000 µs request.
The enabled mixed run included a 2889.5 µs GPIO18 high against approximately
1500 µs, and GPIO23 highs ranged from 110.7 to 2891.3 µs. Enabled dual 5 kHz
also included a 0.6 µs GPIO23 high. No servo or motor was connected, and these
short samples cannot establish a maximum possible excursion.

lgpio's CPU cost rose from approximately 6.88% of one core for one 5 kHz output
to 7.44% for two, versus 7.35% to 10.96% for the enabled draft in these samples.
This suggests investigating multi-output scheduling efficiency, not a causal
conclusion from one dual capture. Source inspection of
[lgpio v0.2.2](https://github.com/joan2937/lg/blob/v0.2.2/lgPthTx.c) confirms a
shared transmit worker with a PWM record list and absolute monotonic sleeps.
Its PWM path writes individual GPIOs; these measurements do not establish
batched PWM ioctls. A shared scheduler is a candidate non-PIO improvement, not
an implemented or validated replacement for the current thread-per-output engine.

The halfway-stop cases drove GPIO18 low and deinitialized it at approximately
10.000 seconds; its quiet tail exceeded 10.19 seconds. GPIO23 continued until
20 seconds, with a normal 0.19–0.21 second tail. This checks independent output
activity, not baseline lgpio line release at the halfway point, pin reuse, or
waveform quality around shutdown. Across all 30 captures every channel ended
low with at least 0.19 seconds of quiet tail. After the batch both pins were
unclaimed, no test/load processes remained, and fresh callers retained normal
policy, 50,000 ns timer slack, and 2,100,000 ns slices. Preliminary three-second
dual 500 Hz idle smoke captures also passed for lgpio and the enabled draft.

Raw captures and metadata are outside the package repository in
`work/pwm-measurements/pi5-single20-*` and `pi5-dual20-*`; the temporary isolated
environment is `/tmp/blinka-pwm-pi5-cooled.y4ysND`. The package remains experimental,
the short-slice option stays off by default, and Blinka is not switched.
NeoPixel/Piomatter coexistence has **not** been tested. Next work should evaluate
shared non-PIO scheduling, repeat dual-output measurements, and cover updates,
coexistence, and older boards/kernels before any migration decision.

## Experimental shared scheduler: first Pi 5 measurements

An original, non-PIO shared scheduler was added behind `BLINKA_PWM_SHARED=1`.
It remains **off by default**, as does the existing short-slice option. The
per-output engine is retained. One worker services outputs with the same
short-slice setting; GPIO requests and synchronous writes remain separate.
No Blinka selection, boot configuration, governor, affinity or priority was
changed. See [the design notes](design.md) for lifecycle and portability limits.

Before GPIO testing, local checks passed **73 tests with 23 Linux-only skips**;
the same source archive built and passed **96 tests on the Pi 5**. Tests cover
same-worker identity, independent shutdown, write-error isolation, new output
construction after fork, retained stopped handles, startup-low cleanup, timer
setup failures and safe short-slice fallback. A deterministic production-code
test checks boundary updates and missed-cycle skipping. A recording-only stress
test completed 400 concurrent attach/update/stop lifetimes. Separate macOS
AddressSanitizer/UndefinedBehaviorSanitizer lifecycle and stress runs and a
ThreadSanitizer stress run passed. None of those regression tests drove GPIOs.

The isolated Pi 5 environment was rebuilt from
`work/pwm-measurements/shared-scheduler-dist/adafruit_blinka_raspberry_pi_pwm-0.0.1.dev0.tar.gz`;
the build produced wheel SHA256
`8acb8e9f360fde29abfe28891d3b4226b89aaf273bdbb43d7a621d5f93f26626`.
Extracted test sources are in `/tmp/blinka-pwm-shared.GszqtJ`. The OS, gpiod,
baseline lgpio/unchanged Blinka wrapper, isolated environment, wiring, 10 MS/s
sampling, load and analysis definitions match the preceding Pi 5 batch.

A three-second idle dual-500 Hz shared/short-slice smoke capture measured
approximately 500.002 Hz on both GPIO18 and GPIO23, zero long gaps, highs of
996.1–1003.4 µs and 996.2–1003.4 µs, and 1.08% CPU of one core. It recorded
only the caller and one 100,000 ns worker. This is a smoke test, not acceptance.

The loaded batch contained **ten 20-second captures**: one per backend/profile
for three profiles, plus one independent-retirement capture. lgpio, the existing
per-output engine with short-slice on, and the shared engine with short-slice on
were compared. Backend order was reversed for the middle profile. This is
**one round per combination**, not repeated statistical evidence; shared mode
with short-slice off has not yet been measured physically.

All ten captures passed thermal checks: endpoint snapshots ranged from 48.500
to 63.350°C and all firmware readings were `throttled=0x0`. The table gives
**GPIO18 / GPIO23** values. CPU is combined PWM-process usage as a percentage of
one core, excluding the four independent load processes.

| Requested Hz, 18 / 23 | Backend | Mean Hz, 18 / 23 | Long gaps, 18 / 23 | Longest period, µs, 18 / 23 | PWM CPU, % |
| --- | --- | --- | --- | --- | --- |
| 5000 / 5000 | lgpio | 5000.012 / 5000.012 | 9 / 9 | 5355.5 / 5355.5 | 7.43 |
| 5000 / 5000 | Per-output, short-slice on | 4996.141 / 4996.493 | 16 / 15 | 3400.2 / 3401.4 | 11.54 |
| 5000 / 5000 | Shared, short-slice on | 4997.246 / 4997.246 | 24 / 24 | 3541.1 / 3541.1 | 8.12 |
| 500 / 500 | lgpio | 500.001 / 500.001 | 10 / 10 | 5954.7 / 5954.3 | 0.789 |
| 500 / 500 | Per-output, short-slice on | 499.951 / 499.951 | 1 / 1 | 4734.9 / 4737.2 | 1.188 |
| 500 / 500 | Shared, short-slice on | 500.001 / 500.001 | 0 / 0 | 2349.3 / 2080.8 | 1.566 |
| 50 / 500 | lgpio | 50.000 / 500.002 | 0 / 6 | 20049.0 / 5952.5 | 0.771 |
| 50 / 500 | Per-output, short-slice on | 50.000 / 499.951 | 0 / 1 | 20070.1 / 4909.1 | 0.849 |
| 50 / 500 | Shared, short-slice on | 50.000 / 499.900 | 0 / 2 | 20012.7 / 4988.3 | 0.857 |

**Shared scheduling is not a demonstrated timing fix.** Dual 5 kHz CPU was lower
than the per-output engine, but gap counts were higher and shared highs reached
3539.6/3539.7 µs against nominal 100 µs requests. At dual 500 Hz, shared mode
had no long gaps, but highs ranged from 650.9–1025.7 µs on GPIO18 and
919.8–1459.6 µs on GPIO23 against nominal 1000 µs. Its CPU cost was higher
than the per-output engine in that capture. A shared worker does not necessarily
coalesce independent outputs' wakeups; no phase synchronization is promised.

The mixed shared run's GPIO18 highs ranged from 1487.7–3001.2 µs against an
approximately 1500 µs target; GPIO23 highs ranged from 7.4–1058.7 µs against
1000 µs. The per-output run's corresponding ranges were 1432.0–1513.1 µs
and 16.0–2959.3 µs. lgpio's 50 Hz request remains integer-quantized to 7%
(1400 µs); its GPIO18 highs reached 4000.9 µs. Near-requested averages and
zero long-gap counts still do not establish pulse-width quality. No servo,
motor, NeoPixel or Piomatter device was attached during these measurements.

The shared retirement capture deinitialized GPIO18 at 10.000163 active seconds;
its low tail was 10.229139 seconds while GPIO23 continued until the endpoint,
with a 0.228238 second low tail. Functional independence passed, but timing
excursions remained: gap counts were 6/12, longest periods 4966.2/6947.4 µs,
and highs reached 4957.3/4947.2 µs. This does not prove clean timing around
deinitialization or reuse of a released pin.

All captured channels ended low, with at least 0.1979 seconds of quiet tail.
Postflight checks found GPIO18/23 unclaimed, firmware flags zero, and no test or
load processes remaining. Raw captures and metadata are outside the package
repository in `work/pwm-measurements/pi5-shared20-*` and `pi5-shared-smoke-500`.
The measurement harness records the shared opt-in and clears it for other modes.

Measurement work stopped after recording these results. Neither opt-in is
promoted and Blinka is unchanged. At the subsequent backup checkpoint, code,
tests and notes were committed together with a compressed measurement recovery
snapshot in `hardware-evaluation/2026-10-01/measurements.tar.gz`; see
`hardware-evaluation/README.md`. Resume with repeated waveform
comparisons and investigation of latency tails, not an assumption that sharing
workers solved them. Other-SBC adapters and non-PIO kernel PWM are candidate
future work; existing `sysfs_pwmout` boards are not newly supported by this draft.

## Pi 5 syscall/deadline diagnostics — October 6, 2026

A fresh-context review of `bd9712f..d5debaf` found no confirmed correctness
issues. Its GPIO-free macOS verification passed 73 tests with 23 Linux-only
skips. This was a code review, not a timing acceptance result. The review excluded
these result notes, the recovery artifacts, and the external measurement folder.

After reboot, `test-pi5` was reachable at 31.8°C with clear firmware limiting
flags. A new isolated environment at `/tmp/blinka-pwm-oct6.F3SDcm/venv` installed
gpiod 2.5.0 and the unchanged production package from `d5debaf`. All 96 existing
GPIO-free tests passed. Six additional lab-recorder tests passed; the complete
Linux suite subsequently passed **102 tests**. The macOS suite passed 73 tests
with 29 Linux-only skips. No GPIO is requested by these automated tests.

The Pi still runs kernel `6.12.75+rpt-rpi-2712`, CPython 3.13.5, normal
SCHED_OTHER/nice 0, all-four-CPU affinity, and the `ondemand` governor. Worker
slices read 100000 ns with the existing short-slice opt-in; the caller retained
2100000 ns. No priority, affinity, governor, kernel tracing, or system package
configuration was changed. The user reconfirmed cooling and the same wiring:
GPIO18/channel 0, GPIO23/channel 1, common ground, no competing devices.

`tools/native_trace.c` and `tools/build_trace.py` build a **lab-only** extension
from unchanged `module.c`, `pwm_engine.c`, and `pwm_shared.c`. Compile-time aliases
wrap their GPIO v2 SET_VALUES ioctls and timed waits. A preallocated recorder
stores monotonic begin/end/deadline, thread CPU elapsed, fd/level/result and tid,
then flushes only at process exit. A trace preflight precedes GPIO requests.
This build lives in a separate `/tmp` source copy; it does not replace the normal
installation or alter `setup.py`. It is deliberately not a performance benchmark:
clock reads and recording perturb timing, and unexpected process termination can
lose the trace. See `tools/README.md` for interpretation and safety constraints.

The same Saleae configuration (Logic 2 2.4.46, 10 MSa/s) recorded GPIO18 at 50 Hz,
duty 4915 (target approximately 1500 µs), and GPIO23 at 500 Hz, duty 32768
(approximately 1000 µs). After a three-second idle smoke capture, four loaded
captures each ran for 20 seconds with four bounded CPU burners. The loaded
instrumented shared mode ran twice, per-output once, and an uninstrumented
shared control once. All used the short-slice opt-in. Endpoint temperatures
were 45.75–57.30°C; firmware flags stayed `throttled=0x0`. These are endpoint
readings plus persistent limiting history, not continuous thermal monitoring.
All outputs finished low with at least 0.205 s quiet tail, and both pins were
unclaimed after cleanup.

| Loaded capture | GPIO18 high min–max, µs | GPIO23 high min–max, µs | Largest timeout lateness, µs | Largest traced ioctl, µs |
| --- | --- | --- | --- | --- |
| Instrumented shared, round 1 | 1503.7–1506.3 | 796.8–1037.2 | 209.647 | 12.722 |
| Instrumented per-output | 487.5–1532.5 | 324.9–2656.3 | 1661.993 | 90.868 |
| Uninstrumented shared control | 1493.3–1533.2 | 987.5–1084.7 | Not recorded | Not recorded |
| Instrumented shared, round 2 | 1504.3–1506.9 | 795.1–1086.6 | 211.008 | 98.661 |

Every trace had zero dropped, file-I/O or clock errors. Successful level-changing
ioctl counts matched the external digital transitions exactly on each channel;
correlation uses edge ordinal, not an assumed common clock origin. All
instrumented GPIO writes succeeded. Wait results are Linux errno values
(`ETIMEDOUT=110`), not the analyzer host's macOS values. Sampling quantization is
100 ns, and analyzer clock accuracy remains uncalibrated.

The per-output capture provides concrete localization of three long GPIO23
highs. At analyzer rise times 16.0295896, 16.5496051 and 17.1096217 s, highs
measured 2655.1, 2655.1 and 2656.3 µs. Associated timed waits returned
1661.899, 1661.993 and 1660.159 µs after their requested deadlines, while using
only 2.333, 2.297 and 6.222 µs of thread CPU across approximately 2652 µs wall
time. Falling GPIO ioctls took just 0.704, 0.722 and 2.056 µs. Thus those
stretched highs coincide with late wait returns, not slow falling writes.
The following highs shortened to 343.1, 342.9 and 344.3 µs as the fixed-deadline
schedule recovered. This does not establish a kernel cause: timed waits include
mutex reacquisition, and elapsed time alone cannot distinguish timer delivery,
run-queue delay, blocking, or preemption.

Not every distortion is inside a wait. GPIO18's shortest high, 487.5 µs, has a
preceding wait only 2.894 µs late, followed by **1017.507 µs between the recorded
wait end and rise-ioctl start**. Three approximately 40 ms GPIO18 periods similarly
have timely wait returns followed by approximately 2655 µs gaps to low writes,
with the expired rises suppressed. Those gaps are outside the measured wait
and ioctl intervals, but include recorder head/tail bookkeeping and native-loop
code; they are not measurements of pure application CPU time. The per-output
capture has eight GPIO18 and ten GPIO23 highs outside ±20% of target, so this
is still not a suitable acceptance result for loaded servo timing.

In shared round 1, the largest late wait occurs while GPIO23 is low: the delayed
rise stretches that low to 1209.2 µs and shortens the next high to 796.8 µs.
Analysis therefore records the wait before a rise separately from waits during
the high. An interval from the largest in-high wait to a fall can also contain
other normal waits; it is not necessarily computation overhead.

The earlier shared-mode approximately 3001 µs servo highs did **not** recur in
these two traced rounds or the one untraced control. That does not invalidate
the October 1 captures or prove the issue fixed. The new evidence establishes
that userspace service latency can appear both in timeout returns and between
recorded operations; it does not prove an improvement from instrumentation or
isolate the cause of the earlier shared outliers. PIO remains excluded, both
options remain default-off, and Blinka has not been switched over.

The new raw captures and reproducible scripts are preserved separately in
`hardware-evaluation/2026-10-06/diagnostics.tar.gz`; see its README. The next
useful investigation is kernel-level timer/scheduling attribution or a non-PIO
kernel/hardware PWM path, while retaining software fallback for other pins.
Further userspace parameter tuning alone is not justified by these traces.

### Private kernel trace follow-up

The user approved one additional 20-second per-output capture with four bounded
CPU burners. Existing `pi` passwordless sudo was used non-interactively; no
password was requested or sudo configuration changed. Only a newly created
tracefs instance was configured: `mono` clock, 8192 KiB per CPU, filtered
worker scheduling and timer lifecycle events. Expiry events selected
`hrtimer_wakeup` callbacks, including other sleepers; attribution matches only
the workers' own timer generations. No instance-wide PID filter was used because
expiry and wakeup can execute in another task's context. Global trace controls,
priorities, affinity, governor, PIO, and production source remained unchanged.

The private instance was stopped, exported and removed normally. Kernel buffers
reported zero overruns, commit overruns or dropped events on all four CPUs.
Native tracing recorded 44012 records with zero drops/errors. Begin/end markers
verified the kernel/native monotonic clock relationship. Kernel text timestamps
have **1 µs resolution**; the Saleae clock is correlated only by edge ordinal,
not aligned numerically to the kernel clock. Both channels' edge counts matched
successful level-changing writes exactly (GPIO18: 2002; GPIO23: 19998).

| Output | High min–max, µs | Longest period, µs | Estimated omitted cycles |
| --- | --- | --- | --- |
| GPIO18, 50 Hz | 1351.0–1525.5 | 20151.2 | 0 |
| GPIO23, 500 Hz | 814.9–1054.0 | 6004.4 | 2 |

Neither channel had a complete steady-state high outside ±20% of its target in
this run. GPIO23 nevertheless missed two cycles, so acceptable-looking high
widths alone do not establish correct PWM delivery.

The worst GPIO23 wait (native sequence 8150, worker TID 2805) returned
**3758.014 µs late**. Its matched monotonic timer had 1 ns permitted slack. The
printed callback timestamp is only 0.544 µs after the requested deadline, below
the trace's 1 µs precision. Wakeup was observed at 3879.292248 s; switch-in on
CPU2 did not occur until 3879.296003 s: **3755 µs runnable but off-CPU**. The
switch-out/in records name bounded burner PID 2802 as the neighboring task.
The native wait used only 4.167 µs thread CPU across 4746.909 µs wall time.
This localizes almost all of this particular timeout tail to delayed CPU service
after wakeup, rather than a millisecond-late timer callback or GPIO ioctl.
The filtered trace does not expose every unrelated task or the scheduler's
internal decision, so it does not prove why resumption was delayed.

The wait occurred while GPIO23 was low. Fixed-deadline recovery suppressed
expired rises rather than emitting a catch-up burst; ordinal-correlated Saleae
edges contain the 6004.4 µs period and approximately 5000.3 µs low interval.
This explains the missed cycles without implying a stretched high for this event.

GPIO18's worst wait (sequence 11922) was 153.909 µs late, including 146 µs from
wakeup to switch-in. Its subsequent high shortened to 1351.0 µs. Its largest
adjacent wait-to-write gap (sequences 31148/31151) was 30.538 µs, including three
runnable switch-out intervals totaling 17 µs around `kworker/u21:0`; the rest
is not established as pure application work. No non-runnable interval appears
inside that gap. The earlier millisecond-scale post-wait gaps did not recur.

Endpoint temperatures were 46.85–58.95°C with clear firmware history. Both
outputs ended low with at least 0.898 s quiet tail. Read-only postflight checks
found no trace instances, no recorded parent/worker/burner PIDs remaining,
GPIO18/23 unclaimed, unchanged global trace controls, and `throttled=0x0`.
The generated-capture/helper harnesses passed 19 GPIO-free tests (plus 12
subtests); kernel analyzer self-tests and lint passed.

This is one doubly instrumented diagnostic run, **not a production performance
comparison or acceptance result**. It supports scheduler service delay as an
observed contributor in this run, not attribution of the earlier shared-mode
outliers or proof that any tuning fixed them. The next design investigation is
a non-PIO kernel/hardware PWM path for suitable pins, while retaining compatible
software fallback. Neither opt-in is promoted and Blinka remains unchanged.
Raw evidence, clock/filter metadata, postflight checks, and exact diagnostic
scripts are preserved separately in
`hardware-evaluation/2026-10-06/kernel-diagnostics.tar.gz`.

### Non-PIO kernel PWM investigation — read-only checkpoint

The user connected Saleae channels 2/3 to `test2-pi4` GPIO18/23, leaving the
Pi 5 on channels 0/1. An initially reported `test1-pi4` hostname was corrected
by the user. Ground and fan signal-pin isolation must be confirmed before
driving the newly connected Pi 4; no new signals or overlays were enabled during
this read-only investigation.

The benches currently differ:

| Bench | Kernel | Header hardware PWM | Other live PWM |
| --- | --- | --- | --- |
| Pi 5 | `6.12.75+rpt-rpi-2712` | RP1 `pwm@98000` disabled; GPIO18 maps to channel 2 | RP1 `pwm@9c000`, channel 3 requested by `cooling_fan` |
| Pi 4 Rev 1.4 | `6.18.50+rpt-rpi-v8` | BCM `pwm@7e20c000` disabled; GPIO18 maps to channel 0 | No PWM chips instantiated; second BCM controller also disabled |

GPIO23 has no hardware PWM route on either board. Installed `pwm` and
`pwm-gpio` overlays and the `pwm-gpio` module are present on both. The old
Pi 4 temporary measurement environment is gone; its new kernel and Python
build mean the October 1 comparisons are not a matched current-system baseline.
Pi 4 non-interactive sudo currently requests a password; none was supplied.
The Pi 5 fan controller is separate from header PWM and must remain untouched.

Primary-source provenance matters. The official packaging changelogs identify
[Pi 5 kernel commit `89050b1`](https://github.com/RPi-Distro/linux-packaging/blob/8b252b157d0c946b50f1360980e7f079e545e07d/debian/changelog)
and [Pi 4 kernel commit `cff533a`](https://github.com/RPi-Distro/linux-packaging/blob/57beb6cc27d4a9e7997413e1213e6d7f4a346c03/debian/changelog).
The latter core serializes per-controller apply operations; the former does
not, despite newer generic documentation describing that guarantee. An eventual
adapter must account for the older controller-wide read/modify/write risk.
Both sysfs interfaces still apply period and duty through separate writes.

Two candidates warrant waveform evaluation:

- **Hardware PWM on GPIO18.** BCM and RP1 have independent per-channel period
  registers; a shared source clock does not require matching frequencies. Pins
  sharing the same hardware channel are aliases, not independent outputs.
  GPIO18 uses different channel numbers across the two families. The generic
  overlay's legacy function mapping is translated by the RP1 pinctrl driver.
  Discover by device-tree/controller identity and active routing, never by a
  hard-coded `pwmchipN`. See the exact [RP1 driver](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/pwm-rp1.c)
  and [Pi 4 BCM driver](https://github.com/raspberrypi/linux/blob/cff533aec2fa601846766b32ff57204e0a61bed7/drivers/pwm/pwm-bcm2835.c).
- **Kernel software PWM on GPIO23.** `pwm-gpio` runs its GPIO toggles from a
  monotonic hrtimer, without a userspace waveform thread or PIO. Both exact
  driver revisions use the same edge logic: pending updates at period end,
  static endpoints, and rejection of sleeping GPIO controllers. They advance
  from previous expiry rather than skipping expired phases. Delayed callbacks
  can therefore catch up with short pulses; IRQ latency and write cost remain
  measurement questions. This is not hardware PWM or a timing guarantee.
  See the [Pi 5 driver](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/pwm-gpio.c)
  and [Pi 4 driver](https://github.com/raspberrypi/linux/blob/cff533aec2fa601846766b32ff57204e0a61bed7/drivers/pwm/pwm-gpio.c).

Neither prospective header provider offers a suitable combined-state
character-device API: Pi 5 predates it, and the newer Pi 4 BCM/`pwm-gpio`
drivers lack waveform callbacks. Sysfs exports are global requests, not
process/FD leases, and another sysfs writer can alter them. Exported channels
survive process death; unexport alone does not universally stop output.
Disabled PWM output is unspecified by the generic API. Require explicit normal
polarity and endpoint verification, low-before-disable/release, ownership checks,
and error-reporting cleanup. A future frequency setter must rescale duty and
handle partially applied writes. See [Linux PWM semantics](https://www.kernel.org/doc/html/v6.12/driver-api/pwm.html).

A direct wrapper around Blinka's current `sysfs_pwmout` is not suitable: it
unexports a pre-existing channel before export and does not enforce the draft's
ownership/fork/lifecycle contract. Reusing the Linux interface is an opportunity,
not permission to take over existing channels or fall back onto their GPIOs.

The initial proposal was runtime Pi 5 `pwm`/`pwm-gpio` overlays, endpoint
checks, a 3-second idle capture and a 20-second four-burner capture, followed
by overlay removal. **That removal plan was withdrawn before any activation.**
Further exact-version source review identified two unsafe teardown paths:

- Pi 5's RP1 probe stores private data on the PWM-chip device but never sets
  platform driver data. Its remove callback retrieves the unset platform
  pointer and dereferences `pc->clk`. It also duplicates managed clock cleanup.
  This is a concrete source-derived defect, not a reproduced kernel crash.
  See [probe/remove](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/pwm-rp1.c#L125)
  and [allocation helper](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/core.c#L1011).
- Both exact `pwm-gpio` revisions call unmanaged `pwmchip_add()` but provide
  neither a remove callback nor managed PWM unregistration. Managed allocation
  only releases the chip reference; timer cancellation and GPIO release do not
  remove the PWM core's registry entry. Hot removal can therefore leave stale
  provider registration or a freed chip pointer. See [Pi 5 allocation/registration](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/core.c#L998)
  and [Pi 4 registration/unregistration](https://github.com/raspberrypi/linux/blob/cff533aec2fa601846766b32ff57204e0a61bed7/drivers/pwm/core.c#L2552).

Do not remove these runtime overlays, unbind their drivers or unload their
modules as experiment cleanup. No teardown was attempted and both boards are
unchanged. The revised proposal, requiring fresh user approval, is to run the
same Pi 5 checks but explicitly stop/release the outputs and leave the providers
configured until a controlled reboot. GPIO18/23 would remain assigned to kernel
PWM until then. No boot-file edits, PIO use, production backend changes or
fan-controller changes are proposed. Pi 4 additionally needs confirmed ground/
fan signal-pin isolation and user-run privileged setup or suitable sudo access.

### Pi 5 non-PIO kernel PWM — hardware checkpoint

The user approved use of the dedicated test Pis. On the Pi 5 only, runtime
overlays were enabled with `dtoverlay pwm pin=18 func=2` and
`dtoverlay pwm-gpio gpio=23`. No boot file was edited. Discovery verified the
header RP1 `pwm@98000`, channel 2, for GPIO18 and an RP1 GPIO23 `pwm-gpio`
provider, channel 0. The live header clock was 50 MHz. The separate
`pwm@9c000` fan controller and its `cooling_fan` consumer were not manipulated.
There was no PIO, scheduler-policy, affinity, governor or kernel change.

All runs used the exact helper SHA256
`ed8e60cd529a9cfdd231994627ef3c1fc1aefb7abf3673c66cd44e38745f119d`,
unprivileged as `pi`. It refused existing exports, tracked only successful fresh
exports, waited for udev permissions, serialized configuration writes, and
explicitly commanded low before disable/unexport. Signal handlers deferred
interruption during cleanup; a 30-second alarm bounded normal execution.
Loaded runs started four independent CPU burners with 25-second self-expiry.
This is a lab helper, not a production ownership or crash-recovery solution.

#### Static endpoints: RP1 hardware full duty is not constant high

Seven 0.2-second holds requested the GPIO18/GPIO23 sequence
`00,10,00,01,00,11,00`, with normal polarity and enabled outputs. Both captures
began and ended low. GPIO23 showed the expected four transitions and no detected
short interior dips. GPIO18 failed the strict four-transition check:

| Capture | Nominal sample interval | GPIO18 transitions | Interior low dips |
| --- | --- | --- | --- |
| `oct6-pi5-kernel-endpoints`, 10 MSa/s | 100 ns | 10 | 3, each digitized as one sample |
| `oct6-pi5-kernel-endpoints-100msps`, 100 MSa/s | 10 ns | 40 | 18, each digitized as 10–20 ns |

At the higher rate, every interior cycle in both full-duty holds has a detected
notch. These are digital threshold-crossing measurements, not analog pulse-width
proof. The analyzer timebase was not calibrated. The initial higher-rate capture
process still had the old 10-MS-only analyzer imported; replay with the updated
offline analyzer rejected the actual extra edges. Raw files and explicit
`endpoint-rejection.json` reports preserve both failures; no filter was used to
reclassify them as passing endpoints.

The exact [RP1 driver](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/pwm-rp1.c#L89)
programs equal DUTY and RANGE at full duty and has no full-duty special case.
The [RP1 datasheet, section 3.4.4.1](https://datasheets.raspberrypi.com/rp1/rp1-peripherals.pdf#page=37)
describes an inclusive RANGE count and output high only when COUNT is below
DUTY. Together these predict a nominal one-20-ns-clock low notch at 50 MHz,
consistent with the higher-rate waveform. This is a strong source-and-waveform
explanation, not a direct register read or a tested driver correction. Sysfs
readback reported the requested full duty but does not prove constant physical
high. A driver correction or separately tested static-endpoint strategy is
needed before this hardware path can preserve CircuitPython's full-duty behavior.

#### Ordinary duties: promising hardware and kernel-software timing

After identifying the endpoint failure, interior duties were measured separately:
GPIO18 at 50 Hz/duty 4915 (approximately 1500 µs high), GPIO23 at
500 Hz/duty 32768 (approximately 1000 µs high), Saleae channels 0/1 at
10 MSa/s. A 3-second idle run and two 20-second four-burner runs were recorded.
The summary trims 0.05 seconds from each end of the active edge train.

| Capture | GPIO18 period range (µs) | GPIO18 high range (µs) | GPIO23 period range (µs) | GPIO23 high range (µs) |
| --- | --- | --- | --- | --- |
| `oct6-pi5-kernel-idle` | 20000.8–20000.9 | 1500.0–1500.1 | 1998.5–2001.4 | 998.5–1001.8 |
| `oct6-pi5-kernel-loaded` | 20000.8–20000.9 | 1500.0–1500.1 | 1999.0–2000.9 | 999.0–1001.6 |
| `oct6-pi5-kernel-loaded-r2` | 20000.8–20000.9 | 1500.0–1500.1 | 1998.7–2001.3 | 998.7–1001.8 |

Trimmed complete-cycle counts were GPIO18 143/993/993 and GPIO23
1449/9950/9950. No analyzed period exceeded 150% of target; no high was outside
20% of target. No draft-scheduler omitted-cycle estimate is applied to these
kernel providers. The small hardware frequency offset cannot be assigned solely
to the RP1 clock from an uncalibrated analyzer. Remote monotonic phase timestamps
are not aligned to Saleae time.

The narrow GPIO23 deviations in that table describe **steady state only**.
Including startup/shutdown, complete raw GPIO23 high widths were
993.1–1017.3 µs and 982.3–1016.8 µs for the two loaded runs; raw periods were
1991.1–2017.0 µs and 1981.5–2027.7 µs. No raw complete period exceeded
150% of target either. Endpoint transition timing needs separate acceptance;
the trimmed figures are not bounds for the entire output lifecycle.
These loaded-run extrema occur in the first two cycles; deviations beyond the
narrow steady-state ranges were confined to the first approximately 20.01 ms
of the physical train. No corresponding shutdown outlier was found. This
localization does not identify the startup cause.

The loaded GPIO23 results are much more stable than the earlier userspace worker
captures, consistent with avoiding runnable-but-unscheduled waveform threads.
They are not a matched implementation benchmark or evidence for all frequencies,
boards and workload types. Kernel hrtimer interrupt latency, expired-phase
catch-up, variable frequency/duty updates, independent shutdown, endpoint
transitions, errors/fork/crash behavior and ownership still need acceptance work.
The good interior-duty measurements do not cancel the RP1 endpoint failure.

#### Cleanup and recovery

All five helpers reported successful low/disable/unexport with no cleanup
errors. External low tails were at least 0.47 seconds. Temperatures before/after
were 46.85/46.85°C and 46.85/47.40°C for endpoints, 47.95/46.85°C idle,
48.50/58.95°C loaded, and 46.85/57.85°C for the loaded repeat; all firmware
limiting flags remained zero. Postflight found both pins physically read low,
no userspace PWM exports and no recorded burner PIDs remaining. Fan ownership
remained `cooling_fan`; its normal thermal-control duty changed during the runs.
The boot configuration SHA256 before and after remained
`b7c4bef8c3e955d6e9b93b0f209ce4b4301549796978b845fbb4ff8ba48f7776`.

The two runtime overlays remain loaded until reboot: GPIO18 is still muxed to
header PWM and GPIO23 remains reserved by its kernel PWM provider. This is
intentional, not complete restoration of GPIO ownership. Do not hot-remove,
unbind or unload these providers. Pi 4 is unchanged and its password-requiring
sudo still prevents unattended privileged setup.

The GPIO-free helper/orchestration/waveform/rejection tests passed 95 cases;
lint passed. Production source and Blinka integration remain unchanged from
`d5debaf0e5caafa1fdf5a7619e1ae2e8cd41f1f4`. The next useful steps are a safe
full-duty strategy and matched Pi 4 kernel-PWM evaluation, not replacing the
existing backend yet.

Raw captures, both rejected-endpoint reports, original source snapshots and
final GPIO-free tools/tests are preserved in
`hardware-evaluation/2026-10-06/kernel-pwm-evaluation.tar.gz`; see its README
for hashes, source-version differences and verified recovery instructions.

### Pi 4 non-PIO kernel PWM — hardware checkpoint

The user ran the privileged runtime setup on `test2-pi4` and explicitly
confirmed channel 2 → GPIO18, channel 3 → GPIO23, common ground, and neither
GPIO used by the fan. All captures then ran unprivileged as `pi`, without
changing sudo policy. The board is Pi 4 Model B Rev 1.4, kernel
`6.18.50+rpt-rpi-v8`. Strict live discovery selected BCM `pwm@7e20c000`,
channel 0, for GPIO18 and the BCM2711 GPIO23 `pwm-gpio` provider, channel 0.
The separate audio controller was not selected; its configuration was not
changed. Clock metadata reported 50,000,001 Hz for the header PWM clock.

The Pi 4-specific discovery wrapper reused the ownership, signals, thermal
gates, bounded CPU load and low/disable/unexport logic from the Pi 5 lab helper.
Core helper SHA256:
`7cb4ea051e346b38b3276b92e5e0edcd9f24f4ed36f7d4f4eeffa4800f8e2111`.
Pi 4 wrapper SHA256:
`ce9765a79d3e20b63a612248a2566e26ea8b2ddd45c71bbb7a3173e8885dc421`.
The core differs from the Pi 5's exact measured helper only by formatting,
import sorting and comments. All existing Pi 5 snapshots remain unchanged.

#### Endpoints pass at matched digital resolution

Both `oct6-pi4-kernel-endpoints` (10 MSa/s) and
`oct6-pi4-kernel-endpoints-100msps` (100 MSa/s) passed the strict physical
`00,10,00,01,00,11,00` pattern: exactly four transitions per channel, normal
polarity, low initial/final states, independent static highs and the expected
both-high overlap. No extra transitions were detected in the full-duty holds,
including at the 10-ns nominal sample interval used for the Pi 5 notch test.
This is finite digital threshold-crossing evidence, not proof of absence of
all analog transients. Neither the analyzer clock nor analog pulse widths were
calibrated. Glitch filtering was disabled in every recorded capture.

GPIO18's high holds were approximately 200/200 ms in the first capture and
200/220 ms in the higher-rate capture; GPIO23's were approximately 203/203 ms
and 201/201 ms. Holds include configuration/readback overhead; one captured
hardware hold differs from the request by approximately one PWM period. The
measurements do not separate syscall/readback time from hardware effects.
They establish static levels
and independence, not immediate setter response or shared phase alignment.
The full-duty problem observed on RP1 therefore was not reproduced with the
Pi 4 BCM provider on this bench.

#### Interior-duty timing

The same GPIO18 50 Hz/duty 4915 and GPIO23 500 Hz/duty 32768 profiles were
recorded at 10 MSa/s for 3 seconds idle and twice for 20 seconds with four
bounded CPU burners. These are matched profiles, not a matched kernel-version
benchmark: the Pi 4 and Pi 5 have different CPUs, GPIO controllers and kernels.

| Capture | GPIO18 period range (µs) | GPIO18 high range (µs) | GPIO23 period range (µs) | GPIO23 high range (µs) |
| --- | --- | --- | --- | --- |
| `oct6-pi4-kernel-idle` | 19999.6–19999.7 | 1499.9–1500.0 | 1998.8–2001.2 | 998.9–1000.1 |
| `oct6-pi4-kernel-loaded` | 19999.6–19999.7 | 1499.9–1500.0 | 1999.4–2000.7 | 999.4–1000.2 |
| `oct6-pi4-kernel-loaded-r2` | 19999.6–19999.7 | 1499.9–1500.0 | 1993.1–2007.0 | 994.8–1002.3 |

These figures trim 0.05 seconds at each end of the physical edge train.
Complete trimmed-cycle counts were GPIO18 143/994/994 and GPIO23
1450/9951/9951. The repeated loaded GPIO23 capture has a 7.0-µs maximum
absolute period error and about 5.22-µs maximum absolute high-width error;
the first run's sub-microsecond results are not a reproducible universal bound.
No trimmed period exceeded 150% of target and no trimmed high differed by
20% from target. Omitted-cycle estimates specific to the draft userspace
scheduler are intentionally not applied. The hardware frequency offset cannot
be separated from analyzer clock accuracy here. Pi monotonic timestamps are
not aligned to Saleae timestamps.

Untrimmed GPIO23 loaded periods were 1985.3–2014.2 µs and
1986.5–2014.5 µs for the repeat; complete high widths were 990.5–1022.8 µs
and 988.5–1013.8 µs. The full-train extrema occur early, within approximately
38 ms, so the trimmed table must not be treated as a whole-lifecycle bound.
Last complete highs were 1002.2 and 1002.7 µs. The hardware ranges remain
unchanged when including the full train. Full-train reports preserve extrema
with their Saleae times and offsets from the first physical rising edge;
neither those times nor the phase logs identify the cause of the deviations.

#### Cleanup and limits

All five helpers reported successful fresh-export release with no cleanup
errors. Low tails were at least 0.58 seconds. Before/after temperatures were
34.076/32.615°C for endpoints, 34.563/33.589°C idle, 33.102/46.738°C loaded,
36.024/48.686°C for the loaded repeat, and 36.024/35.537°C for the higher-rate
endpoints; all firmware limiting flags remained zero. Postflight showed both
pin levels low, no userspace PWM exports and no recorded burner PIDs remaining.
The boot configuration SHA256 stayed
`90a446821551a9df109ec1a77a79f6518fe974517d982d371c5e9efd6bbc98c3`.

The user-enabled `pwm` and `pwm-gpio` runtime overlays remain loaded until
reboot. GPIO18 is still muxed to hardware PWM and GPIO23 is still reserved
by its kernel provider. Do not hot-remove/unbind/unload `pwm-gpio`; stopping
the exported waveform is not removal of the provider. The Pi 5 was not driven
or reconfigured during this evaluation. No PIO, boot-file, kernel, scheduler
policy, affinity, governor or production backend change was made.

Kernel software PWM is promising on both benches for the measured profile,
without the PIO-sharing concern. Broader frequencies/duties, IRQ/I/O workloads,
frequency changes, independent shutdown, ownership/fork/crash/error behavior,
older board/kernel coverage and a Pi 5 constant-high strategy remain necessary
before adopting a new backend. These results do not establish drop-in readiness.

All 282 combined GPIO-free helper, orchestration, waveform, rejection and
full-train tests passed. Lab lint passed with the cosmetic RUF007
consecutive-pair `zip` suggestion explicitly excluded for the offline utility.
Raw evidence, exact helper/source snapshots and final tools/tests are preserved
in `hardware-evaluation/2026-10-06/kernel-pwm-pi4-evaluation.tar.gz`.

### Pi 5 constant-high workaround — focused hardware checkpoint

On the same confirmed Pi 5 GPIO18/channel 0 bench, two short captures tested
**enabled inverse polarity with zero duty** as a replacement representation for
constant high. No PIO, direct register access, kernel patch, package install or
production backend change was made. Only a fresh header RP1 `pwm@98000`
channel 2 export was used; GPIO23 and the separate fan controller were untouched.
The kernel remained `6.12.75+rpt-rpi-2712`.

The [exact kernel's sysfs polarity handler](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/core.c#L656)
accepts `normal` and `inversed`, including changes while enabled.
The [RP1 driver implements inversion](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/pwm-rp1.c#L75)
without a special-case full-duty representation. Inverse-zero avoids the
normal-full comparator boundary identified in the earlier rejected captures.
This is a tested userspace representation, not a correction to the driver.
A future wrapper could preserve the caller's `duty_cycle=65535` while using
inverse-zero internally, and restore normal polarity for interior duties.
That mapping is not implemented in the production `PWMOut` API here.

#### Captured endpoints and ordinary-duty recovery

`oct6-pi5-inverse-endpoints` and `oct6-pi5-inverse-endpoints-r2` both use
100 MSa/s, channel 0 only, physical Logic 8, with glitch filtering disabled
as verified from each saved `.sal` file. Each helper requests this nine-phase
sequence: normal low 0.2 s, ordinary PWM 0.4 s, low 0.2 s, inverse-zero
high 0.3 s, low 0.2 s, inverse-zero high 0.3 s, low 0.2 s, ordinary PWM
0.4 s, final low 0.2 s. Ordinary PWM is 50 Hz/duty 4915. Polarity changes
are conservatively performed while disabled; normal low/interior duty writes
do not toggle enable. The total requested phase holds are 2.4 seconds.

| Capture | First continuous high (ms) | Second continuous high (ms) | Extra captured dips |
| --- | --- | --- | --- |
| `oct6-pi5-inverse-endpoints` | 300.60109 | 300.57365 | 0 |
| `oct6-pi5-inverse-endpoints-r2` | 300.57336 | 300.60780 | 0 |

Both strict analyses pass. Each waveform has exactly 84 transitions: twenty
complete ordinary pulses before the holds, two continuous high holds, and
twenty complete recovery pulses. No extra transition was filtered or merged.
All four ordinary pulse trains have periods 20000.88–20000.89 µs and high
widths 1500.02–1500.03 µs, including their first/last complete pulses.
The recovery timing therefore matches the controls at this digital resolution.
These captures do not repeat the original normal-full baseline; that earlier
100-MS capture and its explicit failure remain unchanged.

The high holds include switching/readback overhead and exceed the requested
300 ms slightly. Low gaps are approximately 200–220 ms. A low separator
precedes recovery, so **direct constant-high → interior PWM was not tested**.
Pi monotonic phase clocks are not aligned to Saleae time; these observations
do not establish immediate setter response or transition latency. The nominal
sample interval is 10 ns, with no calibrated analyzer timebase or analog scope
measurement. No captured dips is finite threshold-crossing evidence, not proof
that all shorter or non-threshold-crossing transients are absent.

#### Cleanup, verification and next step

Inverse-zero makes a normal duty-zero cleanup unsafe. The separate diagnostic
owner restores normal polarity and zero duty while disabled, verifies that
requested state, enables and verifies low, settles for 0.1 s, then disables
and unexports. Cleanup retains the owned export if safe recovery or final
disable cannot be confirmed, and reports failure instead of success JSON.
[Disabled PWM has no guaranteed electrical level](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/Documentation/driver-api/pwm.rst#L58);
[RP1 release is not an emergency-low command](https://github.com/raspberrypi/linux/blob/89050b1059997d38d55462b323b099a6436dc10d/drivers/pwm/pwm-rp1.c#L64).
Readbacks and `low_confirmed` describe cached requested-state checks, not
physical measurements; the independent waveform supplies final-low evidence.

Both helpers finished without cleanup errors, in 2.664/2.772 seconds including
setup and cleanup. Final-low tails were 0.579/0.527 s. Before/after temperatures
were 49.05/48.50°C and 47.95/49.60°C; firmware limiting flags stayed zero.
Postflight found GPIO18/23 low, no test exports or helper PIDs, unchanged fan
provider/consumer/state and the same boot configuration hash. The runtime
overlays remain loaded: GPIO18 stays PWM-muxed and GPIO23 kernel-reserved.
Do not hot-remove/unbind/unload either provider on this tested kernel.

The independent source/safety review found no remaining diagnostic blockers;
the hardware evidence was also independently audited. All 384 combined
GPIO-free lab tests passed, including 38 new helper, 13 orchestration and 51
waveform cases. New-tool lint passed. Both saved analyses reproduce exactly
with the frozen offline analyzer, which rejects injected 10/20-ns dips.
The executed helper SHA256 is
`545b0fd16aaee668040f757be0e49e6021492ff5d64e13a94d8166983164fdbf`;
the common helper SHA256 remains
`7cb4ea051e346b38b3276b92e5e0edcd9f24f4ed36f7d4f4eeffa4800f8e2111`.

The focused experiment supports inverse-zero as a Pi 5 constant-high strategy.
Next is an isolated wrapper with direct high/interior transitions, frequency
changes, lifecycle/error behavior and broader workload/board coverage before
considering adoption. The production backend and Blinka integration are
unchanged. Both captures, exact sources/tests and pre/postflight evidence are
preserved in
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-inverse-evaluation.tar.gz`.

### Pi 5 direct/frequency/lifecycle transitions — strict rejections

Three further GPIO18/channel 0 captures exercised direct constant-high/interior
transitions, normal and high-state 50↔500 Hz changes, and closing from high then
reopening the same channel. All ran at 100 MSa/s, unfiltered, on the same Pi 5
kernel/bench. Logical duty 65535 used inversed-zero. Polarity/frequency changes
first disabled PWM; frequency changes zeroed duty before changing period.
The new diagnostic helper SHA256 is
`9ba7b5ad0893fbc71d508e2f16a91e7f8b5808bc5d749c7c54210ed50186f7f4`.
Its safe cleanup restores the known 20-ms period before inherited normal-low
verification/release. Source review caught and fixed a signal-during-first-close
path that could otherwise reopen generation 2; this was fixed and fake-tested
before any capture. No production code was changed.

All three traces remain **strictly rejected**, with `accepted=false` and every
physical transition retained. They contain shortened outgoing ordinary pulses
at update boundaries, not dips inside steady high holds. No trimming or predicate
relaxation turns these results into passes.

| Capture | Edges | Partial outgoing highs (µs) | Continuous high holds (ms) |
| --- | --- | --- | --- |
| `oct6-pi5-state-direct` | 532 | 1169.21, 429.62, 378.78 | 300.61866, 301.04738, 601.31797 |
| `oct6-pi5-state-frequency` | 486 | 1125.23, 356.42 | 902.40499 |
| `oct6-pi5-state-lifecycle` | 446 | 1213.00, 383.28 | 300.76394, 300.79547 |

In direct/lifecycle captures, the partials immediately precede entry to high.
The frequency capture's partials precede ordinary-frequency changes. Source
ordering makes the enable-bit clear a plausible explanation for truncation;
unaligned Pi/Saleae clocks do not establish syscall-correlated causation or
latency. High→interior recovery produced full ordinary pulses. Complete 50-Hz
groups have highs 1500.02–1500.03 µs and periods 20000.88–20000.89 µs;
500-Hz groups have highs 1000.06–1000.07 µs and periods 2000.10–2000.11 µs.
Retuning while high introduces no captured edge: the direct ~0.6-second and
frequency ~0.9-second holds each stay continuous. No sub-microsecond low run
was detected anywhere in these captures. These sub-findings do not override
the whole-trace rejection.

Lifecycle metadata records two distinct fresh export/unexport generations;
the physical low interval between them is 613.04989 ms. Both generations closed
from high and reported successful normal-low release. All helpers finished with
no cleanup errors, firmware flags zero, and temperatures below 48°C. Recorded
before/after temperatures are 47.40/47.95°C direct, 47.40/47.95°C frequency,
and 46.85/47.40°C lifecycle. Postflight confirms both test pins low, no exports
or recorded helper PIDs, and unchanged fan owner/state and boot configuration.
The providers stay bound until reboot; GPIO18 remains PWM-muxed and GPIO23
reserved. No PIO, kernel/boot/policy or production-backend changes occurred.

The [CircuitPython frequency setter documentation](https://docs.circuitpython.org/en/latest/shared-bindings/pwmio/#pwmio.PWMOut.frequency)
explicitly permits glitches during frequency adjustment. It does not explicitly
promise a complete outgoing pulse for a duty update. The stricter experimental
criterion is useful for characterizing quality, but these partials alone are
**not an established CircuitPython API violation**.

The exact kernel has no atomic userspace PWM state interface: it exposes scalar
sysfs attributes, not PWM cdev/ioctl operations. Per the
[RP1 datasheet, pages 36 and 39](https://datasheets.raspberrypi.com/rp1/rp1-peripherals.pdf),
control/inversion/enable apply at a PWM-clock update, whereas duty/range latch
at counter overflow. A single driver apply therefore does not inherently couple
all those changes at a cycle boundary. A source-supported follow-up keeps PWM
enabled, commands normal-zero, waits two periods for it to latch, and then
inverts; period changes similarly occur at zero with explicit settling.
That strategy intentionally adds delay and is not yet a production solution.

All 481 combined GPIO-free cases passed (38 new state-helper, 28 capture and
31 waveform cases), and new-tool lint passed. An independent raw/SAL/metadata
audit confirmed the rejected analyses and measured sub-findings. Raw captures,
exact sources/tests and pre/postflight are preserved separately in
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-state-evaluation.tar.gz`.

### Pi 5 enabled, period-settled transitions — characterization

The next three short GPIO18/channel 0 captures use the separate
`enabled-period-settled-v1` laboratory wrapper, not a production change.
Ordinary updates stay enabled: before entering inverse-zero high or changing
a normal period, the wrapper commands raw zero and waits two current periods.
Changed periods then settle for two maximum old/new periods before active duty
or inversion. Returning from high first restores normal polarity at raw zero;
high-state frequency changes retain inversed-zero throughout. The deliberate
waits are 40 ms at 50 Hz and 4 ms at 500 Hz; they trade update responsiveness
for finishing outgoing pulses. Cleanup still uses conservative disabled recovery.

| Capture | Edges | Strict `accepted` | Continuous high holds (ms) | Final-low tail (s) |
| --- | --- | --- | --- | --- |
| `oct6-pi5-settled-direct` | 526 | `true` | 300.52804, 300.52867, 641.41899 | 0.749 |
| `oct6-pi5-settled-frequency` | 484 | `false` | 982.23943 | 1.402 |
| `oct6-pi5-settled-lifecycle` | 444 | `true` | 300.90001, 300.88680 | 0.661 |

All captured ordinary highs, including outgoing and recovery pulses, remain
complete: 50-Hz highs are 1500.02–1500.03 µs with within-group periods
20000.88–20000.89 µs; 500-Hz highs are 1000.06–1000.07 µs with periods
2000.10–2000.11 µs. None of these traces has an unexpected high-width run,
a captured dip within a continuous high hold, or a sub-microsecond low run.
The direct capture's adjacent high-frequency phases remain one continuous
641.419-ms hold. Lifecycle closes both fresh generations from high, with a
696.827-ms physical low separator before the second generation's ordinary PWM.

**The frequency capture remains strictly rejected.** Its 982.239-ms continuous
high exceeds the nominal three 300-ms holds, and its ordinary frequency-change
rising-edge gaps are 84.00395 and 46.00209 ms, matching neither the configured
20-ms nor 2-ms period. The explicit zero/period settling inserts quiet gaps and
extends the high hold while retuning; it does not provide uninterrupted ordinary
PWM across frequency changes. No boundary trimming, edge merging, predicate
relaxation or reclassification converts this result into a pass. For example,
the direct waveform has 40.335/42.197-ms low gaps before its two 50-Hz high
holds and an 81.794-ms low gap during high-to-500-Hz recovery. Those are
waveform separators, not aligned measurements of command-to-edge latency.
Pi monotonic clocks remain unaligned with Saleae time, and the logged waits
and cached sysfs readbacks do not independently prove physical settling.

These are single captures with no deliberate CPU load on Pi 5 Model B Rev 1.0, kernel
`6.12.75+rpt-rpi-2712`, using physical Logic 8/Logic 2.4.46 at 100 MSa/s.
The saved `.sal` settings confirm channel 0 only and no glitch filter; every
captured transition is retained. The nominal sample interval is 10 ns, the
analyzer timebase is not independently calibrated, and this finite digital
threshold evidence neither measures analog transients nor excludes shorter
or non-threshold-crossing glitches. The scalar sysfs strategy is not an atomic
PWM-state API, a latency guarantee, or a general backend-readiness result.

All helpers reported cached normal-zero/20-ms final state, final disable and
fresh-export release with no cleanup errors. Direct/frequency/lifecycle helper
elapsed times were 3.676/3.219/2.610 s. Before/after temperatures were
46.85/47.40°C, 47.40/47.95°C and 46.85/47.95°C; firmware limiting flags stayed
zero. `low_confirmed` describes requested-state/readback checks and settling,
while the independent captures supply the final-low observations above.
Only header RP1 channel 2 was exported; GPIO23 and the fan were not driven by
these helpers. The production backend, Blinka integration and frozen earlier
diagnostic sources remain unchanged. Broader repeated/load/frequency coverage
and a suitable update-latency contract remain necessary before adoption.

One unchanged repeat of each sequence agreed with the first run. Direct-r2
passed with 526 edges and continuous highs 300.53676, 300.55442 and
641.35299 ms; frequency-r2 retained the same three strict timing rejections
with 484 edges and one 982.212-ms high. Its boundary low gaps were
82.50391/45.00202 ms. Lifecycle-r2 passed with 446 edges and highs
300.58050/300.62418 ms; its second train contained 201 complete 500-Hz
pulses rather than 200, within the frozen one-cycle allowance. No repeat had
a partial high, captured high-hold dip or sub-microsecond low run. Temperatures
across the repeats were 45.20–47.95°C with flags clear; all exports released.
Pi-clock transition durations in the first set were approximately 40.6 ms
for 50-Hz normal-to-high, 4.5–4.8 ms at 500 Hz, and 81.0–81.4 ms for a
50-to-500-Hz active transition. These include userspace/sysfs work and
deliberate waits, not synchronized electrical latency measurements.

All six original traces and accepted/rejected analyses, exact diagnostic
sources/tests, and pre/postflight records are preserved separately in
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-settled-evaluation.tar.gz`.
The 253,487-byte archive has SHA256
`cfb6c906f4e9672ab44e317867ba76f7776a2f0ecec6509fdcb090b4589414a9`;
all 26 top-level targets were byte-compared after fresh extraction.

### Pi 5 50-Hz half-duty transition follow-up

Two separate `half50-direct-v1` captures add the wider outgoing-pulse case:
low → 50 Hz/duty32768 for 0.4 s → inverse-zero high for 0.3 s →
50 Hz/duty32768 for 0.4 s → low. They reuse the frozen enabled-settled
transition and conservative cleanup; all periods remain 20 ms. The new
analyzer adds only this distinct sequence and its approximately 10-ms pulse
category. It retains every edge, the same ±2% complete-width/period checks,
one-cycle pulse-count allowance, and high-dip/partial-pulse rejection rules.
The earlier captures and their predicates are unchanged.

`oct6-pi5-half50-direct` and `-r2` both passed with 82 edges: 20 complete
outgoing pulses, one continuous high, and 20 complete recovery pulses.
All 40 ordinary highs in each were 10000.59–10000.60 µs, with periods
20000.88–20000.89 µs. High holds were 300.50486/300.52405 ms, with no
captured dips or partial outgoing/recovery pulses. Physical outgoing-to-high
low gaps were 31.83075/31.81675 ms; high-to-recovery gaps were
17.67976/17.67458 ms. These are waveform intervals, not synchronized
command-to-edge latency measurements. The single deliberate zero-settle
wait was 40 ms in both, as independently verified from the audit.

Both saved acquisitions used physical Logic8/channel0, 100 MSa/s, no glitch
filter and no trimming, with a 0.5-s non-GPIO pre-helper observation lead
and 0.2-s post-helper tail. All five exact source hashes matched. Final-low
tails were 0.624/0.847 s. Helpers 4017/4065 reported final normal-zero/20-ms
disable and fresh-export release with no errors; temperatures were
47.40→48.50°C and 46.85→49.05°C, flags clear. The 34 new GPIO-free
helper/capture/waveform tests and selected lint passed. This remains finite,
uncalibrated digital characterization, not analog or backend-readiness proof.

An initial externally launched CPU-only load attempt expired before the capture
handoff; no PWM capture was started. Its successful load receipts are retained
explicitly as setup/coordination evidence, not counted as loaded waveform data.

The two unloaded half50 captures, all exact diagnostic dependencies/tests and
pre/postflight records are preserved separately in
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-half50-evaluation.tar.gz`.
The 102,901-byte archive has SHA256
`e2033169ae3ae3d4187739de39cbd71ef8d686123afce69060a0314c56802425`;
all 28 top-level targets were byte-compared after fresh extraction.

### Pi 5 coordinated two-worker CPU-load follow-up

Two short, separate `-loaded-r2` acquisitions exercise the unchanged settled
direct and half50 sequences while two external CPU-only workers run for ten
seconds. A local coordinator persists and validates the launch receipt before
starting the existing capture helper; it then drains the load completion even
if capture fails. Both actual acquisitions recorded load-helper, recorder and
capture return codes of integer zero. Independent receipt audits confirm that
both actual worker intervals bracket every phase and the entire GPIO helper,
not merely that workers were launched. The initial standalone load attempt
completed before capture started and remains **CPU-only failed-coordination
evidence, not loaded PWM waveform data**.

| Capture | Edges | Strict `accepted` | Continuous high holds (ms) | Final-low tail (s) |
| --- | --- | --- | --- | --- |
| `oct6-pi5-settled-direct-loaded-r2` | 526 | `true` | 300.54664, 300.55339, 641.35334 | 0.86774790 |
| `oct6-pi5-half50-loaded-r2` | 82 | `true` | 300.58296 | 0.67626404 |

Direct retains 20/20/200/20 complete ordinary pulse groups; half50 retains
20 complete outgoing and 20 recovery pulses. Their measured ranges match the
idle captures at the saved 10-ns resolution: servo50 highs 1500.02–1500.03 µs
and periods 20000.88–20000.89 µs; half500 highs 1000.06–1000.07 µs and
periods 2000.10–2000.11 µs; half50 highs 10000.59–10000.60 µs and periods
20000.88–20000.89 µs. No partial ordinary pulse, unexpected high run,
captured high-hold dip or sub-microsecond low run was found. The direct loaded
holds compare with idle 300.52804/300.52867/641.41899 ms; half50 compares
with idle 300.50486/300.52405 ms. These are two diagnostic load captures,
not a statistical bound or proof of workload-independent timing.

Deliberate settling gaps remain. The loaded direct boundary low intervals are
40.31480/17.65448/42.10802/81.85767/4.58559/1.09248 ms, versus first idle
40.33467/17.65325/42.19661/81.79384/4.65803/0.95445 ms. Loaded half50
outgoing-to-high/high-to-recovery gaps are 31.80301/17.62940 ms, versus
31.83075/17.67976 ms idle and 31.81675/17.67458 ms in its idle repeat.
These waveform intervals are not synchronized command-to-edge latency.

Actual direct workers 4144/4145 completed 41054/41064 iterations; half50
workers 4182/4183 completed 42050/41034. Each ran approximately ten seconds
and was reaped with return code zero. The direct helper was bracketed by
approximately 1.016 s before and 5.311 s after; half50 by 1.441 s before and
6.753 s after, for each worker. Receipt timing assumes the same Pi/boot
monotonic clock and does not align that clock with Saleae. Two recorded CPU
workers establish concurrent CPU work, not full four-core saturation or
continuous execution of either worker.

Both original strict analyses and overlap reports reproduce independently;
raw binary/SAL checks confirm physical Logic8/channel0, 100 MSa/s and no
glitch filter. Exact helper source hashes, coordinator
`479eade31269ee00535112eb99fedf92bb47dc0cb1d57c40534de829410eed4b`
and recorder
`6f755cdb1d2a8dc4a2af72248ddda88740ab2a3ab123ac5a1afe82e52d06974d`
match the retained sidecars and frozen sources. The CPU-only helper hash is
`0644d9b0e0228bca813e7b3cbb909165e1c313d04baf2405c8f0f78badbc18ca`.
Kernel remains `6.12.75+rpt-rpi-2712`. These finite, uncalibrated digital
observations do not establish analog quality or exclude sub-sample glitches.

Helpers 4155/4193 reported normal-zero/20-ms final cached state, disable and
fresh-export release, with no cleanup errors. Before/after temperatures were
51.80→52.90°C direct and 50.15→50.70°C half50; firmware flags were zero.
Read-only loaded postflight found all recorded helper/launcher/worker PIDs
absent, both test pins low and no test exports. The separate fan owner and
boot configuration remained intact. Informational gRPC fork/poll stderr is
retained, rather than described as empty. Only GPIO18/header RP1 channel2 was
driven; providers stay bound until reboot, and production/Blinka are unchanged.

The original loaded archive remains immutable:
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-loaded-evaluation.tar.gz`,
151,928 bytes, SHA256
`4e63afe5f416ad5a04ed79fa406960b2268a218886125f7c343f386bcbeb0b10`.
Fresh extraction byte-matched all 51 top-level targets (63 regular files),
including both actual captures, sidecars, original load-only receipts,
pre/postflight and the exclusive pre-handshake recorder/test snapshots.

### Pi 5 self-SIGTERM from inverse-zero high

Two separate `sigterm-high-v1` diagnostic captures command low, then hold
enabled inverse-zero high for 0.3 s before sending real `SIGTERM` once to the
helper's own PID. The active safety guard raises the recorded
`SafetyAbort: Stopped by SIGTERM`; inherited conservative cleanup verifies
normal-zero low, disables and releases the fresh export. The dedicated helper
exits zero only for `expected-sigterm-abort-cleaned` with independently passing
post-abort checks. Both reports explicitly have `completed_normally=false` and
`expected_abort_observed=true`: these are expected-abort diagnostic passes,
not ordinary experiment completion.

| Capture | Raw edges | Strict `accepted` | Initial low (s) | Continuous high (ms) | Final low (s) |
| --- | --- | --- | --- | --- | --- |
| `oct6-pi5-sigterm-high` | 2 | `true` | 2.50791225 | 300.65130 | 1.80386013 |
| `oct6-pi5-sigterm-high-r2` | 2 | `true` | 2.91475851 | 300.96428 | 1.73093449 |

Each unfiltered trace contains exactly one rising and one falling edge, with
no captured high dip or later reassertion. Acquisition receipts retain helper
return code zero, no primary/evidence errors, a 0.5-s observation lead and
1.2-s post-helper tail. Original analyses reproduce independently from raw
binary and physical Logic8/channel0 SAL settings at 100 MSa/s. Pi clocks are
not synchronized with Saleae; the high width is not a signal-to-low latency
bound. Finite sampled threshold evidence is not analog proof or exclusion of
shorter/non-threshold-crossing transients, and this deliberate self-signal case
does not cover arbitrary interruption timing or every possible failure.

PIDs 4281/4309 targeted themselves with signal15 under a nondeferred active
guard. Both fresh channel2 exports were absent after cleanup; final cached
readbacks were normal polarity, duty0, period20 ms and disabled, with no
cleanup errors. Independent before/after-cleanup temperatures were
47.40→47.40°C and 47.95→46.85°C, flags zero. The dedicated exit0 postflight
found both PIDs absent, no test exports, GPIO18/23 low, unchanged boot SHA and
only the separate fan consumer owned, at 48.3°C/flags zero. Its first combined
`pinctrl get 18 23` read-only query failed syntax; the retained receipt records
the completed separate-query retry. Runtime providers remain bound until
reboot; unexport is not pinmux restoration.

All five executed source hashes match frozen files. The SIGTERM helper is
`2db935b3e86c75f12354fc5cfbe2fbeb8fdc016b62dcc93776eff69fafaa7279`.
A new exclusive recovery archive preserves only these two captures, exact
helper/capture/analyzer dependencies and tests, and the dedicated postflight;
per-run remote before-snapshots supply the available actual preflight evidence.
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-sigterm-evaluation.tar.gz`
is 102,400 bytes, SHA256
`4368db377b5349942f156e566bd012d0e4c3151067da4960edefb9bb71905f87`.
All 26 top-level targets (38 regular files) byte-match a fresh extraction.
No guarded files or earlier captures were added to this archive.

These loaded and signal tests are strict passes for narrowly defined diagnostic
protocols. **Baseline parity and production-backend readiness are not yet
established.** Earlier frequency-transition rejections remain unchanged;
broader lifecycle, interruption, load, frequency and update-latency coverage is
still required before adoption. No production code or Blinka integration changed.

### Pi 5 single-period plus 1-ms guard characterization

The separate `enabled-single-period-guard-v1` wrapper changes only the earlier
two-period transition waits to one applicable nominal requested period plus
1 ms: 21 ms at 50 Hz and 3 ms at 500 Hz. A changed period waits
`max(old,new nominal period)+1 ms`; the preceding normal-zero wait remains
separate. Thus normal 50→500-Hz changes request 42 ms total settling and
500→50-Hz changes request 24 ms, instead of 80/44 ms. All actual scalar
writes, readbacks, fresh ownership and conservative disabled cleanup remain
the frozen settled implementation. The guard is a characterization choice,
not a latch acknowledgment, physical-settling or production-latency guarantee.

Eight unloaded acquisitions repeat the same four fixed shapes without
changing any original physical predicate. Every raw edge remains evidence.

| Guarded profile (`oct6-pi5-guarded-` prefix) | Strict first / `-r2` | Edges first / `-r2` | First continuous highs (ms) | Repeat continuous highs (ms) |
| --- | --- | --- | --- | --- |
| `direct` | `true` / `true` | 526 / 526 | 300.93630, 300.55666, 622.40221 | 300.92927, 300.54101, 622.37977 |
| `frequency` | `false` / `false` | 484 / 484 | 944.17310 | 944.13325 |
| `lifecycle` | `true` / `true` | 446 / 446 | 301.02423, 300.58574 | 300.98645, 300.55714 |
| `half50-direct` | `true` / `true` | 82 / 82 | 300.96886 | 300.96489 |

All outgoing and recovery ordinary pulses are complete, with no unexpected
high, captured high-hold dip or sub-microsecond low run. Width/within-group
period ranges remain servo50 1500.02–1500.03/20000.88–20000.89 µs,
half500 1000.06–1000.07/2000.10–2000.11 µs and half50
10000.59–10000.60/20000.88–20000.89 µs. Both lifecycle runs contain 201
complete 500-Hz pulses, within the unchanged one-cycle allowance, and two
fresh export/unexport generations. Their physical low separators are
655.59297/655.74758 ms. Final-low tails across the eight traces are
0.79306415–2.06207257 s.

**Both frequency traces remain strictly rejected**, now for exactly the two
ordinary frequency-change quiet gaps. Boundary rising-edge intervals are
46.00210/26.00121 ms first and 46.00210/26.00120 ms repeat, neither a
complete configured 20-ms nor 2-ms period. Their approximately 944-ms high
holds now satisfy the unchanged nominal 0.9 s ±0.05 s window; removing that
prior high-width rejection does not remove the two gap rejections. These
strict uninterrupted-pulse diagnostic rejections are not, by themselves, an
established baseline-parity failure or CircuitPython API violation. Conversely,
the other diagnostic passes are not proof of baseline parity or readiness.

The shorter waits reduce observed **Pi-side transition command/readback
durations**, measured from phase `begin_ns` to `stable_begin_ns`. Across the
two unloaded repetitions per shape:

| Transition | Earlier two-period strategy (ms) | Guarded strategy (ms) |
| --- | --- | --- |
| Normal 50 Hz → high | 40.553–40.844 | 21.528–21.608 |
| Normal 500 Hz → high | 4.540–4.823 | 3.542–3.558 |
| Active 50 → 500 Hz | 80.906–81.371 | 42.912–43.449 |
| Active 500 → 50 Hz | 45.316–45.322 | 24.920–24.930 |
| Inversed-zero frequency change | 40.620–40.673 | 21.617–21.664 |

These include deliberately requested waits and userspace/sysfs work, not
synchronized electrical latency. For example, guarded half50 outgoing-to-high
low gaps are 12.83989/12.97866 ms, versus earlier 31.83075/31.81675 ms;
high-to-recovery gaps remain 16.20574/16.07096 ms. A faster cached readback
does not confirm the physical latch or establish a maximum signal response time.

Two additional short coordinated load acquisitions use two independently
expiring ten-second CPU-only workers:

| Capture | Strict `accepted` | Edges | Continuous highs (ms) | Final-low tail (s) |
| --- | --- | --- | --- | --- |
| `oct6-pi5-guarded-direct-loaded-r2` | `true` | 526 | 300.91965, 300.59209, 622.43044 | 2.36100436 |
| `oct6-pi5-guarded-half50-loaded-r2` | `true` | 82 | 300.92641 | 0.64980927 |

Both retain the complete ordinary pulse topology and ranges above, with no
captured high dips or partial pulses. Base coordination and separate guarded
wrapper receipts validate the exact pinned sources and actual integer-zero
load-helper, recorder and capture exit codes; no errors were recorded.
Workers 4710/4711 completed 41061/42030 iterations, and workers 4748/4749
completed 42035/41974, each in approximately ten seconds and reaped with
return code zero. Every phase and the entire GPIO helper are bracketed by
each actual worker interval. Minimum whole-helper start/end margins are
3.562648/2.857547 s direct and 1.983659/6.230897 s half50. Original PWM
and overlap analyses reproduce independently, including a separate raw/SAL
audit. Despite the fresh `-loaded-r2` names, there is only **one actual guarded
loaded capture per profile**, not repeated or saturated-load coverage. Two
recorded workers demonstrate concurrent CPU work, not full four-core saturation;
receipt timing assumes the same Pi/boot monotonic clock.

All ten acquisitions retain physical Logic8/channel0, unfiltered 100 MSa/s,
0.5-s lead/0.2-s tail and every raw edge on kernel
`6.12.75+rpt-rpi-2712`. The nominal 10-ns resolution is uncalibrated finite
digital-threshold evidence, not analog quality or exclusion of sub-sample
transients. Pi timestamps remain unaligned with Saleae. Only GPIO18/header
RP1 channel2 was driven; GPIO23 and the separate fan were not targeted.
Every helper reported normal-zero/20-ms cached cleanup, final disable and
fresh-export release without errors. Idle temperatures were 47.40–49.60°C;
loaded endpoints were 51.80→53.45°C direct and 50.15→50.70°C half50,
with firmware flags zero. Final exit0 postflight found all sixteen recorded
helper/launcher/worker PIDs absent, both pins low, no test exports, only the
separate fan owned, unchanged boot SHA and 45.5°C/flags zero. Providers remain
bound until reboot; unexport does not restore pinmux.

Executed guarded helper SHA256:
`142f0afcc8786252ade1a461386715d0d5dbb2f8394c26dcbb40eb34ab635b0b`.
The loaded wrapper SHA256 is
`12278b86ee92c6d5c2f2af9e3d9f3017b0b3e44fb12e7aea6595d94a81e45226`.
All five reported helper hashes and retained coordinator/recorder/capture
hashes match exact frozen sources. The preflight records 87 selected
hardware-free guarded/regression tests; the new loaded wrapper had 23 fake
cases, 56 with original coordinator regressions, and selected lint passed.

A new exclusive recovery checkpoint preserves all ten complete captures,
35 exact dependency/test files, twelve outside loaded sidecars and three
inspection receipts. The prior SIGTERM postflight is included only as the
initial inspection explicitly referenced by guarded preflight; no earlier
capture or archive is rewritten.
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-guarded-evaluation.tar.gz`
is 389,120 bytes, SHA256
`b76925bff876bde8d9232cd40d2d72358cc13327ebb51d394883cc82a2895f4d`.
Fresh extraction byte-matched all 60 top-level targets (122 regular files).
Baseline parity remains unestablished, and production/Blinka are unchanged.

### Pi 5 original-lgpio reference after a clean boot

Six separate acquisitions run the byte-identical original Blinka `PWMOut`
and `lgpio_pin` files from commit
`beb49bf8ea9305dacbd14b08525f234eda563c02`, using distro
`lgpio.py_0.2.2.0` under `/usr/bin/python3`. A controlled reboot removed the
runtime test providers without hot-unbinding them; kernel
`6.12.75+rpt-rpi-2712` and boot-configuration SHA stayed unchanged.
GPIO18 was freshly claimed on the discovered RP1 `/dev/gpiochip0`; GPIO23
and the separate fan were not targeted. This is an unloaded, before-versus-after
clean-boot comparison, not a same-boot, calibrated or load-controlled benchmark.

The first capture's authoritative report is
`oct6-pi5-lgpio-baseline-direct/analysis-rounding-corrected.json`.
Its original `analysis.json` and the exclusive analyzer/test
`*_rounding_v1.py` snapshots remain unchanged: they incorrectly treated 4915
as 8%, with a 1600-µs nominal width. The original formula actually gives
`100*4915/65535 = 7.499809262226291`, which rounds to **7% and 1400 µs**
at 50 Hz. This is different from the kernel diagnostic's approximately
1500.02-µs pulse for the same logical duty. Later five reports use the corrected
formula. All six authoritative reports exactly reproduce offline from the
original SAL, every binary edge, acquisition and source/ownership receipts.

The following counts are descriptive width bins, not acceptance thresholds.
Ordinary-bin counts are 50-Hz/7%, 500-Hz/50%, then 50-Hz/50%; a ±2% bin does
not discard the separately counted unmatched high runs. All captures have
`collection_success=true`, but `waveform_accepted=null` and `parity_pass=null`.

| Original-lgpio profile (`oct6-pi5-lgpio-baseline-` prefix) | Edges | Ordinary-bin counts | Unmatched highs | Continuous highs (ms) |
| --- | --- | --- | --- | --- |
| `direct` | 516 | 56 / 193 / 0 | 6 | 301.29867, 300.89860, 601.21023 |
| `direct-r2` | 512 | 51 / 194 / 0 | 8 | 301.88139, 301.47738, 602.29147 |
| `frequency` | 482 | 39 / 197 / 0 | 4 | 901.22782 |
| `frequency-r2` | 464 | 40 / 186 / 0 | 5 | 901.09150 |
| `half50-direct` | 80 | 0 / 0 / 39 | 0 | 310.34298 |
| `half50-direct-r2` | 80 | 0 / 0 / 39 | 0 | 310.32369 |

The 23 unmatched highs remain in the reports and raw recordings: two
500-Hz-region widths are 1022.25–1024.51 µs, eleven are
1037.73–1047.77 µs, and ten 50-Hz-region widths are 1428.19–1447.03 µs.
The bins do not establish which command caused an individual anomaly.
Each half50 run contains 20 outgoing and 19 recovery pulses, rather than
the guarded diagnostic's 20/20. Their high ranges are
9999.17–10049.14 and 9999.40–10015.80 µs. No transition trimming or glitch
filtering is applied, and no sub-microsecond interior low run is recorded.
Final-low tails are 0.68775598–1.29092036 s. These counts and width variations
must not be replaced by only steady-state or matched-bin statistics.

Original setter events take 5.891–25.153 µs, including instrumentation and
logging, with no additional settling waits. Matched logical-phase
`begin_ns`→`stable_begin_ns` durations expose the guarded strategy's deliberate
caller-response tradeoff:

| Matched phase | Original-lgpio first / repeat (µs) | Guarded first / repeat (µs) |
| --- | --- | --- |
| `direct.high50_first` | 19.229 / 24.259 | 21598.551 / 21596.418 |
| `direct.high500` | 21.988 / 20.340 | 3551.678 / 3542.048 |
| `frequency.pwm500_d32768` | 36.524 / 25.487 | 43449.285 / 43368.817 |
| `frequency.pwm50_d4915_recovery` | 25.002 / 25.931 | 24919.893 / 24930.261 |
| `direct.high50_after_frequency` | 11.670 / 16.957 | 21664.070 / 21634.641 |

Both protocols reach matching logical phase targets, but the kernel helper
combines frequency and duty changes; the original invokes the frequency setter
and then the duty setter when each changes. This is not the same public-API
implementation or a synchronized command experiment. Pi clocks are not aligned
to Saleae, and these caller durations do not measure command-to-edge latency.
If adopted, the guarded waits would block callers materially longer; that is a
prototype responsiveness regression/tradeoff, not a change to production code.
The strategy has **not been shown on-par** with the original. The smallest next
comparison is the actual native draft API using the same setter order, before
expanding the kernel prototype or claiming a default migration.

Physical Logic8/channel0 SAL settings confirm unfiltered 100 MSa/s, with a
0.5-s lead and 0.2-s tail and actual helper/collection exit0. The 10-ns nominal
sample interval is uncalibrated finite threshold evidence, not analog proof,
sub-sample-glitch exclusion or a latency guarantee. API frequency/duty/enabled
readbacks are software state, not electrical measurements. The bench separately
adds PWM cancellation, low drive, 100-ms settling, GPIO read0/`tx_busy`0,
free/release and private chip close; these safety steps are **not the original
deinit behavior**. All six fresh claims released without errors or signals.
Per-run temperatures were 47.40–50.15°C with flags zero; no load workers ran.
The 14-s normal-execution watchdog excludes cleanup and does not protect against
SIGKILL or a native-library hang.

The completed exit0 postflight found PIDs 1920/1954/1972/1990/2008/2026 absent,
GPIO18 released but still output-low, GPIO23 unclaimed input, only the separate
fan PWM provider owned, unchanged boot SHA and 47.7°C/flags zero. Its earlier
read-only fan-consumer query exited1 and is retained with the corrected retry.
Release does not restore input pinmux. The preflight also retains the initial
helper's missing legacy-label failure before any lgpio import/claim and its
corrected, source-pinned read-only preflight.

Executed helper SHA256:
`8018a1766c711a9babe8d98c4f1f77412f23876c4e7fdc96bd012caaf3808b2f`.
Corrected analyzer SHA256:
`f099d76048b018bd976515fd1e65fd86563cfd5b619f50553815d74085918995`.
All four executed source hashes match the exact retained files; 82 current
hardware-free helper/collector/analyzer cases and scoped lint passed.
The new exclusive checkpoint
`hardware-evaluation/2026-10-06/kernel-pwm-pi5-lgpio-baseline-evaluation.tar.gz`
is 225,280 bytes, SHA256
`3e57dc44227a3046e0dbc2ce412326a726db5cb26bedd10d7fc13f0d36f895ab`.
Fresh extraction byte-matched all 22 explicit top-level targets (59 regular
files): six captures, exact dependencies/tests, the prior preflight helper,
prior rounding analyzer/test and pre/postflight. The 14-MB full runtime backup
remains separately preserved locally/remotely and is not duplicated here.
Earlier diagnostics, rejections and archives remain unchanged. **Baseline
parity/default-backend readiness are unestablished; production is unchanged.**

## Pi 5 default-native 50 Hz duty-update comparison, October 7

Two idle recordings now exercise the actual draft public API against the two
retained original-lgpio `half50-direct` references. The sequence is 50 Hz,
duty `0 → 32768 → 65535 → 32768 → 0`, held for
0.2 / 0.4 / 0.3 / 0.4 / 0.2 seconds. Both scheduler options remain off and
`variable_frequency` retains its default `False`. The draft receives the
explicit, preflight-verified RP1 controller plus offset18; the original Pin
resolves the same controller/line. Only duty setters run, avoiding the original's
different writable-frequency behavior. There are no added sequence settling
waits; the separately recorded 100-ms low settle belongs to bench cleanup.

The installed Python files and all six retained native C/header files match
production source at `80d5f69` (unchanged since `d5debaf`). The previously built
extension is source-pinned and preserved, not rebuilt for this comparison.
The bench still uses kernel `6.12.75+rpt-rpi-2712`, Python3.13.5, and native
gpiod2.5.0. Boot ID/configuration match the original references. No kernel PWM,
PIO, bench scheduler/priority/affinity change, load worker, or fan write is used.
CPU scaling is not fixed: native repeat2 records 1.9→2.4 GHz.

Before capture, `oct7-native-half50-plan.json` froze narrow, worst-observed
baseline envelopes and pulse-count checks. Its SHA256 is
`ebf2c59ea9e00dac0f3ea88e105ef47898c45e336aed453671dc3c38c6801d7a`.
These are investigation flags derived from only two baseline samples, not
calibrated statistical acceptance or an overall backend-parity verdict.

| Observation | Original first / repeat | Native first / repeat |
| --- | --- | --- |
| Initial / recovery ordinary highs | 20/19 · 20/19 | 21/20 · 21/20 |
| All captured edges | 80 / 80 | 84 / 84 |
| All ordinary high widths (µs) | 9999.17–10049.14 / 9999.40–10015.80 | 9997.03–10004.35 / 9998.80–10004.93 |
| Within-region rise periods (µs) | 19984.95–20059.70 / 20008.73–20032.11 | 19996.29–20003.47 / 19996.74–20003.58 |
| Continuous-high duration (ms) | 310.34298 / 310.32369 | 290.16527 / 290.13674 |

Native high-width error against the common 10000-µs reference is at most
4.35 / 4.93 µs; against its exact 32768/65535 target of 10000.15259 µs it is
4.19741 / 4.77741 µs. Native period error is at most 3.71 / 3.58 µs.
All 41 interior lows per native capture are retained, including the two hold
boundaries: 9998.01–10004.20 / 9997.64–10003.73 µs. Neither native trace has
unmatched high runs or sampled sub-microsecond interior lows. The finite,
uncalibrated 10-ns nominal sampling interval cannot exclude sub-sample glitches
or establish analog signal quality.

Both native reports flag exactly `initial_pwm_high_count` and `edge_count`:
21 instead of the declared 20 initial highs, and 84 rather than 80–82 edges.
The count limits remain unchanged; no boundary pulse is trimmed. Other
predeclared physical and caller-return envelopes are met. Each trace contains
41 ordinary highs plus one continuous-high run. Relative to the original,
there is one extra ordinary high in each PWM region, not just the flagged
initial-region difference; the recovery allowance was already 19–20.

The worker samples a configuration at cycle entry. Configuration wakes do not
truncate its high/low deadlines, so an update arriving after a cycle starts
can leave that full outgoing cycle in place. Endpoint-to-interior recovery
can merge its first high into the continuous-high run. That mechanism is
consistent with these counts and shorter physical holds, but unaligned Pi and
Saleae clocks do **not** prove which command caused a specific edge, nor exact
command-to-electrical latency. Different boundary counts are a qualification
of this comparison, not automatically a materially worse PWM implementation.

Recorded initial/high/recovery/final setter durations are
8.296 / 7.426 / 5.241 / 3.944 µs and
9.592 / 5.315 / 3.703 / 3.685 µs, versus original
15.501 / 9.175 / 11.543 / 8.028 µs and
14.707 / 12.340 / 22.699 / 17.112 µs. These instrumented caller-return
observations meet every frozen per-scope maximum; they are not synchronized
electrical response measurements and do not imply immediate application.
The kernel prototype's deliberate millisecond waits are absent here.

Both collectors and remote helpers actually exit0. SAL settings independently
confirm physical Logic8/channel0, 100 MSa/s, no glitch filter and no analyzers;
raw version 0 exports omit a sample-rate field, so SAL supplies that provenance.
Every raw edge, stdout, and nonempty informational gRPC-fork stderr is retained.
Private GPIO18 claims are followed by duty 0, 100-ms settle, inactive 0 readback
on that owned request, deinit, and read-only unused-line verification. No
primary/cleanup error or signal is recorded. Temperatures are
46.85→48.50°C and 46.30→48.50°C, with firmware flags 0 throughout.
The normal-execution 14-s watchdog cannot bound a native hang or SIGKILL.

The independent, exit0 postflight at 19:10:59 UTC finds both helper PIDs absent,
GPIO18 unclaimed/output-low, GPIO23 unclaimed/input, unchanged boot SHA, and
only the separate cooling-fan PWM provider owned. Release still does not
promise restoration of input pinmux. A separate raw binary/ZIP audit reproduces
counts, widths, holds, boundaries and receipt provenance without importing the
new analyzer. The package suite passes 102 GPIO-free tests on Linux and
73 with 29 Linux-only skips on macOS; the new recording/analysis fakes pass 63.
Formatting and scoped isolated Ruff checks pass.

The exclusive recovery archive
`hardware-evaluation/2026-10-07/native-pi5-half50-evaluation.tar.gz` is 167,851
bytes, SHA256
`5d47826cb38be70f1c27412b66ebf19c9c1c6d918339440f518353404f18a7dc`.
Fresh safe extraction byte-matches 22 explicit top-level targets (51 regular
files), and both native reports, both original reports and the paired report
reproduce exactly from that extraction. Exact scripts/tests/dependencies,
frozen plan/manifest, compiled extension, source snapshot and pre/postflight
are included. Earlier archives and diagnostics remain unchanged.

This is encouraging low-frequency idle timing evidence, not a migration gate
pass. Frequency-changing native API comparisons (with `variable_frequency=True`
explicitly recorded), repeated loaded comparisons, electrical update-response
bracketing and distinct-pin coexistence remain next. **Overall baseline parity
and default-backend readiness remain unestablished; production is unchanged.**

## Pi 5 native frequency/direct and matched loaded updates, October 7

Four additional idle captures exercise the native public API with the exact
original `frequency` and `direct` setter order and dwell sequences, twice each.
Twelve fresh captures then compare both backends under the same fixed two-worker,
ten-second CPU load: `frequency`, `direct`, and `half50-direct`, twice per backend.
The first repetition runs original then native, the second native then original.
No PIO, kernel PWM, affinity, governor, priority or fan change is made.
Production source remains unchanged at `5dd0fd0` (native sources unchanged since
`d5debaf`); the installed, previously preserved extension is not rebuilt.

Native direct/frequency construction explicitly enables `variable_frequency`.
The original retains its default `False` but nevertheless permits frequency
writes. This is a recorded API difference, not a drop-in compatibility verdict.
Both native scheduler options stay off; native half50 keeps the public default
`variable_frequency=False`. All outputs use the verified RP1 controller/GPIO18.

Before any new waveform, `oct7-native-updates-plan.json` freezes the sequences,
targets, diagnostic rules and narrow idle-reference envelopes. SHA256:
`f0850799856c0d20b54935d6d584c9e10e5f98642a23e24e9e35771d59990a9b`.
Loaded runs retain those idle limits as flags, not loaded acceptance criteria.
The old half50 plan is unchanged. No limits are relaxed after recording.

Unlike original-lgpio's rounded integer-percent duty, native timing uses its
rounded-nanosecond 16-bit target. At duty4915/50Hz those targets are respectively
1400 and 1499.962 µs; at duty32768/500Hz they are 1000 and 1000.015 µs.
The analyzer separately reports errors against the common requested 16-bit
value. It retains every high, low and adjacent-rise interval; unmatched highs
remain in nearest-stable-regime error statistics. Nearby possible intermediate
widths are described separately, not treated as proof of a particular command.
No edge is trimmed to improve a comparison.

Idle frequency captures both have 466 edges and 21/191/20 ordinary pulses,
plus one continuous-high run of 900.20069/900.19236 ms. Their only frozen flag
is the extra initial pulse (21 rather than 20). Both idle direct captures have
528 edges and 21/20/200/20 ordinary pulses plus three holds. Their first two
holds are 281.65505/281.14566 ms and 281.65294/281.14754 ms, versus original
301.29867/300.89860 ms and 301.88139/301.47738 ms. The requested dwell is 300 ms.
Counts, total edges, those two hold durations and the recovery500 duty-setter
caller duration are flagged. Native setters there take 11.907/11.444 µs versus
the retained original per-scope maximum of 6.805 µs. Every idle normalized
high/period/interior-low envelope is met; none of these four traces contains an
unmatched high, nearby intermediate-width high or sampled sub-µs low.

The following loaded maxima include anomalous nearest-regime highs. Period and
low figures describe adjacent ordinary pulses within the same observed regime;
all boundary intervals remain separately available in each report. These are
worst observations across two short recordings, not distribution/tail guarantees.

| Loaded mode / ordinary region | Original max absolute high / period / low error (µs) | Native max absolute high / period / low error (µs) |
| --- | --- | --- |
| Frequency / 50Hz duty4915 | 43.87 / 44.06 / 43.78 | 330.018 / 30.08 / 327.238 |
| Frequency / 500Hz duty32768 | 1.57 / 2.89 / 2.93 | 12.715 / 0.91 / 11.805 |
| Direct / 50Hz duty4915 | 47.73 / 48.55 / 47.93 | 5.312 / 3.52 / 4.032 |
| Direct / 500Hz duty32768 | 46.52 / 49.57 / 46.17 | 22.015 / 22.41 / 22.875 |
| Half50 / 50Hz duty32768 | 41.52 / 35.28 / 40.47 | 4.007 / 3.43 / 3.873 |

The native frequency repeat2 has a concrete retained outlier: high pair227 is
1829.98 µs, 330.018 µs above its native target; its adjoining low is 18172.80 µs,
327.238 µs below target. That is worse than the original in this finite pair and
flags the native high/low idle envelopes. Native direct repeat1 also retains a
978.00-µs high (pair174, −22.015 µs), outside the diagnostic 2% bin but within
the frozen error envelope. Original loaded captures also contain unmatched
highs; their anomalies are included in the table rather than hidden by bins.
No loaded recording contains a sampled sub-µs low or nearby intermediate-width
high. Better typical results elsewhere do not dismiss the 330-µs outlier.

Loaded direct native holds remain about 281.66/281.17 ms against original
301.40/301.00 ms. Loaded half50 native holds are 290.17424/290.13865 ms against
original 309.99920/309.99950 ms; ordinary counts remain 21/20 against 20/19.
This agrees with the earlier observed boundary difference. The worker finishes
the cached outgoing cycle's deadlines before adopting new configuration, but
Pi phase clocks are not aligned to Saleae: these holds and fast caller returns
do not measure command-to-electrical application delay. GPIO23 marker bracketing
is the next measurement, not a claimed result of these captures.

All twelve collectors, PWM helpers and fixed CPU-load helpers actually exit0.
Raw worker-start/completion receipts independently confirm both workers bracket
every phase and the entire PWM helper in all twelve runs, not just that launch
succeeded. Worker durations are 10.000009791–10.000246195 seconds, with positive
iteration counts. This establishes overlap, not whole-machine saturation or
electrically aligned latency. Per-run temperatures are 47.95–53.45°C and all
firmware throttling flags are zero. Cleanup receipts record owned low readback,
private release and no primary/cleanup errors or signals. Original cancellation,
low settling and release are additional bench safety, not original deinit behavior.

The read-only postflight at 19:54:40 UTC confirms all 52 recorded PWM/load PIDs
absent, GPIO18 unclaimed/output-low, GPIO23 unclaimed/input, unchanged boot ID
and configuration SHA, only the separate fan PWM provider, and 46.85°C/flags0.
Every SAL/raw edge and stdout/stderr receipt is preserved. Independent raw/ZIP
and worker-receipt auditing agrees with the new reports; 456 hardware-free
helper/collector/analyzer/load cases and scoped lint/format checks pass.

Recovery archive details are recorded in
`hardware-evaluation/2026-10-07/README.md`. Earlier archives, the historical
rounding-error report and its corrected report remain unchanged. The checkpoint
preserves exact executed scripts, tests, frozen plans/manifests, compiled native
source/binary provenance, all new captures, unchanged original idle references,
loaded overlap receipts, independent audit and postflight.

These results justify continued evaluation, not a backend switch. The loaded
outlier and endpoint-update response need investigation; longer matched timing,
distinct-pin coexistence and wider board coverage remain. **Overall on-par
behavior and default-backend readiness are unestablished; production is unchanged.**

### Loaded frequency outlier recurrence follow-up

Four further matched frequency pairs (eight captures) use the same untouched
helpers, default flags, public setter sequence and two ten-second CPU workers.
Backend order alternates original/native and native/original. A separate plan
is frozen before capture, SHA256
`6798dc13b9214aff0217f715b56f457c895f5cd20202df75c6bc30f127fc6758`.
The previous investigation limits remain unchanged. New >50/>100/>250-µs
absolute-high-error counts and type-7 percentiles are explicitly descriptive,
not acceptance gates. All nearest-regime anomalous highs remain included.

| Follow-up backend / ordinary region | High count | Max / median / p95 / p99 absolute high error (µs) | >50 / >100 / >250 µs |
| --- | --- | --- | --- |
| Native / 50Hz duty4915 | 164 | 6.542 / 0.622 / 2.232 / 3.2137 | 0 / 0 / 0 |
| Native / 500Hz duty32768 | 764 | 29.065 / 0.365 / 0.6835 / 2.532 | 0 / 0 / 0 |
| Original / 50Hz duty4915 | 160 | 3.920 / 0.330 / 1.257 / 2.1146 | 0 / 0 / 0 |
| Original / 500Hz duty32768 | 784 | 125.260 / 0.150 / 0.400 / 5.286 | 1 / 1 / 0 |

The original 125.260-µs error occurs in followupA-r1 pair160: high1125.26 µs,
following low879.65 µs and rise period2004.91 µs. Native extrema include a
970.95-µs high (−29.065 µs) and a 1025.12-µs high (+25.105 µs). No nearby
intermediate-width high or sampled sub-µs low occurs. Every edge, anomaly and
boundary remains preserved. Native ordinary counts are 21/191/20 with 466
edges each; original counts are 20/191–200/20 with 464–482 edges.

The earlier native 330.018-µs observation remains in a separate evidence group,
with one sample above each cutoff. It is not removed or pooled away. Its cause
is unresolved: no recurrence in these four additional native captures is not
a tail guarantee or proof that the earlier event was harmless. Native median
errors are slightly larger here while its worst 500Hz observation is smaller;
these finite distributions do not establish general on-par behavior.

All sixteen actual new workers bracket every phase and the entire PWM helper;
durations are 10.000008177–10.000212883 seconds. Independent raw/SAL and receipt
recomputation matches every per-capture/aggregate percentile and cutoff count.
The read-only postflight at 20:08:05 UTC confirms all 84 recorded PIDs absent,
pins unclaimed (GPIO18 low), unchanged boot configuration, only the fan PWM
provider and 45.75°C/flags0. Thirty-one new offline analyzer cases pass.
Pi phase clocks remain unaligned to Saleae and no electrical latency is inferred.

The additional exclusive archive
`hardware-evaluation/2026-10-07/native-pi5-frequency-followup-evaluation.tar.gz`
is 1,489,337 bytes, SHA256
`540722861b7e3aa50a95d29b892ac7db66ca8d880de1373e765175ee54b2463a`.
Fresh safe extraction byte-matches 186 explicit targets / 384 regular files,
reproduces all 24 new reports across both checkpoints, the five earlier paired
reports and the complete follow-up distribution report. Previous matrix data
is included as an exact dependency; older archives remain unchanged.
Electrical marker bracketing remains the next measurement. Production is unchanged.

### Same-acquisition GPIO23 electrical markers

Four idle captures now record PWM GPIO18/channel 0 and a private GPIO23/channel 1
marker in the same physical acquisition. The frozen 31-phase protocol alternates
ordinary/high/recovery/low at 50 and 500 Hz, then changes frequency. Every changed
public setter is bracketed by GPIO23 high-before / low-after writes. There are
32 sequence markers per run, plus one separately categorized native low-cleanup
marker. Native keeps both scheduler options off and enables variable frequency;
original defaults False but permits writes. No production implementation changes.
The pre-capture plan SHA256 is
`bf5f530a0e6c8d8c4956d307ccfb86ba386453eee166dddef5d6205178f4f63f`.

All four helpers/collectors exit 0 with independent owned-low/release receipts
for both pins. PWM edges are 378/398/398/378, marker edges 64/66/66/64, in
original/native/native/original order. Every marker pairs strictly by validated
setter ordinal and scope. Both raw channels are complete and low at their ends;
neither contains a sampled sub-µs interior low. SAL confirms physical channels 0/1,
100MSa/s and no glitch filtering. Selected-source hashes cover eighteen files,
not a whole-system attestation; library versions are gpiod 2.5.0 / lgpio 0.2.2.0.

Twenty-one of the 24 ordinary-to-high commands have PWM unambiguously low at
marker rise and one subsequent sustained-high run identifiable before the next
marker. Three original 500Hz cases are already high and remain ambiguous.
The intervals below are `[PWM edge − marker fall, PWM edge − marker rise]`.
Ranges span the smallest lower to largest upper endpoint, not confidence
intervals or backend guarantees. Per-trial bounds remain in each report.

| Observed physical event | Native range | Original range | Eligible observations per backend |
| --- | --- | --- | --- |
| 50Hz ordinary→high sustained-run start | 6.90198–16.92831 ms | 4.24873–15.14301 ms | 6 / 6 |
| 500Hz ordinary→high sustained-run start | 924.86–935.91 µs | 208.14–885.29 µs | 6 / 3; three original cases ambiguous |
| 50Hz high→ordinary first fall | 1.50373–1.51618 ms | 5.56573–16.44938 ms | 6 / 6 |
| 500Hz high→ordinary first fall | 1.00509–1.01429 ms | 1.12656–2.67505 ms | 6 / 6 |

Both implementations can wait through part of an ordinary PWM cycle before
the continuous-high run starts. Recovery first falls include the resumed high
width (native/original nominal 1499.962/1400 µs at 50 Hz, 1000.015/1000 µs at 500 Hz).
They are not exact internal adoption/start delay. Native 50-Hz observed holds
are 104.67308–114.69340 ms, original 121.39890–121.39903 ms, for 120-ms commanded
dwells. At 500 Hz the 60-ms dwell yields native 60.15564–60.15985 ms versus
original 60.99921–60.99981 ms. Observed start/recovery-fall differences delimit
these widths; shorter native holds alone do not establish a slower endpoint
response. No source-causal or general on-par conclusion follows from these
unequal phase positions and finite samples.

Same-acquisition channels support physical marker-relative intervals, but Pi
clocks remain unaligned. GPIO-driver/threshold skew and Saleae timebase are
uncalibrated; 10-ns nominal samples are not analog or sub-sample glitch proof.
Markers add caller overhead and do not identify an exact invocation instant.
Already-high/low cases and recovery timing retain their ambiguities; a >30-ms
high tag is descriptive, not automatic command proof. All edges, complete highs,
nearby periods and both marker-boundary levels are retained without trimming.

Independent raw/SAL/receipt reconstruction matches all 21 eligible starts,
three ambiguous cases and 24 recovery intervals exactly. The 63 hardware-free
marker/helper/collector/analyzer cases and scoped lint/format checks pass.
Temperatures are 46.30–48.50°C with firmware flags 0. The read-only postflight
at 20:21:23 UTC confirms all 88 recorded PIDs absent, both GPIO18/23 unclaimed and
output-low, unchanged boot ID/configuration, only the fan provider, and 47.40°C.
Release does not restore input pinmux. Normal watchdogs still cannot bound
native hangs, SIGKILL or hardware faults.

The exclusive recovery archive
`hardware-evaluation/2026-10-07/pi5-electrical-marker-evaluation.tar.gz` is
458,154 bytes, SHA256
`753ad8992ffb5c1839f6e96193ffe9e9ba6701acb9e2c70cde334fc5aa21098e`.
Fresh safe extraction byte-matches 31 explicit targets / 66 regular files and
reproduces all four reports exactly. Exact executed helpers, analysis/test
dependencies, frozen plan/manifest, selected-library hashes/versions, pre/postflight,
independent audit and preserved native binary/source provenance are included.
Previous archives remain unchanged. Dual-output operation and independent
shutdown/restart are next; production and Blinka remain unchanged.

### Endpoint source comparison and native dual-output lifecycle

The upstream lgpio v0.2.2
[`xSetAsPwm` implementation](https://github.com/joan2937/lg/blob/b959a17d723360e85648316757b02dbea9902feb/lgGpio.c)
queues changes for active PWM. Its
[`lgPthTx` worker](https://raw.githubusercontent.com/joan2937/lg/v0.2.2/lgPthTx.c)
consumes them at cycle start and keeps advancing its cycle schedule even at
100% duty. Native instead waits on a condition at duty endpoints and rebases
its cycle start on recovery; ordinary pulses still finish their cached cycle.
These mechanisms are consistent with the marker observations, not proof that
the distro binary was built from that upstream source. The installed wrapper
reports 0.2.2.0 and binary hashes are retained, but distro build provenance is not.

Using marker rises, the physical identity is
`hold = marker gap + recovery-marker→fall − high-marker→rise`.
In the first 50-Hz trial, original r1 gives
120.09466 + 14.92134 − 13.61697 = 121.39903 ms; native r1 gives
120.08957 + 1.51501 − 6.91542 = 114.68916 ms.
The observed hold difference is thus accounted for without aligning Pi clocks
or treating the first recovery fall as exact internal adoption latency.

Two further native-only captures exercise simultaneous GPIO18/channel 0 and
GPIO23/channel 1 PWM, independent endpoints, reciprocal 50/500-Hz frequency
changes, release/restart of GPIO18, release of GPIO23 while GPIO18 continues,
and final low cleanup. The frozen plan SHA256 is
`462b3e808076e13c01b7553ff919b2f3f3333256b557b898091086ac0b068b68`.
Thirteen phases have 3.3 seconds of fixed dwell plus three 0.1-second cleanup
settles. Both scheduler options stay disabled; variable frequency is enabled.

Both helpers and collectors exit 0. All 49 caller events succeed and all 13
phase API readbacks match the declared sequence. The three output generations
privately own only their pins, use distinct concurrent FDs 4/6, and reuse FD 4
only after the first GPIO18 request is released. Each settles low, reads
inactive through its owned request, and releases independently. Continuing
sibling request identity and API settings remain unchanged across shutdown.
These are receipt facts, not electrical generation labels or aligned phases.

Both recordings contain 482 GPIO18 edges and 2020 GPIO23 edges, with every
complete high, low and adjacent-rise interval retained. Unique GPIO18 low gaps
of 468.07482/468.11342 ms contain 234 complete GPIO23 highs and 233 periods each.
Their sibling periods span 1999.17–2000.94 µs / 1998.59–2001.47 µs.
GPIO18 resumes an ordinary 50-Hz train; after GPIO23's final fall, GPIO18
continues with ordinary then approximately 10-ms half-duty highs. Both channels
start and end low and contain no sampled sub-µs interior lows.

One r1 GPIO18 high, pair 143, is 1126.97 µs: +126.955 µs relative to its
1000.015-µs half-500 target. It remains visible and breaks the diagnostic
frequency-swap train into fragments. The revised analysis explicitly marks
the full swap extent ambiguous; it does not widen the frozen ±10% identity
bands or merge through that pulse. Initial reports and their exact analyzer
snapshot are retained alongside revised reports. Neither report is a timing
or parity acceptance decision; guarded physical windows can cover only part
of a command phase, and Pi/Saleae clocks remain unaligned.

The read-only postflight at 20:42:54 UTC confirms all 90 recorded PIDs absent,
both pins unclaimed/output-low, unchanged boot/configuration and fan provider,
48.5°C and firmware flags 0. A live consumer-library check is next. Production
and Blinka remain unchanged; these finite native-only functional recordings
do not establish matched performance parity or an analog failsafe.

Independent reconstruction agrees with every raw edge and complete interval
count. Loading only the two saved SALs and re-exporting their channels produces
four byte-identical raw files, without live acquisition or GPIO activity.
All 82 hardware-free helper/collector/analyzer cases pass. The exclusive archive
`hardware-evaluation/2026-10-07/native-pi5-dual-lifecycle-evaluation.tar.gz`
is 935,831 bytes, SHA256
`89dc8dc8eadab4c75e75e92198c174df9c8b50717b1e894a0efcb80e9b957fb9`.
Fresh safe extraction byte-matches 38 explicit targets / 59 regular files and
reproduces all four initial/revised reports with their corresponding analyzers.
It includes exact executed helpers, source manifests, pre/postflight receipts,
raw channels/SALs, tests, independent audit and preserved native binary/source
provenance. Selected third-party hashes are not complete third-party build
provenance. Earlier archives remain unchanged.

### Native consumer-library idle check

Two native-only, passive-probe recordings use genuine
`adafruit-circuitpython-motor` 3.5.0 `Servo` and `DCMotor` classes with unwrapped
public native `PWMOut` objects. A temporary in-memory `pwmio` export provides
the consumer import; it is restored afterward. This is not an installed
Blinka/`pwmio` integration test, and no actual servo, motor or driver is attached.
Both native scheduler options remain off; production and Blinka are unchanged.

The pre-capture plan SHA256 is
`97bb31a21eee3d2ed33241a5a8ebd92f5b10f56a5081cfad4f7fdb6227eaf0d2`.
Fifteen phases have 3.45 seconds of dwell plus three 0.1-second cleanup settles.
GPIO18 first uses a fresh 50-Hz Servo for angles 0/90/180/None, then releases.
Fresh GPIO18/23 outputs form a 1000-Hz DCMotor for throttles
0/+0.5/+1/−0.5/−1/None. Zero intentionally requests both-high brake, not coast.
Actual Servo duties 3276/4914/6553 have native C-rounded highs
999.771/1499.657/1999.847 µs; motor-half duty32767 has high 499.992 µs.
These quantized targets, not ideal 1000/1500/2000-µs widths, normalize errors.

Both helpers/collectors exit 0; all 41 caller events, ten consumer actions and
15 phase API start/end readbacks succeed. The requested 90-degree getter is
89.97253585596583 because of duty quantization, not an electrical angle reading.
Receipts identify Servo GPIO18 generation 1, motor GPIO18 generation 2 and motor
GPIO23 generation 1, independent owned-low/read/release, and unchanged live sibling
identity. FD 4 is reused only after Servo release; concurrent motor FDs 4/6 are distinct.
Receipt identity is not an electrical generation label or aligned phase clock.

Each capture retains 826 GPIO18 edges/413 complete highs/412 adjacent-rise
intervals and 706 GPIO23 edges/353 highs/352 intervals, including every boundary,
low and anomaly. No sampled sub-µs high or interior low is found. Frozen identity
rules use ±10% width and period bands, at least five pulses, long highs >100 ms,
joint brake overlap at least 100 ms, unique order and sibling-low throughout the
whole isolated run. No central-window substitute, trimming or widened band is used.

Both recordings have uniquely ordered Servo-width trains of 21/20/20 pulses,
then joint both-high brake, a GPIO18-only 350-pulse motor-half train and full
high, then a GPIO23-only 351-pulse half train and full high. Joint brake overlaps
are 200.14258/200.14363 ms; isolated full highs are 199.34233/199.36737 ms on GPIO18
and 199.27366/199.27396 ms on GPIO23. Both satisfy the frozen strict topology identity
rules without an ambiguity entry; that is identification, not timing acceptance
or proof of complete command-phase extents. Silent final lows do not identify
the exact disable, deinit or release calls.

Repeat1 retains a 1972.77-µs Servo180 high (−27.077 µs) and a 473.90-µs forward-half
high (−26.092 µs); their adjoining intervals remain present. Forward-half periods
span 973.74–1026.82 µs in r1 and 997.48–1002.34 µs in r2. Better r2 extrema do not
erase the r1 observations. In both raw records, the first GPIO23 reverse-half
rise follows the GPIO18 full-high fall by 150 ns (15 nominal samples). That
sampled separation has uncalibrated GPIO-driver/threshold/timebase skew: it is
not calibrated deadtime, a shoot-through-safety result or a latency guarantee.
Pi/Saleae clocks remain unaligned; caller returns are not electrical adoption.

Independent raw/SAL reconstruction agrees on the finite physical topology and
interval counts; offline re-export of both saved SALs gives four byte-identical
raw channels. All 87 helper/collector/analyzer hardware-free cases and scoped
lint/format checks pass, verified again before archiving.
The later `oct7-native-consumers-final-report-audit.json` also confirms the frozen
final reports against the independent reconstruction; the earlier audit remains
historically unchanged. The read-only postflight at 21:00:14 UTC confirms all
92 recorded PIDs absent, both pins unclaimed/output-low, unchanged
boot/configuration and fan provider, 48.5°C and firmware flags 0. Normal watchdogs
still cannot bound native hangs, SIGKILL or faults.

Recovery archive
`hardware-evaluation/2026-10-07/native-pi5-consumer-evaluation.tar.gz`:
542,853 bytes, SHA256
`79beb6afcf66c05c2bdb2dd76728760f252b44bb6535f5f3c29b1834baa02231`.
Fresh safe extraction byte-matches all 44 explicit top-level targets / 65 regular
files; offline replay reproduces both reports' JSON data exactly. The checkpoint
preserves both SAL/raw recordings, receipts, the frozen plan/manifests, exact
helper/collector/analyzer sources and fake tests, independent
audits, pre/postflight and native binary/source provenance. Three exact genuine
motor Python files are included under `consumer-library-source/adafruit_motor`;
selected-source provenance is not complete third-party build attestation.
See the dated recovery README for offline replay. This native-only functional check does not establish
matched performance parity, default-backend readiness, general consumer/actuator
compatibility or an analog failsafe. Earlier evidence remains unchanged.

### Native consumer-library under bounded CPU load

Two further native-only passive-probe recordings retain the unchanged genuine
motor 3.5.0 Servo/DCMotor helper, temporary virtual `pwmio` export, collector,
analyzer and strict whole-run sibling-low identity rules above. No installed
Blinka or actual actuator compatibility is established. The separate load plan
is frozen before capture, SHA256
`0a216d5da16a496315fbc0ea446bcb797e32c23b49ac37bc038683c89e93cf20`.
The narrow `capture_native_pwm_consumers_loaded.py` coordinator validates the
persisted launch before calling the frozen collector in-process, then checks
actual typed consumer SSH exit 0 and load SSH exit 0. It does not invent a
collector-process return code or treat launch as proof of workload coverage.

Each recording has 826 GPIO18 / 706 GPIO23 edges, all 41 successful caller
events, ten consumer actions, 15 matching phase readbacks and three fresh private
owners with independent low/read/release. The unique ordered physical topology
remains identifiable with no ambiguity entries; every edge, high, low, period,
boundary and anomaly is retained. Identity bands are not timing acceptance.

| Ordinary width target | Maximum absolute target-normalized high error, r1 / r2 (µs) |
| --- | --- |
| Servo angle0, 999.771 µs | 3.029 / 6.551 |
| Servo angle90, 1499.657 µs | 1.137 / 0.747 |
| Servo angle180, 1999.847 µs | 5.697 / 1.667 |
| Motor forward-half, 499.992 µs | 3.132 / 1.122 |
| Motor reverse-half, 499.992 µs | 8.228 / 6.818 |

Both actual workers bracket the entire helper and every one of its 15 phases
in each run. Worker durations are 10.000034376/10.000238265 seconds in r1 and
10.000078803/10.000147767 seconds in r2; helper durations are
3.825028484/3.821722282 seconds. Start/end bracketing margins span
1.01769–1.03913 / 5.13588–5.16669 seconds. These Pi-clock receipts prove overlap,
not CPU saturation or alignment to electrical timestamps. The earlier idle
27.077/26.092-µs errors and the separate 330.018-µs loaded native frequency event
remain unresolved, separate evidence; better finite samples are not guarantees.

All 105 combined hardware-free cases pass, including 18 new coordinator cases;
scoped lint and coordinator/state format checks are clean.
Independent raw and worker reconstruction agrees with the checked final report
facts; all four saved-SAL re-exports are byte-identical. Descriptive bins,
low-summary boundary bases and additional statistics differ between methods;
the preserved final audit checks common raw arrays, shared statistics and frozen
boundary-inclusive sibling conditions without trimming. Preserved nonempty
`remote.stderr` includes local gRPC fork-child diagnostics (host PIDs 363948/364626,
not the distinct Pi helper PIDs); stderr is not erased or described as empty.
The read-only postflight at 21:27:47 UTC confirms all 100 recorded PIDs absent,
both pins unclaimed/output-low, 47.4°C / flags 0 and unchanged sources, boot/config
and fan. Production and both disabled scheduler options remain unchanged.

Recovery archive
`hardware-evaluation/2026-10-07/native-pi5-consumer-loaded-evaluation.tar.gz`:
618,073 bytes, SHA256
`a9fa9ecbfc185934a1a6dafd15132bbaa296c5a83ca9e8bfcedb5434ff52332e`.
Fresh safe extraction byte-matches all 66 explicit top-level targets / 87 regular
files; both waveform and both worker-overlap reports' JSON data replay exactly.
Exact sources, frozen plans/manifests, both captures, load receipts and independent
audits are preserved, including the three genuine motor Python sources and ARM64
native provenance. This is native-only functional-under-load evidence,
not matched lgpio parity, electrical latency, calibrated deadtime, actuator
qualification or an analog failsafe. Earlier archives remain unchanged.

### Paired original-lgpio and native consumer-library idle recordings

Four fresh passive-probe recordings run original → native, then native →
original on the same Pi 5 GPIO18/ch0 and GPIO23/ch1, at 100 MSa/s with no glitch
filter. The pre-capture plan SHA256 is
`a4bf9e03fd8fd7d95f2dff9118108f046999272e63d95f7cc78d87caa3f80c7c`.
The genuine motor 3.5.0 Servo/DCMotor calls and fifteen-phase dwell protocol
are unchanged. Original Pin/PWMOut source and distro lgpio 0.2.2 are used without
changing percent rounding or setters; scoped library hooks enforce/record
private ownership. Native production, independent-worker mode and both disabled
scheduler opt-ins are unchanged. No PIO, header PWM provider, priority, affinity,
governor, fan or boot configuration is changed.

Original duty 4914 at 50 Hz submits 7%, nominally 1400 µs; the draft preserves
the u16 fraction, C-rounded to 1499.657 µs. Original Servo0/180 targets are
1000/2000 µs versus native 999.771/1999.847 µs; motor-half targets are
500 versus 499.992 µs. Duty/readback quantization is distinct from jitter.
This is a temporary in-memory `pwmio` export, not an installed Blinka test or
actual actuator qualification.

| Descriptive complete pulse set | Original maximum absolute target error, r1 / r2 (µs) | Native maximum absolute target error, r1 / r2 (µs) |
| --- | --- | --- |
| Servo angle0 | 10.210 / 34.710 | 3.169 / 4.399 |
| Servo angle90, different backend nominal widths | 0.740 / 1.180 | 1.397 / 1.617 |
| Servo angle180 | 1.210 / 37.000 | 1.117 / 0.897 |
| Motor forward-half | 8.960 / 1.620 | 2.318 / 2.222 |
| Motor reverse-half, including original anomalies | 74.890 / 1.070 | 6.928 / 7.538 |

These descriptive extrema use every complete pulse in the independent raw
layout, not just qualified diagnostic fragments. Original reverse r1 retains
425.110/551.170-µs highs; reverse periods span 924.450–1077.000 µs. Better repeat2
does not erase them. Earlier native 27.077/26.092-µs consumer idle errors and the
separate 330.018-µs loaded frequency-update event likewise remain unresolved.
No baseline-derived quantitative acceptance thresholds or overall parity
verdict are established by these four finite idle observations.

Original recordings retain 822/704 GPIO18/23 edges, 411/352 complete highs,
20/20/20 Servo pulses and 349/350 forward/reverse half pulses each. Native
recordings retain 826/706 edges, 413/353 highs, 21/20/20 Servo pulses and 350/351
motor pulses each. Counts are raw facts, not proof of omitted command cycles:
receipt, host and Saleae clocks remain unaligned. Every low, adjacent rise,
boundary and short/anomalous fragment is retained. No sampled sub-µs high or
interior low is present in either backend.

Both native records support the frozen whole-run ordered topology without
ambiguity entries. Both original records withhold strict isolated full-extent
association: GPIO23's first reverse rise precedes GPIO18's full-high fall by
0.640/0.630 µs, a sampled both-high overlap outside the intentional brake.
Native observations instead have 1.150/0.140-µs both-low gaps. These uncalibrated
digital timestamps are not deadtime, electrical adoption latency or a motor
driver safety qualification. The original r1 report retains its later candidate
and all earlier fragments as ambiguity; it does not substitute that candidate
for the complete reverse extent.

Identification method differences remain explicit. The independent target-
normalized ±10% bins split original r1 reverse pulses into 20/1 anomaly/3/1
anomaly/325. The frozen original analyzer uses symmetric `math.isclose` relative
tolerance 0.10, which includes 551.170 µs in the 500-µs bin; its blocks are 20/329,
with 425.110 µs unmatched. Both retain identical raw widths and withhold complete
isolated topology. Neither diagnostic convention is a timing pass threshold.

All four actual helper SSH exits and local collection commands exit 0. Original
receipts retain 78 nested completion-order events versus native 41 caller events;
each has ten consumer actions, fifteen phase readbacks and three distinct
output generations with independent privately owned low/read/release. Original
public `deinit()` changes flags only: separate lab cancellation, low write,
settled low/not-busy readback, line free and private chip close provide cleanup.
Do not credit that cleanup to original public deinit. Native deinit performs its
own low/release operation. Nonempty stderr containing local gRPC fork-child
diagnostics is preserved, distinct from the Pi helper PIDs.

The independent audit was frozen before report generation. All eight saved-SAL
raw re-exports are byte-identical; all 248 combined hardware-free cases and
scoped lint/format checks pass. Read-only postflight at 22:05:55 UTC confirms 104
recorded PIDs absent, both pins unclaimed/output-low, 47.95°C, firmware flags 0,
matching selected sources and unchanged boot/configuration/fan. Production and
earlier archives remain unchanged; loaded paired comparison and the remaining
validation gates are still required.

The separate final-report audit finds zero mismatches in checked raw arrays,
common statistics, receipt/source facts and conservative topology verdicts;
the tolerance/fragment method difference above is preserved explicitly.
Recovery archive
`hardware-evaluation/2026-10-07/pi5-consumer-paired-evaluation.tar.gz`:
1,133,753 bytes, SHA256
`39937f59947c6560a73e2e86d4509b39932b3d7a5c878d316f5cfb7ff98e5c1f`.
Fresh safe extraction byte-matches all 69 explicit top-level targets / 111 regular
files. Isolated replay reproduces both original and both native report facts;
only the verified absolute original plan location is relocated during comparison.
All other hashes, raw arrays and receipt/report facts must match. Exact sources,
tests, plans/manifests, SAL/raw channels, actual stderr, pre/postflight, selected
native/consumer provenance, independent audits and their method scripts are
preserved. See the dated recovery README; earlier checkpoints stay immutable.

### Paired consumer-library recordings under bounded CPU load

Four further passive-probe recordings use original → native, then native →
original, with the same genuine motor 3.5.0 protocol, selected sources, backend
nominals and GPIO18/ch0 + GPIO23/ch1 wiring as the idle pairing above. The new
pre-capture plan SHA256 is
`1cedb74c5e1ff8531fe7b34d3e8da3aa37643ebc28a1341562db9468a512694b`.
Each run starts two privately owned, independently expiring ten-second workers
performing `sum(range(10000))`. Independently reconstructed actual worker
intervals bracket the entire helper and all fifteen phases through final
readbacks; launcher receipts alone are not this proof. This is bounded load,
not demonstrated CPU saturation or electrical-clock alignment. Production,
both disabled scheduler opt-ins, PIO exclusion and system configuration remain
unchanged.

| Descriptive complete pulse set | Original maximum absolute target error, r1 / r2 (µs) | Native maximum absolute target error, r1 / r2 (µs) |
| --- | --- | --- |
| Servo angle0 | 36.830 / 1.840 | 3.139 / 4.641 |
| Servo angle90, different backend nominal widths | 2.930 / 27.330 | 4.367 / 3.417 |
| Servo angle180 | 68.400 / 47.370 | 4.193 / 2.183 |
| Motor forward-half | 41.790 / 44.180 | 0.832 / 1.102 |
| Motor reverse-half | 38.200 / 44.700 | 8.268 / 7.868 |

These extrema retain every complete high in the independent descriptive raw
groups, not only the analyzer's isolated candidates. Original r1 includes
963.170/1031.360-µs Servo0 highs and a 1931.600-µs Servo180 high; r2 includes
1372.670-µs Servo90 and 2047.370-µs Servo180 highs. Motor forward widths span
458.210–521.240 / 497.210–544.180 µs; reverse widths span
498.620–538.200 / 482.680–544.700 µs. Full highs, lows, adjacent rises and all
boundaries are preserved. The frozen symmetric `math.isclose` identity band
accepts these ordinary width/period groups; supplementary target-normalized
±10% membership agrees in this batch. Neither diagnostic band establishes
quantitative parity. Earlier native consumer and frequency-update outliers
remain unresolved; these better finite loaded samples do not erase them.

Original r1/r2 retain 822/822 GPIO18 edges and 704/706 GPIO23 edges, twenty pulses
per Servo group, and 349 forward / 350 or 351 reverse-half pulses. Native retains
826/706 edges in both runs, 21/20/20 Servo and 350/351 motor-half pulses. Different
counts are not proof of missed command cycles with these unaligned timebases.
Both original full extents have a 0.610-µs sampled peer-high direction boundary;
both reports withhold complete isolated ordered topology and retain three
ambiguity entries. Native full extents support the frozen ordered topology,
with 4.170/7.250-µs both-low handoff gaps. These digital observations are not
calibrated deadtime, application latency or motor-driver safety qualification.

All four actual consumer/load SSH exits are 0, both workers per run exit 0 and
are reaped, and all ownership/protocol/cleanup checks pass. The original's
privately owned lab cancellation/low/read/free/close remains distinct from its
public flags-only deinit. Minimum whole-helper start/end worker margins are
1.100663/4.979766, 1.062002/5.116619, 0.986209/5.192253 and
1.013173/5.067257 seconds in capture order. Helper durations are
3.919416/3.821196/3.821286/3.919596 seconds; these are whole lab protocols,
including cleanup and receipt work, not comparative setter latency.

The initial independent audit/notes were frozen before report generation.
All eight saved-SAL raw-channel exports are byte-identical; 2,156 independent
receipt/source/ownership checks pass. Nonempty local gRPC fork-child stderr
diagnostics remain preserved and distinct from Pi helper PIDs; load stderr is
empty in each run. Read-only postflight at 22:31:38 UTC confirms all 120 recorded
PIDs absent, both pins unclaimed/output-low, matching selected sources and
unchanged boot/configuration/provider identity. Temperature rises from 46.85°C
to 52.35°C with firmware flags 0. The separate cooling fan PWM3 duty changes
from 0 to enabled 12225 ns at unchanged 41566-ns period; unused PWM0–2 remain
0 ns. This is consistent with automatic cooling, not proof of its cause or a
claim that fan duty stayed unchanged. Installed Blinka, actual actuators and
the other validation gates remain untested by this temporary `pwmio` fixture.

The separate final comparison finds zero mismatches in 1,218 main waveform/
scope checks plus 293 receipt checks. Waveform reports do not contain worker
overlap evidence; the independent raw-worker reconstructions and actual load
receipts remain the separate proof. All 476 combined hardware-free cases,
scoped lint/format checks and warning-free documentation build pass.

Recovery archive
`hardware-evaluation/2026-10-07/pi5-consumer-loaded-paired-evaluation.tar.gz`:
1,431,905 bytes, SHA256
`a9feb3694b18cbbef6c95e6bc05f69e061d551f4662fd8c3002f274a66305c23`.
Fresh safe extraction byte-matches 103 explicit top-level targets / 149 regular
files. Isolated replay reproduces both original and both native waveform
reports and all four worker-overlap reports, with only the verified absolute
original plan location relocated. Exact frozen sources/tests, plans/manifests,
SAL/raw channels, load/stdout/stderr/coordination, state chain, independent
audits and ten independent method/check files are preserved. Earlier archives
and production source remain unchanged; this is paired functional-under-load
evidence, not overall quantitative parity or migration readiness.

### Real installed Blinka consumer integration on Pi 5

Two idle passive-probe recordings now exercise installed `board` and `pwmio`,
genuine `board.D18`/`board.D23` Pin objects and motor 3.5.0 Servo/DCMotor,
without a virtual `pwmio` module. This closes that narrow integration gap, not
the timing/parity or general-library validation gates. The private Python
3.13.5 environment uses a test-only Blinka wheel
`9.0.5.dev74+pwmeval.beb49bf`, from source commit
`beb49bf8ea9305dacbd14b08525f234eda563c02`, with only the existing integration
patch changing `src/pwmio.py` among the original source files. It is not a
published Blinka version or a production/default-backend switch.

The PWM wheel is freshly built on ARM64 from `0e1c7cd`; production source is
byte-unchanged from `d5debaf`. Its extension SHA256 is
`86e3c5f580c0c2599f29e12c0846189543726a73544cbe93a84a7b45cbb8b214`,
not the earlier build's binary hash. The exact 23 runtime wheels, seven selected
distribution versions and 72 selected helper/runtime source hashes are retained.
Selected installed distribution files byte-match their wheel members; this is
not whole-system attestation. The patched source tar retains 646 extra
AppleDouble metadata files (501 original versus 1,147 patched regular files);
the built Blinka wheel has 417 entries and no AppleDouble files. Archive file
sets are therefore not described as identical.

The first guarded import-only probe failed because the harness expected
`RASPBERRY_PI_5B`/`BCM2712`. PlatformDetect 3.89.1 actually reports
`RASPBERRY_PI_5`/`BCM2XXX`, with both Raspberry Pi predicates true. Correcting
those two harness expectations makes the probe pass; both outcomes and the
pre-correction helper are preserved. Neither probe requests or writes GPIOs.
The installed Pi 5 NeoPixel dependency satisfies Blinka's availability check,
but no NeoPixel/PIO module is loaded or exercised. This does not establish
coexistence with active NeoPixels or Piomatter. Both scheduler opt-ins remain
disabled, and no PIO, kernel header PWM, priority, affinity, governor, fan or
boot configuration is changed.

The pre-capture plan SHA256 is
`04869dae6b202202fc2c2b6bfdaa1dbaa7bcaf5a2f8a946ee65d81073a1c6161`.
GPIO18/ch0 and GPIO23/ch1 are recorded at 100 MSa/s without glitch filtering.
Both actual local collection commands and helper SSH commands exit 0, with
15 phase readbacks, ten consumer actions, 41 caller events and three distinct
private output generations. Native public PWMOut is used unwrapped with the
real Pin objects. Scoped import instrumentation refuses GPIO claims/writes,
restores its hooks, and closes only its owned lgpio import handle after native
output cleanup; that close is lab instrumentation, not a claim about Blinka's
automatic global-handle cleanup. Each private native output is low/read/released
independently, including the surviving sibling.

Each recording retains 826/706 edges, initial/final low levels, 21/20/20 Servo
pulses and 350/351 forward/reverse-half pulses. Every complete high, low, adjacent
rise, boundary and diagnostic fragment remains in the reports and independent
audit. The full reverse region in repeat 2 includes the anomalous pulse below;
it is not limited to the eligible width fragments.

| Complete descriptive pulse set | Maximum absolute native target error, r1 / r2 (µs) |
| --- | --- |
| Servo angle0, 999.771 µs | 3.279 / 3.009 |
| Servo angle90, 1499.657 µs | 1.807 / 2.647 |
| Servo angle180, 1999.847 µs | 4.957 / 0.757 |
| Motor forward-half, 499.992 µs | 1.022 / 1.292 |
| Motor reverse-half, all 351 highs | 7.228 / 191.132 |

Repeat 1 supports the frozen ordered joint topology without ambiguity entries.
Repeat 2 does **not**: GPIO23 reverse pair 259 is 308.860 µs high, versus the
499.992-µs target, with adjacent rise intervals 1195.990/805.740 µs. The reverse
region spans 308.860–507.220 µs and splits into 258 eligible pulses, the retained
short pulse, then 92 eligible pulses. The report preserves two reverse candidates
in one ambiguity entry and withholds complete joint topology. Both saved-SAL
channel re-exports byte-match all four original raw exports, so the short pulse
is also present in the saved recording. Diagnostic identity bands are not timing
acceptance criteria.

No direction-boundary overlap is observed. Repeat 1 has a 0.480-µs digital
both-low handoff gap; repeat 2's raw first-rise gap is 0.150 µs, while its selected
topology gap is withheld because the reverse association is nonunique. These
uncalibrated digital observations are not deadtime or actuator-safety evidence.
Source inspection shows that the falling deadline stays anchored to cycle start,
not to completion of the rising write. The anomalous shape is consistent with a
late rise followed by that falling deadline and next-cycle phase recovery; the
preserved illustrative phase model does not measure C deadlines or distinguish
wake/preemption, ioctl/driver and electrical delay. No production fix or delay
cause is established by this sample alone. Earlier consumer and frequency-update
outliers remain unresolved rather than being superseded by quieter recordings.

All 60 selected package tests pass in the fresh installed Pi environment without
GPIO use; this is not the omitted native C/trace tool suite. All 396 combined
hardware-free lab cases pass, with scoped lint/format checks clean. Independent
pre-report reconstruction passes 146 receipt checks; later comparison finds zero
mismatches across 299 raw/report checks, preserving the initial audit bytes.
Nonempty stderr contains retained host-local gRPC fork-child diagnostics, distinct
from Pi helper PIDs 6308/6329; no timing cause is attributed to those messages.
Helper durations 3.968193/3.957496 seconds describe the entire lab protocol, not
setter latency. Temperatures across captures are 47.4–48.5°C, firmware flags 0.

Read-only postflight at 23:26:30 UTC confirms all 122 recorded PIDs absent,
both GPIOs unclaimed/output-low, 47.4°C / flags 0, matching selected sources and
unchanged boot/configuration/provider identity. The separate cooling PWM3 is
retained at 41566-ns period, inverse polarity and duty 0 in pre/post snapshots;
unused PWM0–2 remain 0 ns. No claim about unobserved fan behavior is made.

Recovery archive
`hardware-evaluation/2026-10-07/pi5-installed-blinka-consumer-evaluation.tar.gz`:
6,913,796 bytes, SHA256
`59f3b680d1420faa9a11dbd1925ab24583bec181a4a70b24742404f99bda4748`.
Fresh safe extraction byte-matches all 164 explicit regular files. Isolated
offline replay reproduces both complete report JSON objects exactly, with no
fact or path adjustments. Source archives, actual wheels/build/install logs,
failed/corrected probes, exact methods/tests, plans/manifests, SAL/raw captures,
cleanup/state receipts, independent audits and the source diagnosis are retained.
See the dated README for recovery limitations. Earlier archives remain immutable;
this is installed Pi 5 functional evidence, not overall parity or migration
readiness. Warning-free documentation build also passes.
