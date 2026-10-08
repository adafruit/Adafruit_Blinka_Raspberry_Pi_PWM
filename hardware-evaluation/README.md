# Hardware evaluation recovery snapshot

October 8 configured BCM/RP1 production-package support and ten focused Pi 4/Pi 5
GPIO18 hardware captures are preserved in
`2026-10-08/configured-hardware-package-evaluation.tar.gz`. This is an additional
hardware path, not a rewrite of the older software/prototype evidence. All steady
groups pass; Pi 4 HIGH frequency transitions retain LOW gaps and ambiguous
aggregate mapping. Read the final section of `docs/draft-results.md` and the
archive's byte-verification receipt before using it as qualification evidence.

The subsequent October 8 [focused Blinka integration](2026-10-08/gpiod-integration.md)
passes installed-wheel GPIO/pull/ownership checks on Pi 4 and Pi 5, with raw
passive-probe traces and LOW/free postflight. It preserves a rejected no-claim
alias-discovery preparation separately. Blinka PR1122 is pushed with passing
CI but remains draft pending a published PWM dependency and compatibility
decisions. Production PWM is unchanged; no new timing sweep or parity claim.

The October 8 [Pi 4 installed-Blinka checkpoint](2026-10-08/README.md) completes
the final four fixed-50-Hz original/native recordings and ends this physical
PWM test sweep. It preserves every interval, both instrumentation failures and
their source versions, and the final idle-state inspection. Its encouraging
idle result does not erase the earlier Pi 5 timing outliers or establish overall
default-backend parity. Production PWM source remains unchanged.

The October 7 [night stopping point](2026-10-07/RESUME.md) preserves the installed
Pi 5 checkpoint and unfinished Pi 4 preparation. No new Pi 4 GPIO capture was
started; only isolated environment bootstrap completed. Its separate recovery
archive is preparation evidence, not a timing result or ready acquisition tool.

The additional October 7 native frequency/direct and matched loaded matrix is
preserved in `2026-10-07/native-pi5-updates-loaded-evaluation.tar.gz`, with four
new idle captures and twelve loaded captures. Its directory README records
byte/replay verification and recovery instructions. Most normalized timing is
encouraging, but a retained 330-µs loaded high-pulse error and endpoint response
differences still need investigation. No on-par/default-migration verdict or
production change is implied.

`2026-10-07/native-pi5-frequency-followup-evaluation.tar.gz` adds four further
matched loaded pairs and independently audited error distributions. The prior
330-µs native event remains separate and unresolved; better follow-up samples
are not a tail/parity guarantee. Recovery and replay details are in the dated README.

`2026-10-07/pi5-electrical-marker-evaluation.tar.gz` adds four two-channel
setter-bracketing recordings. It retains every edge and explicitly ambiguous
cases; physical marker-relative intervals are not exact adoption latency or
an overall on-par verdict. Both pins release low and the fan remains unchanged.

`2026-10-07/native-pi5-dual-lifecycle-evaluation.tar.gz` adds two simultaneous
GPIO18/23 functional recordings with independent release/restart and sibling
continuity. The retained wide pulse and partial-swap ambiguity are not hidden;
this is not a matched performance-parity checkpoint.

`2026-10-07/native-pi5-consumer-evaluation.tar.gz` adds two native-only idle
passive-probe recordings using genuine motor 3.5.0 Servo/DCMotor classes through
a temporary virtual `pwmio` export. Frozen ordered, whole-run sibling-low
association preserves every edge and the r1 −27.077/−26.092-µs pulse errors.
This does not prove installed Blinka, actual actuator operation, calibrated
deadtime, electrical latency or performance parity. Recovery details are in
the dated README; production remains unchanged.

`2026-10-07/native-pi5-consumer-loaded-evaluation.tar.gz` adds two native-only
passive-consumer recordings under two self-expiring ten-second CPU workers.
Actual worker receipts bracket the entire helper and all 15 phases; overlap is
not CPU saturation. Frozen strict topology rules and all raw intervals remain
unchanged. Better finite widths do not erase the earlier idle errors or separate
330-µs event, nor establish parity, actuator safety, latency or deadtime.

The October 7 default-native 50-Hz update comparison is preserved separately in
`2026-10-07/native-pi5-half50-evaluation.tar.gz`; see its directory README.
It includes two new native captures, the two unchanged original-lgpio
references, all raw edges, fixed comparison limits, exact recording/analysis
sources and tests, and the native binary/source provenance. Native widths and
caller returns meet the narrow observed envelopes, while both traces retain
the flagged extra outgoing pulse/total-edge count. Neither those flags nor the
other passing comparisons establish overall backend parity. Blinka and the
production package are unchanged.

The incremental October 6 diagnostics are in `2026-10-06/diagnostics.tar.gz`
`2026-10-06/kernel-diagnostics.tar.gz`, and
`2026-10-06/kernel-pwm-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi4-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-inverse-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-state-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-settled-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-half50-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-loaded-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-sigterm-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-guarded-evaluation.tar.gz`, and
`2026-10-06/kernel-pwm-pi5-lgpio-baseline-evaluation.tar.gz`; see that directory's README
for provenance, raw captures, and interpretation. Extract each incremental
archive into a separate empty directory to preserve each script version.

The loaded checkpoint preserves two accepted, narrowly scoped diagnostic
waveforms with independently verified two-worker overlap and actual exit0
coordination, plus an earlier load-only failed handoff that is **not waveform
data**. The SIGTERM checkpoint separately preserves two accepted expected-abort
diagnostics, not ordinary helper completion. Original predicates, earlier
rejections and archives remain unchanged. Neither checkpoint establishes
baseline parity, analog/latency guarantees or production-backend readiness;
no guarded files are included in these earlier recovery archives.

The separate guarded checkpoint preserves eight original idle outcomes
(direct/lifecycle/half50 pass twice; frequency stays rejected twice for quiet
gaps) and two short, accepted two-worker loaded captures. It changes only the
experimental wait policy, retains every edge and original waveform rule, and
does not establish aligned electrical latency, baseline parity or readiness.
Earlier checkpoints remain immutable.

The original-lgpio checkpoint separately preserves six clean-boot reference
captures, all raw edges and anomalies, corrected integer-percent rounding,
the first erroneous report and exact source snapshots. Collection success is
not a pulse/parity verdict. The guarded prototype's deliberate waits would
block callers longer than the original setters; differing setter paths and
unaligned clocks prevent an electrical-latency or on-par claim. Production
remains unchanged; compare the actual native draft API with matching setter
order before considering migration.

`2026-10-01/measurements.tar.gz` preserves the local `pwm-measurements` workspace
at the October 1, 2026 checkpoint, excluding generated Python bytecode caches.
It includes the capture/analysis scripts, recording-only harness tests, timing
investigation notes, results JSON, Saleae `.sal` captures, exported digital edge
data, diagnostic CSV recordings, remote test stdout/stderr, and source archives
used for the isolated test builds. Earlier thermally confounded runs are retained
as evidence, not accepted timing results; consult `docs/draft-results.md`.

This is a recovery artifact, not an installed package component or CI input.
Extract it into an empty directory to recover the original measurement layout.
The scripts preserve the original bench paths and analyzer configuration; review
and adapt those before use. Running capture scripts deliberately drives GPIOs
and may start bounded CPU load. Do not run them against an unconfirmed setup.

The production source, tests, and result interpretation are tracked normally in
this repository. The shared scheduler and short-slice options remain off by
default, PIO is excluded, and Blinka has not been switched to this backend.

The separate October 7 paired consumer checkpoint preserves four fresh idle
original-lgpio/native Servo/DCMotor recordings with alternating order, all raw
boundaries and anomalies, private ownership/cleanup receipts and independent
audits. Original percent quantization and sampled handoff overlaps remain distinct
from the draft's observations; no quantitative parity or actuator verdict follows.
Its recovery archive also retains the independent method scripts and reproduces
all four report facts after safe byte-checked extraction. See the dated README
and `docs/draft-results.md`; earlier checkpoints remain immutable.

The separate paired loaded-consumer checkpoint adds four alternating-order
original-lgpio/native recordings with independently verified two-worker overlap
through every consumer phase/readback. It retains complete extrema/boundaries,
the automatic-cooling-compatible fan duty change, raw/load/cleanup/state evidence
and independent method sources. Safe byte-checked recovery reproduces four
waveform and four workload-overlap reports. These finite functional results are
not overall parity or installed Blinka/actuator qualification; see the dated
README for the archive and replay details.

The installed Blinka Pi 5 checkpoint separately adds two real installed
`board`/`pwmio` Servo/DCMotor recordings, rather than the temporary export used
above. It preserves the private test-only dispatch build, exact ARM64/runtime
wheels and logs, source inventory, failed/corrected import probes and complete
raw/cleanup/state/audit evidence. One recording retains a 308.860-µs reverse
pulse against a 499.992-µs target and withholds complete waveform topology;
integration success is not a timing/parity verdict. Safe byte-checked extraction
reproduces both report JSON objects exactly. See the dated README and
`docs/draft-results.md`; production/default dispatch and earlier archives remain
unchanged.

Snapshot SHA256:
`d052d0bbed06d6c0361cbb39b043814ef5c5fa4e633a698244c3487544a26ab0`.
The archive is approximately 77 MB and is explicitly excluded from source
distributions by `MANIFEST.in`.
