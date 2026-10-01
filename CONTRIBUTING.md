# Contributing

This package is experimental. Preserve the CircuitPython-facing API and the
arbitrary-pin software engine while evaluating additional engines. Report
issues and propose changes through this repository's GitHub issues and pull
requests. Please follow the
[Adafruit Community Code of Conduct](https://github.com/adafruit/Adafruit_Blinka/blob/main/CODE_OF_CONDUCT.md).

## Development setup

In an activated Python 3.9+ virtual environment:

```sh
python -m pip install -e '.[test,docs,dev]'
pre-commit install
```

The repository uses `src/adafruit_blinka_raspberry_pi_pwm/` for the Python
package, `src/native/` for its C extension and scheduler, `examples/` for runnable
hardware examples, `tests/` for automated checks, and `docs/` for Sphinx sources
and evaluation records. Native sources ship in the source distribution, not as
a separate Python package.

## Checks before proposing a change

```sh
pre-commit run --all-files
python -m pytest
python -m build
make -C docs html
```

The tests need a C compiler to exercise the production native scheduler.
The GPIO extension builds only on Linux; macOS can run the API and scheduler
tests. No automated test requests physical GPIO lines.

## Hardware validation

Use [the validation plan](docs/validation.md) before driving a pin or claiming
performance improvements. Record board, OS/kernel, architecture, Python and
dependency versions, wiring, load, and measurement equipment with results.
Do not use interrupt-timestamp loopback tests as proof of waveform quality.
Blinka integration and publishing releases remain separate steps from drafting
or reorganizing this package.
