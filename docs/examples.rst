Examples
========

These programs drive real GPIOs. Check wiring and pin availability before
running. BCM numbers are GPIO identities, not physical header pin numbers.

LED simple test
---------------

Connect an LED with a suitable series resistor to GPIO 18 and ground.
This example additionally requires Adafruit-Blinka for ``board.D18``.

.. literalinclude:: ../examples/pwm_simpletest.py
   :language: python

Servo
-----

Use a suitable externally powered servo, a common ground, and GPIO 18 for its
signal. Do not power the servo from a GPIO. This example additionally requires
Adafruit-Blinka and adafruit-circuitpython-motor.

.. literalinclude:: ../examples/pwm_servo.py
   :language: python

Loopback validation
-------------------

Join two free GPIOs with a jumper. Choose both pins explicitly:

.. code-block:: sh

   python examples/pwm_loopback.py --output 18 --input 23 --frequency 500 --backend draft

Repeat with ``--backend blinka`` to compare with an unchanged Blinka install.
Read :doc:`validation` first: interrupt timestamps are only a smoke test.

.. literalinclude:: ../examples/pwm_loopback.py
   :language: python
