# Lab-only native tracing

`native_trace.c` records GPIO v2 write calls and native timed waits in an
isolated diagnostic build. `setup.py` never enables it, and these files are
not part of the installed Python package. No production scheduling source is
modified. Do not use the diagnostic extension in an application.

On Linux, in a fresh **source copy under `/tmp`**, run:

```sh
python tools/build_trace.py /tmp/your-lab-copy/src/adafruit_blinka_raspberry_pi_pwm
```

The builder refuses to overwrite an existing extension. Use that source copy
only for the diagnostic subprocess via `PYTHONPATH`. Set `PWM_TRACE_PATH` to a
new absolute CSV path before importing `_native`. Load the extension with
`ctypes.CDLL(_native.__file__)` and require `pwm_trace_status() == 0` **before**
constructing any `PWMOut`: gpiod requests themselves configure hardware.
Confirm wiring, ownership, cooling, and bounded duration separately.

The CSV is exclusively created with mode 0600 and close-on-exec. Storage is
preallocated for 131072 records; no allocation or file logging occurs in the
waveform loop. Normal runs must explicitly deinitialize every output before
process exit, when records are flushed. Require the stderr footer's
`attempted == written`, `dropped == 0`, and all error fields zero. SIGKILL and
`_exit()` cannot flush the trace. Forked processes cannot use this recorder.

Record meanings:

- `I`: GPIO v2 ioctl; fd is the native duplicated single-line request descriptor,
  not the BCM pin. Level is request bit zero. Result is zero on success or errno.
- `W`: `pthread_cond_timedwait`; result is the pthread return code. Deadline and
  wall timestamps are absolute `CLOCK_MONOTONIC` nanoseconds; `cpu_ns` is elapsed
  `CLOCK_THREAD_CPUTIME_ID`, sampled outside the wall-clock bracket.
- Only `ETIMEDOUT` records are classified as timeout lateness. A successful wait
  may be a configuration/stop/spurious wake. Wait time includes condition-mutex
  reacquisition. Wall time minus CPU time does not identify why a thread was
  off CPU (timer delivery, scheduling, blocking, etc.).

Map GPIOs from sequential initial writes while retaining both live outputs,
then correlate successful level-changing writes by edge ordinal with the
external analyzer. Do not infer synchronization from the two clocks' absolute
origins. Check edge counts and report analyzer sampling/clock limitations.

Every event adds clock reads and an atomic reservation: these traces explain
**instrumented behavior**, not production performance. Keep uninstrumented
benchmarks separate. `tests/test_native_trace.py` exercises fake ioctls, real
timed waits, errno preservation, exclusive files, and concurrent recording
without requesting GPIOs.
