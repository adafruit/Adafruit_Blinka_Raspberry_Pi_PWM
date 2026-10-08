Introduction
============

.. image:: https://github.com/makermelissa/Adafruit_Blinka_Raspberry_Pi_PWM/actions/workflows/pip.yml/badge.svg
    :target: https://github.com/makermelissa/Adafruit_Blinka_Raspberry_Pi_PWM/actions/workflows/pip.yml
    :alt: Build Status

.. image:: https://github.com/makermelissa/Adafruit_Blinka_Raspberry_Pi_PWM/actions/workflows/docs.yml/badge.svg
    :target: https://github.com/makermelissa/Adafruit_Blinka_Raspberry_Pi_PWM/actions/workflows/docs.yml
    :alt: Documentation Build

.. image:: https://img.shields.io/discord/327254708534116352.svg
    :target: https://adafru.it/discord
    :alt: Discord

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Code Style: Ruff

CircuitPython-compatible ``PWMOut`` for Raspberry Pi, intended for use with
Adafruit Blinka and CircuitPython libraries. It uses configured BCM/RP1 hardware
PWM where available and native software PWM on other GPIOs. No PIO is used.

This package is under development. Installing it does not automatically replace
Blinka's PWM backend or configure hardware PWM.

Dependencies
============

* Python 3.9 or later on Raspberry Pi Linux with GPIO character-device v2 support.
* The official ``gpiod`` Python bindings for software PWM.
* Permission to access GPIO devices and, for hardware PWM, its sysfs controls.
* A C compiler and matching Python development headers for source installation.

Examples using ``board`` also need Adafruit-Blinka; the servo example additionally
needs ``adafruit-circuitpython-motor``.

Installing from source
======================

Until a PyPI release is available, install from this repository in a virtual
environment:

.. code-block:: shell

    git clone https://github.com/makermelissa/Adafruit_Blinka_Raspberry_Pi_PWM.git
    cd Adafruit_Blinka_Raspberry_Pi_PWM
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install .

Usage
=====

Connect an LED with a suitable series resistor to GPIO18 and ground:

.. code-block:: python

    import time
    import board
    from adafruit_blinka_raspberry_pi_pwm import PWMOut

    with PWMOut(board.D18, frequency=500, duty_cycle=32768) as pwm:
        time.sleep(5)

BCM GPIO numbers, such as ``PWMOut(18)``, can be used without importing Blinka.
Duty cycle ranges from 0 to 65535. To change frequency after construction, pass
``variable_frequency=True``. See `examples <examples/>`_ for LED, servo, and
loopback programs.

Hardware PWM and timing
=======================

Hardware selection requires a configured kernel PWM driver and a verified
single-pin route. The package does not load overlays or change pinmux. Occupied
channels and hardware errors are reported rather than silently switching to
software. Unconfigured GPIOs use software PWM.

Hardware frequency limits depend on the controller and driver. Software accepts
1--10000 Hz, but Linux scheduling affects timing and jitter. Duty resolution is
controller-dependent, and updates are not guaranteed glitch-free. Hardware
cleanup releases the channel but leaves its pinmux configured; a forced process
termination can leave PWM active.

Read the `usage guide <docs/usage.rst>`_ for setup, channel mapping, ownership,
and safety details. Check the waveform before connecting motors or servos.

Documentation
=============

The `documentation sources <docs/index.rst>`_ contain the usage guide, API
reference, and examples. Build them locally with:

.. code-block:: shell

    python -m pip install '.[docs]'
    python -m sphinx -W -b html docs docs/_build/html

Development and contributing
============================

See `CONTRIBUTING.md <CONTRIBUTING.md>`_ for development setup and checks.
Participation follows the `Code of Conduct <CODE_OF_CONDUCT.md>`_. Automated
tests do not drive GPIOs; hardware examples require deliberate wiring.

AI-assisted development
=======================

OpenAI Codex has assisted with implementation, tests, documentation, and
hardware-test tooling and analysis. AI-generated work does not replace human
review or physical validation, or establish correctness, timing, safety, or
compatibility on its own.

License
========

This project uses the MIT license; see `LICENSE <LICENSE>`_.
