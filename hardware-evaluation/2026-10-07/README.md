# October 7 default-native Pi 5 comparison

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
