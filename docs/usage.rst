Usage
=====

This experimental package provides CircuitPython-compatible ``PWMOut`` on
Raspberry Pi. Installing it does not replace Blinka's ``pwmio`` backend.

System setup
------------

Use Python 3.9+ on Linux with GPIO character-device v2 support and a recognized
Raspberry Pi GPIO controller. A source installation needs a C compiler and
matching Python development headers. In an activated virtual environment, from
the repository directory:

.. code-block:: sh

   python -m pip install .

Software output needs permission to access the GPIO character devices.
Raspberry Pi OS normally provides this through the ``gpio`` group; check your
system's configuration. Installation does not change permissions or boot setup.
Use unclaimed GPIOs, and never drive the same pin through two libraries or
processes at once. Some backends bypass character-device ownership checks.

Basic use
---------

Pins can be BCM GPIO integers or supported Blinka pins such as ``board.D18``.
BCM numbers are GPIO identities, not physical header pin numbers.

.. code-block:: python

   from adafruit_blinka_raspberry_pi_pwm import PWMOut

   with PWMOut(18, frequency=500, duty_cycle=32768) as pwm:
       input("Press Enter to stop PWM")

The defaults are ``frequency=500``, ``duty_cycle=0``, and
``variable_frequency=False``. Frequency must be a positive integer in Hz;
changing it requires ``variable_frequency=True`` at construction. Duty cycle
is an integer from 0 to 65535: 0 requests steady LOW, 65535 requests steady HIGH,
and intermediate values request the corresponding fraction of time HIGH.
These are 16-bit API values, not a guarantee of 16-bit physical resolution.
Controller quantization, GPIO latency, and scheduling affect the waveform.

Configured hardware output
--------------------------

Already-configured BCM or RP1 header PWM is preferred when its identity and
single-pin route can be verified. Otherwise an available GPIO can use software
PWM. The selected engine does not change during an object's lifetime.
Ambiguous, occupied, unsupported configured routes and hardware errors are
reported, not silently retried as software output.

Hardware setup is a separate system-administration step. It requires a matching
kernel driver and device-tree configuration, including the default pinctrl
route. RP1 also requires an unambiguous assigned header PWM0 clock. The package
does not load overlays, select pinmux, or assume a particular ``pwmchip`` number.
The user must be able to write the provider's ``export`` and ``unexport`` files
and read/write the newly exported channel's ``period``, ``duty_cycle``,
``polarity``, and ``enable`` attributes.

Recognized header mappings are:

* BCM: GPIO12 or GPIO18 is channel 0; GPIO13 or GPIO19 is channel 1.
* RP1: GPIO12 is channel 0; GPIO13 is channel 1; GPIO14 or GPIO18 is channel 2;
  GPIO15 or GPIO19 is channel 3.

Pins sharing a channel are aliases, not independent outputs. A channel routed
to multiple pins is rejected to avoid driving them together. Only the supported
header controller is eligible; on RP1 this is PWM0, not the separate cooling-fan
controller. PIO PWM, audio controllers, and other PWM providers are not selected.

Hardware frequency limits follow controller/driver clock and counter limits,
not the software 10 kHz ceiling. Unsupported periods or duties can be rejected.
An assigned RP1 clock rate is not measured runtime clock readback. Sysfs state
and the public properties describe configured values, not physical measurements.
Duty/frequency writes are not atomic or guaranteed glitch-free: updates can
truncate a pulse or introduce a gap.

Focused hardware measurements cover GPIO18 on Pi 4 and Pi 5. They do not qualify
every channel, frequency, board, or independent multi-output configuration.
Verify the actual waveform in your configuration before connecting an actuator.

Software output
---------------

Software PWM accepts 1--10000 Hz. This configuration range is not a timing or
performance guarantee: Linux scheduling and GPIO writes can introduce jitter,
late edges, and omitted pulses, especially under load. Ordinary updates take
effect at the next cycle boundary, so a 1 Hz update can take up to one second.

Two experimental options are off by default. Set them before creating outputs;
only the exact value ``1`` enables either option:

.. code-block:: sh

   BLINKA_PWM_SHORT_SLICE=1 python your_program.py
   BLINKA_PWM_SHARED=1 python your_program.py

``BLINKA_PWM_SHORT_SLICE`` requests a shorter normal-policy worker slice where
supported; unsupported or denied requests keep inherited scheduling settings.
``BLINKA_PWM_SHARED`` shares a worker between software outputs. A slow GPIO write
can delay the other outputs in its group. The options can be combined, but neither
provides real-time guarantees or phase-locked outputs.

Cleanup and safety
------------------

Use a context manager or explicitly call ``deinit()``. Successful cleanup stops
output and releases its GPIO request or hardware export; repeated cleanup is
safe. A failed hardware cleanup retains ownership for retry. Handle the reported
error and retry ``deinit()`` after addressing its cause; ``deinitialized`` remains
false until release succeeds. Do not create a replacement owner to bypass it.
RP1 hardware cleanup includes a period-derived settling wait (about 41 ms after
50 Hz use); ordinary setters do not add settling sleeps.

Hardware cleanup does not restore GPIO pinmux. A later GPIO request may need
deliberate system reconfiguration. Sysfs exports are not crash-safe leases:
``SIGKILL`` can leave hardware active, and unrelated noncooperating writers can
interfere. Objects created before a fork cannot be used in the child; create fresh
outputs there. Cleanup is not an electrical failsafe.

Power servos or motors from a suitable external supply, use a common ground and
appropriate drivers, and never power an actuator directly from a GPIO. Provide
an independent safe shutdown where uncontrolled motion could cause harm.

Check the physical output
-------------------------

1. Start with the actuator disconnected and a suitable logic analyzer or scope.
   Verify wiring, voltage compatibility, pin availability, and permissions.
2. Measure frequency and pulse width at the settings your application needs,
   including duty endpoints and small pulses, both idle and under realistic load.
3. Check duty/frequency changes, independent outputs, and LOW after cleanup.
   Test restart and pin reuse with the intended hardware configuration.
4. Record board, OS/kernel, dependency versions, wiring, load, and equipment.
   Compare existing backends separately on the same pin and conditions.

GPIO loopback timestamps are a smoke test only: interrupt latency and lost events
can hide waveform problems. A successful setter or cached readback is not proof
that an electrical transition has occurred.
