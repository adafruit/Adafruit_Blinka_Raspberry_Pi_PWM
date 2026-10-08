# October 8: focused Blinka gpiod/PWM integration

Blinka draft PR1122 now selects gpiod GPIO and this package's native PWM on
Raspberry Pis together. The tested integration is Blinka commit
`f3fdc2c4fd1fdfd558414771b36c933c7a57d30a`. Production PWM source remains
unchanged from `d5debaf`; this is a functional integration checkpoint, not a
new PWM timing sweep or a performance-parity verdict.

## Installed-wheel checks

The pure Blinka evaluation wheel `adafruit_blinka-9.0.5.dev77-py3-none-any.whl`
has SHA256 `19fe8a3c20de1684cf594f78e0b815837a0e34e6c8b196e8ef19f60d1f3e70ab`.
All 418 included Python sources byte-match the checkout. Universal wheel
requirements do not include board-specific gpiod/PWM packages; those are
selected by the runtime platform table. This local wheel version is not a release.

Offline, no-dependency installation into fresh `integration-gpiod-r2/site`
overlays on both existing private benches exits 0. The earlier environments
and distro packages remain unchanged. Both use CPython 3.13.5, PlatformDetect
3.89.1, gpiod 2.5.0 and the previously installed native PWM 0.0.1.dev0 package.
The Pi 4 is ARM64/BCM2711; the Pi 5 is ARM64/RP1. Manifests record exact boot,
configuration, controller, distribution and source identities. This does not
reclassify the previously retained full-environment pip-check failure as clean.

No-claim import checks verify actual `board`, `digitalio` and `pwmio` classes,
integer BCM pin IDs, lazy aliases and installed-source origins. Neither
RPi.GPIO/lgpio nor PIO/NeoPixel code is loaded. The finite helper then exercises
GPIO18 and GPIO23 sequentially: pull UP/read HIGH, DOWN/read LOW, no pull with
explicit disabled-bias metadata, output LOW/HIGH/LOW, release and reclaim.
Floating no-pull voltage is not an acceptance criterion. Simultaneous INPUT
ownership verifies releasing GPIO18 leaves GPIO23 usable. A genuine zero-duty
50-Hz PWM object owns GPIO18, competing DigitalInOut receives EBUSY (errno 16),
then GPIO18 is reclaimable after public PWM deinit. No actuator was connected.

Both actual SSH/helper exits are 0, all public readbacks and ownership checks
pass, and cleanup errors are empty. Each Saleae channel has exactly four edges
and two HIGH runs; all raw intervals, including boundaries, are retained.
Pi 4 uses channels 2/3 and Pi 5 channels 0/1, at 10 MSa/s without filtering.
The approximately 82--86-ms HIGH holds are GPIO observations, not PWM timing
measurements or aligned API-to-electrical latency. Pi and analyzer clocks are
not aligned. The saved SAL files were not replayed/re-exported.

Both postflights show GPIO18/23 LOW and unclaimed, no remaining test helper,
unchanged boot identity and throttle flags 0. Pi 4 temperature is 32.615°C and
Pi 5 is 46.850°C. Pi 4's remote stderr retains local capture-client gRPC/fork
logging; it did not prevent actual SSH/helper completion.

## Pi 3B+ follow-up

The short smoke also passes on a newly provisioned Raspberry Pi 3 Model B Plus
Rev 1.4 (`test-pi3`), with ARM64 userland, CPython 3.13.5 and Linux
6.18.50+rpt-rpi-v8. This is separate from the earlier 32-bit build/API tests.
An isolated private venv installs 16 frozen cached wheels without system-site
packages or distro changes. Actual pip install and `pip check` both exit 0;
547 installed site sources byte-match their wheels. Four relocated pyftdi
utility-script payloads match after the expected pip shebang rewrite.

Genuine Pi 3/BCM283x dispatch and installed origins pass before claiming any
line. GPIO18/23 then pass UP/DOWN/disabled-bias input checks, LOW/HIGH/LOW
public readback, repeated release/reclaim, independent ownership and native
zero-duty 50-Hz PWM/EBUSY handoff. The helper exits 0 with 66 recorded events,
no cleanup errors and empty stderr. The no-pull voltage is not an acceptance
criterion. No analyzer was used, no nonzero-duty PWM was requested, and
this adds no waveform, timing or parity evidence. Final read-only postflight
confirms both pins OUTPUT LOW/unclaimed, no helper, unchanged source/boot/config
identity, 34.862°C and `throttled=0x0`.

The initial wheel verifier exits 1 after successful installation because it
looked for relocated utility scripts under site-packages; no GPIO helper ran
then. Its exact failed method/logs remain separate. Corrected verification
reuses the successful installation without reinstalling. Thirty-two recording
tests and scoped E4/E7/E9/F lint pass; the broader lab Ruff run retains three
intentional broad-catch cleanup warnings and one import-alias style warning.
Measured methods are not reformatted afterward.

## Fixes and retained rejected preparation

Pi-only GPIO regressions cover preserving a commanded HIGH when DigitalInOut
reapplies output/drive mode, clearing previous input bias on output, independent
handles and partial-failure cleanup. Generic drivers on other boards are unchanged.
The first no-claim preparations installed dev76 successfully, then rejected
`gpiochip4 -> gpiochip0` as two controllers. Their actual receipts, stderr,
methods and dev76 wheel remain separate. No GPIO helper or capture ran in those
attempts. Canonical discovery now deduplicates aliases without a chip0 fallback;
genuinely distinct matching controllers still reject. Corrected dev77 checks
do not replace or relabel the earlier failures.

113 focused Blinka tests and 17 recording-only helper tests pass. The broad
Blinka suite has 131 passes and two unchanged settings-test failures, both
reproduced on untouched HEAD. Scoped Black/Pylint, warning-as-error Sphinx and
PR1122's GitHub CI pass. Writable frequency, period and enabled behavior are
covered by adapter tests; electrical frequency is rounded to integer Hz within
the native 1--10,000-Hz configuration range. Higher-frequency compatibility is
still a user decision. The dependency is not published to PyPI, so PR1122 stays
draft. Melissa wants the PWM repository transferred to Adafruit before finishing
PR1122; transfer, project-URL updates and publication remain pending.
The Pi 3B+ smoke adds real BCM283x GPIO coverage; prior Pi 3
32-bit native build tests remain distinct. No new broad matrix,
publication, merge, PIO, boot or permission changes are implied.

## Recovery

`pi-gpiod-blinka-integration.tar.gz` contains 52 regular files, 2,748,949 bytes,
SHA256 `4f0c00640753a47e225449441f43f67264599ed7d669568fe65c251d1f3899fe`.
It preserves both failed preparations and both successful installed imports,
raw captures, complete analyses, postflight receipts, exact methods, frozen
wheels and local verification logs. Every member byte-matches its source;
see `gpiod-integration-archive-verification.json`. No extraction or live replay
was performed. Restore only into a fresh directory; do not execute saved GPIO
commands merely to recover evidence. Private /tmp paths and boot identities
are session-specific. Earlier PWM archives and timing qualifications are unchanged.

The separate Pi 3 checkpoint `pi3-gpiod-blinka-smoke.tar.gz` contains 28 regular
files, 195,986 bytes, SHA256
`66bada18fe8409528eab0c645b2af96dda75b546c7d51531c052a869e0989aff`.
It retains the exact failed/corrected preparation methods, actual installation
and command-completion receipts, full import/hardware reports, postflight,
32-test output, scoped/broad lint outputs and independent saved-receipt audit.
All members byte-match their sources; see `pi3-gpiod-archive-verification.json`.
Sixteen wheel payloads are byte-verified references to the earlier Pi 5
installed-consumer and Pi 4/Pi 5 integration archives, not duplicated here.
No extraction or GPIO replay was performed. Restore only into fresh directories;
the new Pi 3 private paths and boot identity are also session-specific.
