# Hardware evaluation recovery snapshot

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

Snapshot SHA256:
`d052d0bbed06d6c0361cbb39b043814ef5c5fa4e633a698244c3487544a26ab0`.
The archive is approximately 77 MB and is explicitly excluded from source
distributions by `MANIFEST.in`.
