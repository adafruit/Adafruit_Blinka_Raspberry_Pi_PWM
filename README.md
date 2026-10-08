# Adafruit Blinka Raspberry Pi PWM

[![Build and test](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/pip.yml/badge.svg)](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/pip.yml)
[![Documentation](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/docs.yml/badge.svg)](https://github.com/makermelissa/adafruit_blinka_raspberry_pi_pwm/actions/workflows/docs.yml)

## Introduction

Experimental CircuitPython-compatible `PWMOut` for Raspberry Pi, intended for
use with Adafruit Blinka and existing CircuitPython libraries. The initial
software engine preserves arbitrary-pin PWM with a native C scheduler. A new
BCM hardware draft prefers already-configured, independently routed header PWM
channels on Pi 4 and earlier. Pi 5 currently retains software PWM; its dedicated
non-PIO RP1 hardware path is separate unfinished work.

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

## Hardware PWM draft

Hardware selection requires an existing bound BCM2835 PWM driver and a default
device-tree PWM route for the requested pin. GPIO12/18 share channel 0 and
GPIO13/19 share channel 1; a channel routed to multiple physical pins is rejected
to avoid driving an unexpected pin. No overlay is loaded automatically.
Unconfigured pins use software PWM. Busy channels, permission failures and
hardware startup errors are reported, not silently retried through GPIO.
Hardware use also requires access to the provider's sysfs export controls and
channel attributes; access to `/dev/gpiochip*` alone is not sufficient. A
configured Pi 5 RP1 header route is currently refused, not taken over by software.

Hardware frequency is limited by the controller/driver and integer-nanosecond
period representation, not the software backend's 10-kHz limit. Sysfs updates
are separate writes and are not promised to be glitch-free or atomic. No PIO is
used. The new hardware implementation has not yet completed physical qualification;
existing recorded software measurements do not validate this path.

Only exports created by this instance are released. Sysfs exports are not
file-descriptor leases: SIGKILL can leave PWM running, and unrelated sysfs writers
are not isolated. Explicit `deinit()` reports cleanup errors and retains ownership
for retry when release has not completed. A forked child never cleans up its
parent's hardware output. Use deliberate bench validation before connecting
actuators.

Releasing a hardware channel does not restore its pin to GPIO mode. The kernel's
configured PWM route remains active; changing that route is a separate system
configuration step, not something `deinit()` performs.

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
