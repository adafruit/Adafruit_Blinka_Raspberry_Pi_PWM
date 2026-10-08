# October 7 night stopping point

Stopped at Melissa's request, before any new Pi 4 helper deployment or GPIO
capture. No overnight testing or monitoring is scheduled. Production source is
unchanged from `d5debaf`; neither scheduler opt-in is enabled and no PIO is used.

## Completed and preserved

The installed-Blinka Pi 5 consumer checkpoint was committed and pushed as
`f89e996`. Its archive, raw captures, complete reports, source/install provenance
and replay verification are retained unchanged. Both native consumer runs finish
and release their outputs, but repeat 2 retains a 308.860-µs motor-half pulse
against a 499.992-µs target. That −191.132-µs event and the earlier timing outliers
remain unresolved. This is functional evidence, not overall performance parity
or permission to change Blinka's default backend.

After the requested Pi 4 reboot, read-only inspection records GPIO18/23 as
unclaimed input/pull-down/low, 33.589°C and firmware flags 0. The header/audio
PWM nodes are disabled and no pwmchip is registered. `pi` can access gpiomem and
gpiochip0 through its existing gpio group; sudo still requires a password.
No boot, privilege, fan or distro-package configuration was changed.

Only the private environment bootstrap completed on `test2-pi4.local`:
`/tmp/blinka-pwm-pi4-real-pin.2y4fi6z0`, with system-site-packages enabled to
inherit the unchanged distro RPi.GPIO 0.7.1a4. Actual SSH, venv creation and
private pip-version exits are all 0; private pip is 25.1.1. Wheel transfer and
installation are **not started**. No board/pwmio/RPi.GPIO runtime import or
GPIO write was made by this setup. The observed boot ID is
`5d3cf2af-f7f0-4199-a1d1-25958db13921`; it is historical, not an overnight check.

The local Pi 4 helper, collector and setup drafts are saved with recording-only
tests: all 167 cases pass, and all six files pass the format check. A broad root
Ruff invocation reports nine findings (I001, RUF059, BLE001, RUF007); this is not
described as a clean broad lint result. Scoped agent checks had passed.
The new source-policy comparison retains primary lgpio/RPi.GPIO C snapshots
with licenses, version labels and explicit binary/source provenance caveats.
Source shape alone does not establish the cause of an observed electrical delay.

## Resume here, not at capture

1. Recheck the bench, boot/configuration, cooling, free pins and private root.
   Reboot or `/tmp` loss invalidates the current setup chain; preserve the old
   receipts and prepare a fresh identity-bound chain rather than reusing them.
2. Finish reading the final helper and its tests. Finish the collector's strict
   actual-helper receipt/source/backend/cleanup binding and duplicate-key
   rejection. Add rejection of missing, empty or nonregular SAL/raw files even
   if SDK operations return successfully. Resolve lint and rerun the fakes.
   The current collector is an **unfinished draft**, not ready for hardware.
3. Complete the private offline transfer/install from the exact cached wheels,
   preserving actual outcomes and leaving distro RPi.GPIO untouched. Verify real
   installed file origins, hash-check deployment and run guarded import-only
   inspection before constructing PWMOut. Record the absent rpi_ws281x dependency;
   do not claim NeoPixel compatibility from a PWM-only non-TTY import.
4. Freeze a new Pi 4 plan before driving GPIO18. The proposed small idle test is
   50 Hz / duty 32768 / three seconds, original→native then native→original,
   using real board.D18 and unwrapped public objects. Analyzer channel 2 is
   GPIO18; channel 3 observes the untouched GPIO23 sibling. Retain all pulses,
   boundaries and failures. No plan or capture for this sequence exists yet.

The Saleae connection has been released. No new Pi 4 capture/load/helper was
started, and no ongoing remote operation was left by the completed bootstrap.
Future hardware use still needs fresh source, ownership and bench checks.

## Recovery

`pi4-preparation-night-stop.tar.gz` is a preparation snapshot, **not waveform
evidence**: 70,905 bytes, SHA256
`ca9e1d23c230ff7585aaf92a8d8818f06e3949dfab533f60cd15a4d69a694ec1`.
Its exact 26 regular members were checked directly against every original byte
and pinned SHA256; no extraction or report replay is claimed for this snapshot.
It preserves methods/tests, read-only inspection/inventory outcomes (including
the first SSH-resolution failure), the accepted bootstrap/raw outputs, source
policy comparison and primary C snapshots, reused wheel plan/parser and a
machine-readable input-pin/unfinished-work record.

The exact 23 wheels and original Blinka/native source dependencies are already
in `pi5-installed-blinka-consumer-evaluation.tar.gz`, SHA256
`59f3b680d1420faa9a11dbd1925ab24583bec181a4a70b24742404f99bda4748`.
The stop snapshot references that immutable archive rather than duplicating it.
Its `installation-preparation/wheelhouse` retains the wheels; the original
Blinka/native source tar files and explicit integration patch retain source-only
fixture dependencies. Tests expect the original sibling repository layout.
Extract each archive into a separate empty directory and inspect its methods
before use. Never run the unfinished collector or saved live setup commands
merely to recover files. Saved host, boot and `/tmp` paths can expire.
