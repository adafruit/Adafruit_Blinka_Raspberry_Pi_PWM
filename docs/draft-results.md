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
