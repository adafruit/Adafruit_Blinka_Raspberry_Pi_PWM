# Adafruit Blinka Raspberry Pi PWM

[![Build and test](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/pip.yml/badge.svg)](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/pip.yml)
[![Documentation](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/docs.yml/badge.svg)](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/docs.yml)

## Introduction

Experimental CircuitPython-compatible `PWMOut` for Raspberry Pi, intended for
use with Adafruit Blinka and existing CircuitPython libraries. The initial
engine preserves arbitrary-pin software PWM with a native C scheduler.

**This is an evaluation draft, not a Blinka backend replacement.** Selected
Pi 4 and Pi 5 bench measurements are preserved in the
[recorded results](docs/draft-results.md), including timing outliers. They do not
establish overall performance parity or validate every Raspberry Pi. See the
[implementation notes](docs/design.md) and [validation gates](docs/validation.md).

## Dependencies

- Raspberry Pi running Linux with GPIO character-device v2 (kernel 5.10+).
- Python 3.9 or later and the official `gpiod` Python bindings.
- GPIO device access, normally through the `gpio` group on Raspberry Pi OS.
- A C compiler and matching Python development headers for source installation.

## Installation

There is no PyPI release or published wheel yet. Install from source in a
virtual environment:

```sh
git clone https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm.git
cd adafruit_blinka_raspberry_pi_pwm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

The examples using `board` and `adafruit_motor` additionally require
`Adafruit-Blinka` and `adafruit-circuitpython-motor`. Installing this package does
not change Blinka's PWM backend, device permissions, or boot configuration.

## Usage example

```python
import time
import board
from adafruit_blinka_raspberry_pi_pwm import PWMOut

# Connect an LED with a suitable series resistor to GPIO 18.
with PWMOut(board.D18, frequency=500, duty_cycle=32768) as output:
    time.sleep(5)
```

See [examples](docs/examples.rst) for LED, servo, and GPIO loopback programs.
BCM GPIO numbers can also be passed directly, without importing Blinka.

## Documentation

Documentation uses Sphinx, like other Blinka companion packages:

```sh
python -m pip install -e '.[docs]'
make -C docs html
```

Open `docs/_build/html/index.html` for the API reference and validation plan.
Read the Docs configuration is included; no hosted documentation site is claimed
until the repository is connected to that service.

## Contributing and testing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and checks.
Hardware tests are opt-in and must be wired deliberately; the automated test
suite does not drive GPIOs. [Recorded results](docs/draft-results.md) distinguish
API/build tests from physical waveform testing.

## License

Original code is [MIT licensed](LICENSE). No RPi.GPIO source has been copied or
vendored. Dependencies retain their own licenses.
