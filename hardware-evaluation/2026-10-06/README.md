# October 6, 2026 hardware diagnostic checkpoints

## Enabled, period-settled Pi 5 follow-up

`kernel-pwm-pi5-settled-evaluation.tar.gz` is a separate recovery checkpoint.
Extract into a fresh empty directory, not over earlier snapshots. It contains
six short GPIO18/channel0 captures (direct, frequency, shutdown/reopen, and
one repeat each), unfiltered 100-MSa/s SAL/binary exports, the unchanged strict
analyses including both frequency rejections, exact helper/capture/analyzer
sources and tests, and pre/postflight records. No production code changed.

Archive size: 253,487 bytes. SHA256:
`cfb6c906f4e9672ab44e317867ba76f7776a2f0ecec6509fdcb090b4589414a9`.
All 26 top-level targets (56 regular files) were byte-compared after extraction.
Direct and lifecycle passed twice; frequency changes preserved complete pulses
but remained strictly rejected for deliberate quiet gaps and extended hold time.
No captured high dips or partial pulses occurred. Finite digital observations
do not establish analog quality, atomic updates, latency guarantees or readiness
to replace Blinka. The 61 new GPIO-free settled tests and selected lint passed.
See `docs/draft-results.md` for measured timings, limitations and remaining work.
All helper PIDs were absent, test exports released, and pins low after testing.
Overlays remain bound until a controlled reboot; never hot-remove/unbind them.

## Fixed 50-Hz half-duty Pi 5 follow-up

`kernel-pwm-pi5-half50-evaluation.tar.gz` is a separate recovery checkpoint
for the two `half50-direct-v1` captures. Extract into a fresh empty directory.
It preserves unfiltered 100-MSa/s SAL/binary exports, original analyses,
five exact helper dependencies, capture/analyzer tools and GPIO-free tests,
and pre/postflight records. All 28 top-level targets (38 regular files) were
byte-compared after extraction. Archive size: 102,901 bytes. SHA256:
`e2033169ae3ae3d4187739de39cbd71ef8d686123afce69060a0314c56802425`.

Both captures passed: 20 complete approximately 10-ms outgoing pulses,
one continuous approximately 300-ms high, and 20 complete recovery pulses.
No partial pulses or captured high dips. These finite digital observations
retain the response-delay and analog/timebase limitations in draft-results.
The 34 new tests and selected lint passed. Production and providers unchanged;
normal-zero/disable/export-release cleanup and thermal gates were verified.

## Coordinated two-worker CPU-load Pi 5 follow-up

`kernel-pwm-pi5-loaded-evaluation.tar.gz` is a separate immutable recovery
checkpoint for `oct6-pi5-settled-direct-loaded-r2` and
`oct6-pi5-half50-loaded-r2`. It preserves both original unfiltered 100-MSa/s
SAL/binary captures, strict analyses, independent worker-overlap reports,
exclusive coordination/receipt sidecars, exact sources/tests and pre/postflight.
It also retains the initial CPU-only attempt, explicitly **not PWM waveform
data**, and the exclusive pre-handshake recorder/test snapshots. No guarded
files are included. Extract into a fresh empty directory, not over earlier data.

Archive size: 151,928 bytes. SHA256:
`4e63afe5f416ad5a04ed79fa406960b2268a218886125f7c343f386bcbeb0b10`.
Fresh extraction byte-compared all 51 top-level targets (63 regular files)
with the unchanged originals.

Both strict captures passed: direct has 526 edges and high holds
300.54664/300.55339/641.35334 ms; half50 has 82 edges and a 300.58296-ms
high. All ordinary pulses are complete and have the same saved width/period
ranges as idle, with no captured high dips. Deliberate transition quiet gaps
remain; these are not command-to-edge latency measurements. Actual worker
receipts bracket every phase and the entire GPIO helper; launcher/helper,
recorder and capture each recorded exit0. Each of two workers ran approximately
ten seconds and was reaped. This shows concurrent CPU work, not full four-core
saturation, statistical bounds or baseline parity.

All recorded PIDs were absent in loaded postflight, no exports remained and
both pins were low. Temperatures were 51.80→52.90°C direct and
50.15→50.70°C half50, firmware flags zero. Normal-zero/20-ms cached cleanup,
disable and fresh-export release succeeded. Coordinator/recorder/helper hashes
match retained sidecars and exact frozen sources. Informational gRPC fork/poll
stderr is retained. The providers/fan/boot configuration and production backend
were unchanged; providers stay bound until reboot. See draft-results for exact
timings, source hashes and finite digital/clock-alignment limitations.

## Self-SIGTERM from inverse-zero high

`kernel-pwm-pi5-sigterm-evaluation.tar.gz` is a new exclusive recovery
checkpoint containing only `oct6-pi5-sigterm-high` and `-r2`, their native SAL,
all raw edges, original analyses/acquisition receipts and stdout/stderr, exact
frozen helper/capture/analyzer dependencies/tests, and dedicated postflight.
The actual per-run remote before-snapshots provide available preflight evidence;
there is no separate SIGTERM preflight file. No earlier evidence or guarded
files are included. Extract into another fresh empty directory.

Archive size: 102,400 bytes. SHA256:
`4368db377b5349942f156e566bd012d0e4c3151067da4960edefb9bb71905f87`.
All 26 top-level targets (38 regular files) byte-match fresh extraction.

Both strict diagnostic captures passed with exactly two raw edges: initial
lows 2.50791225/2.91475851 s, continuous highs 300.65130/300.96428 ms,
then persistent lows 1.80386013/1.73093449 s. No captured high dip or later
reassertion occurred. Self-PID SIGTERM15 raised the expected SafetyAbort;
helper exit0 means expected-abort checks passed, **not ordinary completion**.
Reports retain `expected_abort_observed=true`, `completed_normally=false`,
normal-zero/20-ms final cached disable, absent fresh export and no errors.
Independent after-cleanup temperatures were 47.40/46.85°C with flags zero.
Postflight confirms PIDs 4281/4309 absent, both pins low, no test exports,
unchanged boot SHA and only the separate fan consumer owned, at 48.3°C/flags0.
The receipt discloses the failed combined pinctrl read syntax and successful
separate-query exit0 retry. Providers remain bound until reboot.

Executed SIGTERM helper SHA256:
`2db935b3e86c75f12354fc5cfbe2fbeb8fdc016b62dcc93776eff69fafaa7279`.
Capture SHA256:
`3fec63e40a2bb41a6368ab1037524eda24befffe8ae00bdfaf3a87043bf01126`.
Analyzer SHA256:
`aebc8ba6919e5addcb1616f31b5aaae02f6365e60bb057e9e68c7ad7ef2c468b`.
All five reported helper hashes matched the frozen sources, and both original
analyses reproduced independently. These finite, uncalibrated 100-MSa/s
digital observations do not establish signal-to-edge latency, analog quality,
arbitrary-interruption coverage or backend readiness. Baseline parity remains
unestablished; earlier strict frequency rejections are unchanged. Production
and Blinka integration were not changed.

## Single-period plus 1-ms guard Pi 5 characterization

`kernel-pwm-pi5-guarded-evaluation.tar.gz` is a new exclusive recovery
checkpoint for eight unloaded captures (direct, frequency, lifecycle,
half50-direct and one repeat each) plus two short loaded direct/half50
captures. It retains native SAL, every binary edge, original accepted/rejected
analyses, acquisition/stdout/stderr evidence, two independent overlap reports,
twelve outside loaded sidecars, 35 exact source/test dependencies and guarded
pre/postflight. The prior SIGTERM postflight is included only as the initial
inspection referenced by guarded preflight. No earlier capture or archive
changed. Extract into a fresh empty directory, not over earlier checkpoints.

Archive size: 389,120 bytes. SHA256:
`b76925bff876bde8d9232cd40d2d72358cc13327ebb51d394883cc82a2895f4d`.
All 60 top-level targets (122 regular files) byte-match fresh extraction.

The strategy changes only transition waits: one nominal period plus 1 ms
requests 21/3 ms at 50/500 Hz, retaining original writes, cached readbacks,
fresh ownership, conservative cleanup and strict waveform predicates.
Direct/lifecycle/half50 passed twice; frequency remains strictly rejected
twice for its two ordinary quiet-gap boundaries, not high width. Its
944.17310/944.13325-ms high holds now satisfy the unchanged window, while
46.00210/26.00121-ms boundary rising-edge gaps (repeat: 26.00120 ms) match
neither configured period. Those stricter diagnostic rejections are not an
established baseline-parity failure; the passes do not establish parity either.

Both loaded captures passed: direct has 526 edges and highs
300.91965/300.59209/622.43044 ms; half50 has 82 edges and high 300.92641 ms.
Complete ordinary pulses retain the idle ranges, with no captured high dips or
partial pulses. Actual worker receipts bracket every phase and entire helper;
load-helper, recorder and capture exit0, pinned source validation and normal
worker reap were independently checked. Each guarded loaded profile has one
actual capture, despite its fresh `-loaded-r2` name. Two ten-second CPU workers
are moderate concurrent work, not repeated, saturated four-core coverage.

Pi-side command/readback transition durations are shorter (about 21.6 ms
normal 50 Hz → high versus 40.6 ms; about 43 ms active 50→500 Hz versus 81 ms), not
aligned electrical latency or settling guarantees. Physical Logic8/channel0
100 MSa/s has no glitch filter, independent timebase calibration or analog
measurement. Every edge and original rejection remains retained. Maximum
endpoint temperature was 53.45°C with flags zero. Conservative normal-zero/
20-ms/disable/unexport cleanup passed; final exit0 postflight found all sixteen
recorded PIDs absent, both pins low, no test exports, only the separate fan
owned and unchanged boot SHA, at 45.5°C/flags zero. Providers stay bound until
reboot; GPIO18 remains PWM-muxed and GPIO23 reserved.

Guarded helper SHA256:
`142f0afcc8786252ade1a461386715d0d5dbb2f8394c26dcbb40eb34ab635b0b`.
Capture/analyzer SHA256:
`bd41cc2b8bcf68b9ccc303009aaa423f0ec68325d38a910c3ea91ffa4c1d254a` /
`e67450ec606fe0ef7e73050340fc21445da8498d654200ebee40ad8d81336dfa`.
Loaded wrapper SHA256:
`12278b86ee92c6d5c2f2af9e3d9f3017b0b3e44fb12e7aea6595d94a81e45226`.
Exact reported hashes match the frozen sources. The 87 selected guarded
hardware-free cases and 56 loaded-wrapper/coordinator cases passed, with
selected lint. See draft-results for individual observations and limitations.
Baseline parity/readiness remain unestablished; production/Blinka are unchanged.

## Earlier October 6 checkpoints

`diagnostics.tar.gz` contains five new capture directories, native `.sal` files,
digital exports, JSON summaries/edge-correlated analyses, trace CSVs and remote
stdout/stderr, plus the exact capture/analysis harnesses and the source archives
used during setup. Extract into an empty directory; paths and analyzer identity
are bench-specific. Do not execute capture scripts without confirming hardware.
The earlier October 1 snapshot is separate and unchanged.

Archive size: 2,911,563 bytes. SHA256:
`4db6cd581c4bbacfdd13ec19015a1d06b99401dc1f738c09f860b984bfcad676`.
Extraction into a fresh directory was byte-compared against all five original
capture directories and all seven included scripts/source archives.

This is recovery evidence, not an installed package or CI input. `MANIFEST.in`
prunes all of `hardware-evaluation`. The six automated trace tests use fake
ioctls and ordinary pthread timed waits, never GPIO devices.

Captures:

- `oct6-trace-shared-idle`: 3 seconds, no burners, 6607 trace records.
- `oct6-trace-shared-loaded`: 20 seconds, four burners, 43016 records.
- `oct6-trace-per-output-loaded`: 20 seconds, four burners, 44004 records.
- `oct6-untraced-shared-loaded`: 20 seconds, four burners, no instrumentation.
- `oct6-trace-shared-loaded-r2`: 20 seconds, four burners, 43016 records.

All use short-slice opt-in, GPIO18/50 Hz/duty 4915 and GPIO23/500 Hz/duty 32768,
confirmed channel 0/1 wiring and ground, 10 MSa/s, Logic 2 2.4.46. Firmware flags
remained clear and endpoint temperatures stayed within the documented bench
gates. No PIO, RT priority, affinity, governor, or system configuration was changed.
All ended low and pins were released. Instrumentation is not a speed benchmark.
See `docs/draft-results.md` for results, caveats, and remaining acceptance work.

Production source is unchanged from
`d5debaf0e5caafa1fdf5a7619e1ae2e8cd41f1f4`. SHA256s:

| File/build | SHA256 |
| --- | --- |
| `src/native/module.c` | `c536a372630e04156d74c7e0b2ac6b5a644a031e12440c5ebfe304ba36cc820e` |
| `src/native/pwm_engine.c` | `b9fa5840d9fa801625f7d0520fc41f4e9365751d76ee4887fb5856ebee3cd5a1` |
| `src/native/pwm_shared.c` | `1e94596f98511507c21d774aa7c125e0e56014c00880e0173dcfa02d675ed7f3` |
| `tools/native_trace.c` used for captures | `18ca155c17963db4004d876682a91cf8e425173e488008b1d50ce2e1406cb1d1` |
| Normal Pi 5 wheel | `4079cc79443fc1130804cd7e5effeb76e0c03dd8aba6cb8fcbf3eacbbd9a3fce` |
| Traced `_native.cpython-313-aarch64-linux-gnu.so` | `e5031d140a92cc8931a2c9d413a4c6b174c406d2d604d8385a8aa234e6bb1064` |

Pi build: CPython 3.13.5, `aarch64-linux-gnu-gcc`, sysconfig `LDSHARED`, `CFLAGS`
and `CCSHARED` (O2), C11, pthread, `_POSIX_C_SOURCE=200809L`, and the two function
aliases documented in `tools/README.md`. The trace source undefines both aliases
before includes so calls reach the real libc functions. Isolated runtime source:
`/tmp/blinka-pwm-oct6.F3SDcm/trace-source/src`; normal installation remains in
`/tmp/blinka-pwm-oct6.F3SDcm/venv`. Reboots may remove these temporary directories.

Recorder path is exclusive/private/close-on-exec. Each trace footer reports zero
dropped, initialization, file-I/O and clock errors. Both channels' external edge
counts exactly match successful level-changing trace writes. The analyzer uses
Linux ETIMEDOUT=110 even when run on macOS. Existing `trace-analysis.json` files
are retained; `trace-analysis-with-rises.json` adds preceding-wait context for the
first shared and per-output captures. Long gaps between recorded operations
cannot be treated as pure CPU time. The recorder perturbs scheduling itself.

The first source archive predates the recorder hardening; only the second
(`oct6-trace-v2-source.tar.gz`) supplied the trace C used for these captures.
The final tests and tool README are tracked in the repository; source archives
are setup evidence, not substitutes for that final source.

## Approved private kernel trace follow-up

`kernel-diagnostics.tar.gz` is a second, independent incremental archive. Extract
it into another empty directory: it contains newer versions of some harness
files than `diagnostics.tar.gz`. The first archive is unchanged.

Archive size: 1,742,006 bytes. SHA256:
`e0f1280a15817c6eb054a116e1dc38147af912c0dd29ad26ff2b94026c1bf217`.
Extraction was byte-compared with the complete original capture directory and
all eight included capture/analysis/test scripts.

It contains `oct6-kernel-per-output-loaded`, including native CSV, kernel trace,
event formats/filters and loss counters, clock markers, Saleae waveform/digital
exports, both offline analyses, command output, and read-only postflight checks.
The captured helper SHA256 is
`71ac51b981f1384e8a244f5e8d8eae883fe5355a34d171d9792935f9854506ee`.
Production and native-recorder source/build hashes remain those listed above.

The user approved one 20-second per-output run on the same GPIO18/23 bench,
with four bounded burners and short-slice opt-in. PWM ran as `pi`. Existing
passwordless sudo controlled one exclusive private tracefs instance only:
`mono` clock, 8192 KiB per CPU, scheduling filters for the two worker TIDs and
their timer lifecycle events. Callback filtering also includes unrelated
`hrtimer_wakeup` timers, so pointer identities are matched chronologically to
the workers' own starts. No global trace controls or system policy was changed.
Do not execute the privileged helper outside this specifically confirmed bench.
An export failure deliberately retains its stopped buffer for recovery; it
must not be treated as successful cleanup or recursively removed.

The instance was stopped/exported/removed normally, all kernel loss counters
were zero, and the native recorder had 44012 records with zero errors/drops.
The worst GPIO23 wait was 3758.014 µs late, including 3755 µs runnable off-CPU
after wakeup. Its matched timer callback was near its deadline at 1 µs text
resolution. The waveform contains a 6004.4 µs period and two estimated omitted
cycles; acceptable high widths alone do not establish correct delivery.
See `docs/draft-results.md` for attribution limits and other observations.

Endpoint temperatures were 46.85–58.95°C with clear firmware flags; both pins
ended low and were released. Postflight found no trace instances or recorded
test/worker/burner PIDs remaining. The 19 GPIO-free capture/helper tests (plus
12 subtests), analyzer self-tests, lint and warning-strict documentation build
passed. This doubly instrumented run is not a production performance benchmark
or proof about prior captures. Defaults and Blinka integration are unchanged.

## Approved non-PIO kernel PWM evaluation

`kernel-pwm-evaluation.tar.gz` is a third independent incremental archive.
Extract it into another empty directory, not over the earlier checkpoints.
It preserves five Pi 5 capture directories (two rejected endpoint tests,
three ordinary-duty timing runs), postflight output, nine final scripts/tests,
and two pre-format source snapshots. No PIO or production backend change was
made. The Pi 4 was not modified or driven.

Archive size: 481,126 bytes. SHA256:
`81690f99d2f7bcda9a245512979621c5c712f43e2061c1922490fe21a728626c`.
Fresh extraction was byte-compared against every capture/postflight directory,
both source snapshots and all nine direct script/test files (17 top-level targets).

The exact remotely executed helper SHA256 is
`ed8e60cd529a9cfdd231994627ef3c1fc1aefb7abf3673c66cd44e38745f119d`,
present in both source snapshots. `oct6-kernel-pwm-v1-source.tar.gz` preserves
the original 10-MS capture/analyzer files and tests; its SHA256 is
`8b2920f126501eef6fdb5263714056a4598a6f12d2b1b72a1655f4389c97bd8c`.
`oct6-kernel-pwm-v2-source.tar.gz` preserves higher-rate capture/offline analysis
support and the rejection inspector before final formatting; its SHA256 is
`5fa251969b2fd507d12c49bd6f22098e53d593d6bcb2ac7484ed86a3e9df73dd`.
The direct final helper differs only by import sorting, formatting and comments;
it was not uploaded. The final direct tests passed 95 GPIO-free cases and lint.

Captures:

- `oct6-pi5-kernel-endpoints`: seven 0.2-second holds, 10 MSa/s. GPIO18
  hardware full duty failed: ten transitions, including three digitized dips.
- `oct6-pi5-kernel-endpoints-100msps`: same holds, 100 MSa/s. Forty GPIO18
  transitions include eighteen digitized 10–20 ns dips, one every interior cycle
  in both full-duty holds. GPIO23 has four clean endpoint transitions in both runs.
- `oct6-pi5-kernel-idle`: 3 seconds without CPU burners.
- `oct6-pi5-kernel-loaded` and `oct6-pi5-kernel-loaded-r2`: 20 seconds each,
  four bounded burners. GPIO18 is hardware 50 Hz/duty 4915; GPIO23 is kernel
  software 500 Hz/duty 32768. Ordinary-duty captures use 10 MSa/s.

The higher-rate capture process initially retained its previously imported
10-MS-only analyzer. Offline replay with the updated analyzer rejected the real
GPIO18 extra edges. Both `endpoint-rejection.json` reports keep these failures
explicit; neither endpoint run has a passing `analysis.json`. Three ordinary-duty
analyses preserve the 50-ms-end-trim convention. See `docs/draft-results.md` for
the larger untrimmed startup deviations, measurement limits and exact driver/
datasheet explanation. Digitized notch widths are not analog-width proof, and
the analyzer timebase was not calibrated.

Both PWM channels were commanded low, disabled and unexported after every run;
all recorded burners exited. Firmware limiting flags stayed zero. The fan
controller/consumer and boot configuration were left intact. **The runtime
`pwm` and `pwm-gpio` overlays remain loaded until reboot**: GPIO18 remains muxed
to PWM and GPIO23 remains kernel-reserved. Do not hot-remove/unbind/unload these
providers; exact-version teardown defects were found during source review.
This is experimental evidence, not permission to run captures on another setup
or replace Blinka's current backend. All hardware archives remain excluded from
source distributions.

## Approved Pi 4 kernel PWM evaluation

`kernel-pwm-pi4-evaluation.tar.gz` is another independent incremental archive.
Extract into a separate empty directory; earlier captures/source versions
remain unchanged. It contains five Pi 4 capture directories, preflight and
postflight, seventeen direct lab script/test files and two source snapshots.
All twenty-five top-level targets were byte-compared after fresh extraction.

Archive size: 522,137 bytes. SHA256:
`df5a711f5323e1b9c188e9f34c6e993f033d4556fdc3816e348fb843520c4e93`.
Source snapshots:

- `oct6-pi4-kernel-v1-source.tar.gz`: original 10-MS tools, SHA256
  `dc678ac5be83fdeb80d5988e1c248c9cadbc58e55b60fc90879da564f542e85c`.
- `oct6-pi4-kernel-v2-source.tar.gz`: endpoint-only 100-MS support, final
  full-train analysis and combined tests, SHA256
  `b7c047b5eb12171e6a068d61202ce1570c5738aca04fb7aad4fa06c03ce303a1`.

The exact remotely executed core helper SHA256 is
`7cb4ea051e346b38b3276b92e5e0edcd9f24f4ed36f7d4f4eeffa4800f8e2111`;
the Pi 4 discovery wrapper is
`ce9765a79d3e20b63a612248a2566e26ea8b2ddd45c71bbb7a3173e8885dc421`.
Both hashes appear in preflight/postflight and source snapshots. There were no
remote dependency installs or kernel builds. The user enabled the two runtime
overlays and confirmed grounding; subsequent helpers ran as `pi` without sudo.

Captures on Pi 4 Model B Rev 1.4 / kernel `6.18.50+rpt-rpi-v8`:

- `oct6-pi4-kernel-endpoints` and `oct6-pi4-kernel-endpoints-100msps`: seven
  0.2-second logical holds at 10/100 MSa/s. Both pins passed four-transition
  endpoint checks. No RP1-like full-duty notch was detected at matched resolution.
- `oct6-pi4-kernel-idle`: 3 seconds without burners.
- `oct6-pi4-kernel-loaded` and `oct6-pi4-kernel-loaded-r2`: 20 seconds each
  with four bounded CPU burners.

GPIO18/ch2 is BCM hardware 50 Hz/duty 4915; GPIO23/ch3 is kernel software
500 Hz/duty 32768. Ordinary captures use 10 MSa/s, real Logic 8, glitch
filtering disabled. Export headers are v0 with no rate field; SAL metadata
confirms capture configuration. These are sampled, uncalibrated digital results.

Every saved strict `analysis.json` was independently reproduced. The three
ordinary captures also have `full-train-analysis.json`, including final highs
and timestamps of extrema; the inspector wrote only new files and left all
35 original capture files unchanged. The last loaded run's steady-state GPIO23
period range widened to 1993.1–2007.0 µs. Including startup, loaded period
ranges were 1985.3–2014.2 and 1986.5–2014.5 µs; full high ranges were
990.5–1022.8 and 988.5–1013.8 µs. Do not present trimmed statistics as
whole-lifecycle bounds. No clock alignment, analog glitch-width proof, causal
attribution or omitted-cycle estimate is established. Pi 4/Pi 5 profiles match,
but CPU/controllers/kernel versions do not; this is not a matched-driver benchmark.

All five runs ended low with successful low/disable/unexport. Recorded burner
PIDs were absent in postflight; firmware flags remained zero and loaded endpoint
temperatures remained below 49°C. Boot-file hash and the unselected audio
controller were left intact. The runtime overlays remain loaded until reboot;
GPIO18 stays PWM-muxed and GPIO23 kernel-reserved. Do not hot-remove/unbind/unload
`pwm-gpio`. Neither PIO nor production source/Blinka integration was changed.

All 282 combined GPIO-free cases passed. Lab lint passed with `RUF007` excluded
for the offline utility's existing consecutive-pair `zip` idiom. Warning-strict
documentation compilation also passed. See `docs/draft-results.md` for thermal
readings, acceptance limits and remaining Pi 5 full-duty work. These archives
are recovery evidence and remain excluded from installed source distributions.

## Approved Pi 5 inverse-zero constant-high experiment

`kernel-pwm-pi5-inverse-evaluation.tar.gz` is another independent incremental
archive. Extract into a separate empty directory; it does not replace any
earlier baseline/failure evidence. It contains two complete capture directories,
preflight/postflight text, and nine exact lab source/test files, including the
unchanged common helper and binary reader. All thirteen top-level targets
(twenty-three regular files) were byte-compared after fresh extraction.

Archive size: 67,510 bytes. SHA256:
`ce7a9a111796460457f6e370ac3ceb4d6e1115183cd74f63304d1d57294bc002`.
Executed helper SHA256:
`545b0fd16aaee668040f757be0e49e6021492ff5d64e13a94d8166983164fdbf`.
Common helper SHA256:
`7cb4ea051e346b38b3276b92e5e0edcd9f24f4ed36f7d4f4eeffa4800f8e2111`.
The new helpers ran from the fresh private
`/tmp/blinka-pwm-oct6.F3SDcm/inverse-eval` directory, without overwriting earlier
Pi 5 helpers. Only GPIO18 header RP1 PWM0 channel 2 was exported, as `pi`.
No PIO, sudo, boot edits, provider removal or production backend changes occurred.

`oct6-pi5-inverse-endpoints` and `oct6-pi5-inverse-endpoints-r2` each request
nine phase holds totaling 2.4 seconds: normal low, ordinary PWM, low,
inverse-zero high, low, inverse-zero high, low, ordinary PWM, low. Two 0.3-second
high holds are separated by normal-low phases. The normal controls/recovery
are 50 Hz/duty 4915 for 0.4 seconds each. Both native SAL recordings confirm
physical Logic 8 channel 0 only, 100 MSa/s, and disabled glitch filtering.

Both analyses pass and exactly reproduce offline: 84 edges each, twenty pulses
before and after two uninterrupted high holds. The four highs measure
300.57336–300.60780 ms, with no extra captured dips. All ordinary periods are
20000.88–20000.89 µs and highs 1500.02–1500.03 µs, including complete boundary
pulses. This is finite, uncalibrated digital evidence, not analog proof. Direct
high-to-interior PWM was not tested because a low separator precedes recovery.
Pi/Saleae clocks are not aligned and setter latency is not established.

The dedicated owner restores normal-zero, enables/verifies/settles low, then
disables and unexports. Failed low recovery retains the export and reports
failure; inverse-zero must never use the normal-only helper's cleanup directly.
Sysfs readbacks are cached requested state, not physical measurements. Both
waveforms finish low with tails exceeding 0.52 seconds; helpers report no
cleanup errors. Postflight finds both test pins low, no test exports or helper
PIDs, unchanged fan ownership/state and boot hash, and clear thermal flags.
The providers remain loaded until reboot; the pins are not generally unclaimed.

The source/safety review and independent hardware-evidence audit found no
remaining diagnostic blockers or discrepancies. All 384 combined GPIO-free lab
cases and new-tool lint passed. See `docs/draft-results.md` for detailed thermal
readings, exact-source links, limitations and remaining wrapper/lifecycle tests.

## Pi 5 direct/frequency/lifecycle transition checkpoint

`kernel-pwm-pi5-state-evaluation.tar.gz` is a separate incremental archive:
three complete capture directories, pre/postflight text, and twelve exact source/
test files including the frozen dependencies. All seventeen top-level targets
(thirty-two regular files) were byte-compared after extraction to an empty
directory. Earlier endpoint/failure evidence remains unchanged.

Archive size: 143,358 bytes. SHA256:
`ce76a6db12b4e2a5e3b569f083cb4a2596f89b14670bf53d01f27481aed1d906`.
Executed state helper SHA256:
`9ba7b5ad0893fbc71d508e2f16a91e7f8b5808bc5d749c7c54210ed50186f7f4`.
Frozen inverse/core source hashes remain those listed in the prior section.
The helper ran from fresh private `state-eval` under the existing isolated Pi 5
bench directory; it did not overwrite earlier helpers. Only GPIO18 RP1 PWM0
channel 2 was exported, without sudo, PIO or production/boot changes.

`oct6-pi5-state-direct`, `-frequency`, and `-lifecycle` each have an explicit
**accepted=false** analysis retaining all raw transitions. Their 532/486/446
edges include three/two/two shortened outgoing ordinary pulses at setter
boundaries. Continuous high holds remain clean, including ~0.6/~0.9 s high
frequency-change spans; high→ordinary recovery pulses are complete. Lifecycle
successfully releases and recreates the same channel across two generations,
with a 613.04989-ms physical low interval. The normal-operation strategy disables
before polarity/frequency changes; a source-supported period-settled alternative
is a later experiment, not a rewrite of these rejected results.

All three saved SALs confirm physical Logic 8, channel 0 only, 100 MSa/s, no
glitch filter. Sysfs readbacks are cached requested state; Pi/Saleae clocks are
not aligned and the analyzer timebase is uncalibrated. No sub-microsecond low
run was detected; this is finite digital evidence, not analog proof. The strict
boundary criterion is stronger than CircuitPython's documented frequency API,
which permits an adjustment glitch; rejection alone is not an API violation.

All helpers report successful normal-low cleanup with no errors. Postflight
shows pins low, no test exports/helper PIDs, unchanged fan and boot hash, and
zero firmware flags. Runtime providers remain loaded/reserved until reboot;
never hot-remove/unbind/unload them. The source review fixed the diagnostic
lifecycle signal/reopen bug before hardware. All 481 combined GPIO-free tests,
new-tool lint and independent evidence audit passed. Consult draft-results for
all widths, thermal readings, exact source links and interpretation.

## Original-lgpio Pi 5 clean-boot reference

`kernel-pwm-pi5-lgpio-baseline-evaluation.tar.gz` is a new exclusive checkpoint,
not a replacement for any kernel diagnostic. It preserves six complete
`oct6-pi5-lgpio-baseline-` captures, every raw edge/native SAL and receipt,
six exact current helper/collector/analyzer/test files, two byte-identical
original Blinka files, three required dependencies, three exclusive prior
source/test snapshots and pre/postflight. Extract into a fresh empty directory.
All 22 explicit top-level targets (59 regular files) byte-match fresh extraction;
no links/special files are included. Archive size: 225,280 bytes. SHA256:
`3e57dc44227a3046e0dbc2ce412326a726db5cb26bedd10d7fc13f0d36f895ab`.
The 14-MB pre-reboot runtime backup remains separately preserved locally/remotely,
not duplicated in this lean checkpoint. Earlier archives/evidence are unchanged.

The original files come from Blinka commit
`beb49bf8ea9305dacbd14b08525f234eda563c02`; distro `lgpio.py_0.2.2.0`
and `/usr/bin/python3` were used. A controlled reboot removed runtime providers,
with no hot-unbinding and unchanged kernel `6.12.75+rpt-rpi-2712`/boot SHA.
Only freshly claimed GPIO18 on the discovered RP1 gpiochip was driven.
This is before-versus-after clean boot, not a same-boot/load/calibrated benchmark.

The first authoritative report is `direct/analysis-rounding-corrected.json`
under the full capture prefix. Its original `analysis.json` and
`*_rounding_v1.py` sources/tests retain the erroneous 8%/1600-µs nominal math.
The unchanged original formula yields 4915=7.499809262226291%, rounded to
**7%/1400 µs**, not the kernel's approximately 1500.02-µs logical-4915 pulse.
All six authoritative reports reproduce independently. All collections have
exit0/safe receipt success, but waveform acceptance and parity remain `null`.

| Original profile | Edges first / repeat | First continuous highs (ms) | Repeat continuous highs (ms) |
| --- | --- | --- | --- |
| `direct` | 516 / 512 | 301.29867, 300.89860, 601.21023 | 301.88139, 301.47738, 602.29147 |
| `frequency` | 482 / 464 | 901.22782 | 901.09150 |
| `half50-direct` | 80 / 80 | 310.34298 | 310.32369 |

Descriptive ±2% width bins retain 23 unmatched highs across direct/frequency
runs, without trimming: 1022.25–1024.51, 1037.73–1047.77 and
1428.19–1447.03 µs. Each half50 trace has 20 outgoing/19 recovery pulses;
no sub-microsecond interior low run is recorded. These bins are not acceptance
rules. SAL confirms physical Logic8/channel0, unfiltered 100 MSa/s;
uncalibrated finite threshold evidence cannot prove analog or sub-sample quality.

Original instrumented setters take 5.891–25.153 µs, without added waits.
Matched logical-phase timings show the guarded prototype's intentional waits
would block callers substantially longer (for example approximately 21.6 ms
versus 19.229/24.259 µs entering high at 50 Hz). The kernel helper combines
frequency/duty updates, while the original calls frequency then duty setters;
these are not identical API paths. Pi/Saleae clocks are unaligned and no physical
command-to-edge latency is established. This strategy is not shown on-par;
compare the actual native draft API with matching setter order before expanding
the prototype or considering migration. Production remains unchanged.

API readbacks are software state. Separately recorded bench cleanup cancels PWM,
drives/settles low for 100 ms, verifies GPIO read0/`tx_busy`0, frees GPIO18 and
closes its private chip; these are not the original deinit's behavior.
All six claims released without signals/errors, at 47.40–50.15°C/flags zero;
no load workers ran. The 14-s normal watchdog excludes cleanup/SIGKILL/native
hangs. Exit0 postflight finds all six PIDs absent, GPIO18 released output-low,
GPIO23 unclaimed input, fan-only PWM ownership and unchanged boot SHA at
47.7°C/flags zero. Failed initial preflight/fan-query diagnostics and corrected
retries remain documented; release does not restore input pinmux.

Executed helper SHA256:
`8018a1766c711a9babe8d98c4f1f77412f23876c4e7fdc96bd012caaf3808b2f`.
Corrected analyzer SHA256:
`f099d76048b018bd976515fd1e65fd86563cfd5b619f50553815d74085918995`.
All four helper source hashes match exact retained files. The 82 current fake
cases and scoped lint pass. See `docs/draft-results.md` for every count,
caller timing comparison and limitations. **Baseline parity and default-backend
readiness remain unestablished.**
