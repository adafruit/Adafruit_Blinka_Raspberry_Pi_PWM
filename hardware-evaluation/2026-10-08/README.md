# October 8: final Pi 4 installed-Blinka comparison

The planned four finite idle recordings are complete. This closes the physical
PWM test sweep; no additional broad matrix or overnight monitoring is scheduled.
Production PWM source is unchanged from `d5debaf`, both scheduler options remain
off, and no PIO, boot, permission or distro-package changes were made.

## Result and scope

On `test2-pi4.local`, GPIO18/channel2 runs through genuine `board.D18` and public
PWMOut objects. GPIO23/channel3 is an untouched LOW control. Original is the
unchanged installed Blinka RPi.GPIO wrapper; native is the actual installed
`pwmio.PWMOut` selected by the explicitly test-only integration patch.
The declared sequence is 0.2 s LOW, 3 s at 50 Hz/duty32768, 0.2 s commanded LOW,
public deinit, and 0.2 s quiet observation. Capture order is original, native,
native, original, at 100 MSa/s without filtering, CPU load or actuators.

All four final `r1c/r2c` helpers and collection commands exit 0. They report real
Pin/alias and public-class identity, exact installed source hashes, successful
public deinit, LOW boundaries and unclaimed lines. All complete intervals and
both recording boundaries are retained, not selected or trimmed.

| Final run | Complete highs | Median high (µs) | Maximum absolute high error (µs) |
| --- | ---: | ---: | ---: |
| Original r1c | 149 | 10058.290 | 60.120 |
| Native r1c | 151 | 9999.030 | 4.087 |
| Native r2c | 151 | 9999.040 | 3.947 |
| Original r2c | 149 | 10058.430 | 59.240 |

Targets reflect the implementations: original 10000 µs after integer-percent
rounding; native 10000.153 µs from the 16-bit duty and C rounding. Median adjacent
rise periods are original 20116.600/20116.860 µs versus native 19999.980/19999.990 µs.
GPIO23 remains LOW with zero edges in every final capture.
Native is more accurate in this narrow idle fixed50 comparison. This is not
overall parity, calibrated API/electrical latency or actuator-safety evidence.
Independent state-toggled binary decoding matches all complete report arrays,
boundaries and statistics: 7,041 compared values, zero differences and zero
failed checks, including the earlier accepted original-r1b separately.
The prior Pi 5 330.018-µs loaded update error and 191.132-µs installed idle motor
error remain retained qualifications; quieter samples do not supersede them.

## Failed attempts and installation provenance

The initial original-r1 attempt stops on a helper regex that rejected the real
`op -- pn` output-LOW formatter. No half-duty command ran. The next original-r1b
finishes, while native-r1b generates PWM and successfully deinitializes before
the helper misclassifies gpiod 2.5's direct-Exception `RequestReleasedError`.
Both failures and their exact helper/collector source archives remain unchanged;
neither is relabeled as accepted. The final helper accepts mode-coupled LOW
formatting and specifically catches the documented release exception. The final
177 recording-only helper/collector tests pass; these are not physical GPIO tests.

The private `/tmp/blinka-pwm-pi4-real-pin.2y4fi6z0` environment uses the same 23
cached wheels as the saved Pi 5 evaluation and inherits unchanged distro
RPi.GPIO 0.7.1a4. Actual pip install exits 0, but full `pip check` exits 1 with 17
unrelated inherited metadata/type-stub requirements. Its original install
receipt stays `accepted=false`; the whole environment is not claimed clean.
A separate inventory verifies all 26 active requirements of the tested 23-wheel
closure and 445 installed selected sources; deployment adds the exact helper as
source 446. Both revised import-only preflights pass without PWM construction.
Absent rpi_ws281x is retained; this PWM-only test makes no NeoPixel claim.

Final read-only postflight at 17:52 UTC records GPIO18/23 LOW and unclaimed, no
suspected helper/load process, 32.615°C and firmware flags 0, with unchanged
boot/configuration/provider identities. `pinctrl` reports GPIO18 input while
`gpioinfo` reports output; both raw queries are retained without conflating
their direction observations. Saleae acquisition and SSH sessions are closed.

## Recovery

`pi4-installed-half50-evaluation.tar.gz` preserves all seven attempt directories,
SAL/raw exports, complete reports, exact current and failed method versions,
plans/manifests, actual deployment/install outputs, independent audit and
read-only receipts. Its embedded file manifest records every member's SHA256
and size. The separate verification receipt records exact tar/original byte
comparison without extraction or replay; those operations are not claimed.
The archive contains 180 regular files and is 1,293,131 bytes, SHA256
`d16aa13a04dc07093c851e70f3b00798a649994ba9078b5723222c9946907214`.
See [archive-verification.json](archive-verification.json) for the exact
byte-comparison outcome and unchanged wheel/source archive references.

The Mac package suite passes 73 tests with 29 Linux-only skips; the scheduler
formatting change is nonfunctional. Scoped package/helper lint and the
warning-as-error Sphinx build pass. The executed independent-audit method has
a retained nonfunctional Ruff startswith/format warning; its source bytes are
not reformatted after the embedded method SHA was recorded.

Exact wheels and original source fixtures are referenced, not duplicated, in
`../2026-10-07/pi5-installed-blinka-consumer-evaluation.tar.gz`, SHA256
`59f3b680d1420faa9a11dbd1925ab24583bec181a4a70b24742404f99bda4748`.
The prior night-stop archive also remains immutable. Restore archives into
separate empty directories. Do not execute saved SSH/setup/capture commands
merely to recover files: host, boot and private `/tmp` identities can expire.

The next work is focused Blinka integration and package-release preparation,
not another broad physical PWM sweep. Reuse Blinka's existing gpiod backend,
preserve integer BCM pin IDs for consumers, resolve the actual header chip,
and switch GPIO/PWM requirements together. A published dependency/install
route and explicit legacy-API compatibility choices remain needed before
changing Blinka's default; this checkpoint neither publishes nor merges them.
