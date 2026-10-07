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
