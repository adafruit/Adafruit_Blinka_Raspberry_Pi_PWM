# Hardware evaluation recovery snapshot

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
