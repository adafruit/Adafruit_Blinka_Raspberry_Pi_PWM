Adafruit Blinka Raspberry Pi PWM
================================

Experimental CircuitPython-compatible PWM for Raspberry Pi: arbitrary-pin
software output and a draft backend for configured BCM/RP1 hardware channels.
This draft does not replace Blinka's existing backend. Hardware waveform and
performance validation are required before migration.

.. toctree::
   :maxdepth: 2

   design
   api
   examples
   validation
   draft-results

The :download:`draft Blinka integration patch <blinka-integration.patch>` is
illustrative only. Installing this package does not apply it.
