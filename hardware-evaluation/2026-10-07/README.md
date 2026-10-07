# October 7 default-native Pi 5 comparison

## Frequency/direct and matched loaded checkpoint

`native-pi5-updates-loaded-evaluation.tar.gz` preserves four new idle native
captures and twelve matched two-worker loaded captures (native/original,
frequency/direct/half50, two repeats). Six unchanged original idle references
are included. Source and Blinka remain unchanged; both native scheduler options
stay off. See `docs/draft-results.md` for the complete interpretation.

Archive: 877,956 bytes; SHA256:
`61d4ecde5e58a26da15759f257ffc2bd5d869b3bf5b0be04e69e74629a70bafa`.
Fresh safe extraction byte-matches all 127 explicit top-level targets, 273
regular files. From that extraction, all sixteen new analysis reports, five
paired comparisons and twelve load-overlap receipts reproduce exactly.

The archive includes SAL/raw exports, actual exits/stdout/stderr, exact executed
helpers/collectors/analyzers and their fake tests/dependencies, immutable plans
and manifests, original source snapshots, the previously preserved native
binary/source provenance, independent loaded audit and read-only postflight.
The first original direct report's historical rounding error and corrected
report are both retained. No older evidence is overwritten.

Native timing is generally encouraging but not an on-par qualification:
frequency-loaded repeat2 retains a 1829.98-µs high against its 1499.962-µs
target (+330.018 µs) and shortened adjoining low. Native direct repeat1 retains
a 978-µs half500 pulse. Endpoint hold durations/counts consistently differ from
the original, and caller-return timing is not electrical application latency.
Every anomaly and boundary remains in the evidence. All 24 actual workers
bracket every phase and the whole PWM helper; this proves overlap, not CPU
saturation. No sampled sub-µs lows were found in these finite recordings.
The postflight confirms all 52 recorded PIDs absent and private pins released.

Extract into a separate empty directory. Example offline replay with Saleae's
Python package installed (new output names avoid overwriting evidence):

```console
python analyze_native_pwm_updates.py oct7-pi5-native-updates-frequency-loaded-r1 oct7-pi5-native-updates-frequency-loaded-r2 --baseline oct7-pi5-lgpio-updates-frequency-loaded-r1 oct7-pi5-lgpio-updates-frequency-loaded-r2 --output-name replay.json --comparison-output replay-frequency-loaded.json
```

`checkpoint_native_updates.py` documents the exact inspected targets and replay
checks. Its archive-creation path is specific to the original sibling layout;
do not rerun it against this already existing archive. Fake tests also require
matching package source, recoverable from the included production-source tar.
Do not run hardware helpers without a fresh bench/ownership/source check.
GPIO23 was not driven in this checkpoint; electrical marker tests are later work.

## Loaded frequency follow-up checkpoint

The separate `native-pi5-frequency-followup-evaluation.tar.gz` adds four matched
loaded frequency pairs, retaining the prior evidence as a separate report group.
Size: 1,489,337 bytes; SHA256:
`540722861b7e3aa50a95d29b892ac7db66ca8d880de1373e765175ee54b2463a`.
Its 186 explicit targets / 384 regular files safely extract and byte-match;
all 24 new capture reports, five paired comparisons and the distribution report
reproduce. Exact prior matrix dependencies are included, not altered.

New native maxima are 6.542 µs (50Hz) and 29.065 µs (500Hz), original maxima
3.920/125.260 µs. The earlier native 330.018-µs event remains separate and its
cause unresolved; non-recurrence here is not a tail/parity guarantee. All sixteen
new workers bracket every phase and helper. The independent audit and read-only
postflight are retained alongside raw data, plans, exact sources and fake tests.
No GPIO23 marker captures are included yet.

Offline replay uses `python analyze_native_frequency_loaded_followup.py --output replay-followup.json`
from a fresh extraction. Do not rerun the checkpoint creator against existing
archives. Review bench ownership and paths before any hardware helper execution.

## Electrical marker checkpoint

`pi5-electrical-marker-evaluation.tar.gz` preserves four matched idle GPIO18 PWM /
GPIO23 marker captures. Size 458,154 bytes; SHA256:
`753ad8992ffb5c1839f6e96193ffe9e9ba6701acb9e2c70cde334fc5aa21098e`.
All 31 targets / 66 regular files byte-match a fresh safe extraction and reproduce
all four analysis reports. Sources/tests, raw channels, source manifests,
independent audit, pre/postflight and native binary/source provenance are included.

Thirty-two sequence marker pulses pair strictly to setters; native has one extra
separate cleanup pulse. Twenty-one ordinary→high starts are identifiable from
low-at-marker cases; three original 500-Hz already-high cases remain ambiguous.
Recovery first falls include resumed pulse width, not exact adoption delay.
Both backends can wait part of a cycle before entering sustained-high output;
different hold widths alone do not establish a slow-native endpoint regression.
Same-acquisition intervals are uncalibrated finite threshold facts, not precise
internal adoption latency or overall parity. Read the dated results before use.

Offline replay after fresh extraction (requires Saleae's Python package):

```console
python analyze_gpio_pwm_marker.py oct7-pi5-lgpio-marker-updates-r1 oct7-pi5-native-marker-updates-r1 oct7-pi5-native-marker-updates-r2 oct7-pi5-lgpio-marker-updates-r2 --output-name replay.json
```

Selected third-party hashes/versions are retained, not all third-party binaries.
The ARM64 native extension is evidence, not a macOS runtime. Hardware helpers
drive both confirmed pins and require new bench/source/ownership verification.

## Native dual-output checkpoint

`native-pi5-dual-lifecycle-evaluation.tar.gz` preserves two native-only GPIO18/23
functional recordings: independent endpoints, reciprocal frequency changes,
separate shutdown and GPIO18 restart. It is 935,831 bytes; SHA256:
`89dc8dc8eadab4c75e75e92198c174df9c8b50717b1e894a0efcb80e9b957fb9`.
All 38 explicit targets / 59 regular files byte-match a fresh safe extraction,
and all four initial/revised reports reproduce with their exact analyzers.

GPIO18's roughly 468-ms low gaps contain 234 continuing GPIO23 pulses each;
GPIO18 later continues after GPIO23 stops. Private per-generation ownership,
separate low/read/release and sibling API identity are receipt evidence, not
electrical phase or generation labels. An r1 1126.97-µs high remains retained
with explicit full-swap-extent ambiguity. This is functional evidence, not
matched performance parity. All edges and complete intervals remain available.

Independent reconstruction agrees; offline re-export of both saved SALs gives
four byte-identical raw channels. All 82 hardware-free cases pass. Both pins
release low; cooling, boot/configuration and production remain unchanged.
The archive includes ARM64 native binary/source provenance, not a macOS runtime
or complete third-party build attestation. Read the dated results before use.

Offline replay from a fresh extraction (requires Saleae's Python package):

```console
python analyze_native_pwm_dual.py oct7-pi5-native-dual-lifecycle-r1 oct7-pi5-native-dual-lifecycle-r2 --output-name replay.json
```

Do not rerun checkpoint creators against existing archives. Hardware helpers
drive both confirmed pins and require fresh source/bench/ownership checks.

## Native consumer-library checkpoint

`native-pi5-consumer-evaluation.tar.gz` preserves two native-only idle GPIO18/23
passive-probe recordings using genuine motor 3.5.0 Servo/DCMotor classes and
unwrapped native public PWMOut objects. The temporary in-memory `pwmio` export
does not establish installed Blinka compatibility; no actual actuator is attached.
Archive: 542,853 bytes; SHA256
`79beb6afcf66c05c2bdb2dd76728760f252b44bb6535f5f3c29b1834baa02231`.
Fresh safe extraction byte-matches all 44 explicit top-level targets / 65 regular
files; offline replay reproduces both final reports' JSON data exactly.

The frozen 15-phase sequence uses Servo angles 0/90/180/None on GPIO18 at 50 Hz,
releases it, then fresh motor GPIO18/23 at 1000 Hz for throttles
0/+0.5/+1/−0.5/−1/None. Zero means both-high
brake. Actual u16/C-rounded targets, strict unique ordered topology and whole-run
sibling-low checks are preserved, with no post-capture central guard or band
adjustment. Both collections exit 0 and retain all 826 GPIO18 / 706 GPIO23 edges each.
The r1 −27.077-µs Servo180 and −26.092-µs motor-half errors are not discarded.
The sampled 150-ns cross-channel separation is uncalibrated, not deadtime or an
actuator-safety result. Neither clocks nor consumer calls align to the waveform.

Included evidence covers SAL/raw exports, acquisition/remote receipts, exact
executed helpers/collectors/analyzer and dependencies, fake tests, frozen plan
and 18-source manifests, independent audits, pre/postflight and native binary/source
provenance. Three exact genuine motor Python sources are included under
`consumer-library-source/adafruit_motor`. The final-report audit confirms the
frozen reports against the independent reconstruction; historical audits stay
unchanged. All 87 hardware-free cases and scoped lint/format checks pass, verified
again before archiving. This is finite native-only functional evidence, not matched performance parity,
electrical application latency, analog failsafe or production readiness.

Extract into a separate empty directory. Offline replay with matching dependencies
and Saleae's Python package installed uses exclusive new outputs:

```console
python analyze_native_pwm_consumers.py oct7-pi5-native-consumers-r1 oct7-pi5-native-consumers-r2 --output-name replay.json
```

The ARM64 extension is provenance, not a macOS runtime. Selected third-party
hashes are not complete build attestation. Do not rerun checkpoint creators
against existing archives or execute hardware helpers without fresh
bench/source/ownership checks. Production, Blinka and earlier archives remain
unchanged; passive probes do not qualify a motor driver or physical actuator.

## Native consumer-library loaded checkpoint

`native-pi5-consumer-loaded-evaluation.tar.gz` preserves two further native-only
passive consumer captures, each with two self-expiring ten-second CPU workers.
Archive: 618,073 bytes; SHA256
`a9fa9ecbfc185934a1a6dafd15132bbaa296c5a83ca9e8bfcedb5434ff52332e`.
Fresh safe extraction byte-matches all 66 explicit top-level targets / 87 regular
files; both waveform and both worker-overlap reports' JSON data replay exactly.

The existing genuine motor 3.5.0 helper, collector, analyzer and strict whole-run
identity plan remain unchanged. A narrow in-process coordinator checks the
persisted launch, actual typed consumer/load SSH exits 0 and real worker
bracketing of the entire helper and every phase. The raw-audit label
`consumer_coordinator_exit` means `coordination.consumer_remote_returncode`, the
actual consumer SSH exit, not an in-process collector or local CLI status.
Each recording retains 826 GPIO18 / 706 GPIO23 edges and identifiable ordered
topology without ambiguity entries.
Every interval and nonempty stderr remains preserved, including host-local gRPC
fork-child diagnostics distinct from Pi helper PIDs. This is not an installed
Blinka/actuator test, CPU-saturation proof or matched lgpio comparison.

The archive includes exact source dependencies, load/helper/coordination
receipts, frozen plans/manifests, SAL/raw channels, pre/postflight and selected
consumer/native provenance, including three exact genuine motor Python sources
and the ARM64 native binary. All 105 combined hardware-free cases pass, with
scoped lint and coordinator/state format checks clean. The independent raw audit
is preserved before final-report comparison; the later
`oct7-native-consumers-loaded-final-report-audit.json` finds no checked mismatches.
All four saved-SAL re-exports are byte-identical. Different descriptive bins,
low-summary boundary bases and additional statistics remain documented; the
comparison checks common arrays/statistics and frozen boundary-inclusive sibling
conditions. Earlier idle and loaded outliers stay separate, unresolved evidence.

From a fresh extraction, offline waveform replay uses new output names:

```console
python analyze_native_pwm_consumers.py oct7-pi5-native-consumers-loaded-r1 oct7-pi5-native-consumers-loaded-r2 --output-name replay.json
```

The coordinator's `audit()` function rechecks saved worker/consumer receipts
offline; its CLI performs hardware collection and must not be used for replay.
Read the dated results and confirm fresh bench/source/ownership before any live
helper use. Pi/Saleae clocks, threshold/driver skew and timebase remain
uncalibrated; no electrical-latency, deadtime, parity or actuator guarantee follows.

## Paired consumer-library idle checkpoint

`pi5-consumer-paired-evaluation.tar.gz` preserves four fresh passive-probe Pi 5
consumer recordings: original → native, then native → original. Archive:
1,133,753 bytes; SHA256
`39937f59947c6560a73e2e86d4509b39932b3d7a5c878d316f5cfb7ff98e5c1f`.
All 69 explicit top-level targets / 111 regular files byte-match fresh safe
extraction. Isolated replay reproduces all four report facts, normalizing only
the verified relocated absolute original plan path; every other fact/hash matches.

Original duty 4914 submits 7% at 50 Hz (1400 µs) versus the native u16 target
1499.657 µs. Both original recordings retain a sampled 0.640/0.630-µs both-high
direction handoff overlap and withhold whole-run isolated topology. Original r1
retains 425.110/551.170-µs reverse highs and every fragment. Native handoffs have
1.150/0.140-µs both-low gaps and identifiable complete ordered topology. These
are uncalibrated digital facts, not deadtime or motor-safety qualification.

The initial independent audit/notes remain immutable; all eight saved-SAL exports
are byte-identical. The later final-report audit finds zero checked numeric/raw/
receipt/scope mismatches. Target-centered ±10% versus symmetric `math.isclose`
relative tolerance 0.10 produces different diagnostic reverse fragments for
551.170 µs: independent 20/1 anomaly/3/1 anomaly/325 versus reported 20/329.
Both preserve the same raw data and withhold complete original isolated topology;
no later quiet candidate replaces the whole run. See `docs/draft-results.md`.

The archive includes all four captures, source/test dependencies, frozen plans,
21-source original and 18-source native manifests, actual collection/cleanup and
state receipts, independent/final audits, and selected native/consumer provenance.
`audit-source/` preserves four independent method scripts plus their initial and
final receipt-check JSON; their original paths/output behavior need review before
reuse. Original public deinit remains flags-only; explicit privately owned lab
cancel/low/read/free/close is separate. All 248 combined hardware-free cases and
scoped lint/format pass. Postflight records 104 PIDs absent, both pins free/output-
low, 47.95°C / flags 0 and unchanged boot/configuration/fan. Nonempty local gRPC
fork-child diagnostics remain preserved, distinct from Pi helper PIDs.

From a fresh extraction with matching Python dependencies, offline report replay
uses exclusive new filenames (CLI defaults differ):

```console
python analyze_lgpio_pwm_consumers.py oct7-pi5-lgpio-consumers-r1 oct7-pi5-lgpio-consumers-r2 --plan oct7-lgpio-consumers-plan.json --output replay.json
python analyze_native_pwm_consumers.py oct7-pi5-native-consumers-paired-r1 oct7-pi5-native-consumers-paired-r2 --output-name replay.json
```

Do not rerun capture, state or checkpoint CLIs as offline replay. Capture helpers
drive physical GPIO; state CLIs contact the original hosts; creators require fresh
outputs and preserve original bench paths. Earlier native outliers remain
unresolved; this idle functional pairing is not overall quantitative parity,
installed Blinka/actuator compatibility or production-backend readiness.

## Earlier half50 idle checkpoint

`native-pi5-half50-evaluation.tar.gz` preserves two idle native public-API
GPIO18 recordings against the two unchanged original-lgpio `half50-direct`
references. Both scheduler opt-ins remain disabled; no PIO or kernel PWM is
used. Production source is unchanged. See `docs/draft-results.md` for the
interpretation and remaining migration gates.

Archive: 167,851 bytes; SHA256:
`5d47826cb38be70f1c27412b66ebf19c9c1c6d918339440f518353404f18a7dc`.

Twenty-two explicit top-level targets contain 51 regular files. Fresh, safe
extraction byte-matched every file, then exactly reproduced both native
reports, both original reports, and the paired comparison. Contents include:

- Four complete recording directories, including SAL/raw edges, acquisition,
  receipts, nonempty informational stderr, manifests and original reports.
- Six new recording/analysis source/test files and their exact dependencies.
- `oct7-native-half50-plan.json`, frozen before capture; its limits are not
  adjusted after the native count flags.
- `oct7-native-half50-manifest.json` and the paired comparison JSON.
- `oct7-native-half50-runtime`: pre/postflight summaries, the exact installed
  ARM64 extension and a Git source snapshot from `80d5f69`. The previously
  built extension's SHA256 is
  `4268007f3e96ef16b869c6cf98478cbd470f855b764c8854d07d8d242f2a38bb`.

Both native traces have 84 edges, 21 initial ordinary highs, one continuous-high
run and 20 recovery highs. The provisional initial-count and total-edge limits
are flagged; all other declared physical/caller envelopes are met. No edge or
boundary anomaly is filtered or discarded. This finite idle comparison is not
an overall parity/default-migration verdict or synchronized electrical-latency
measurement. Do not attribute the kernel prototype's millisecond waits to the
native package.

Extract into a separate empty directory, preserving the archive unchanged.
With the Saleae automation Python package installed, offline replay uses:

```console
python analyze_native_pwm_half50.py oct7-pi5-native-half50-direct oct7-pi5-native-half50-direct-r2 --output-name replay.json --comparison-output replay-comparison.json
```

Replay outputs are exclusive new files. The fake tests also require the
matching repository Python source in the original sibling layout; the included
source snapshot can recover it. The ARM64 extension is evidence, not a macOS
runtime component. Do not execute capture helpers without a newly confirmed
bench, source manifest and GPIO ownership checks. Their saved `/tmp` paths may
not survive reboot. Never remove live PWM providers or overlays; the separate
fan is out of scope. This whole directory remains excluded from distributions.
