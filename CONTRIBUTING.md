# Contributing

Contributions are welcome. Please follow the [Code of Conduct](CODE_OF_CONDUCT.md)
and use GitHub issues and pull requests for bug reports and proposed changes.

## Development setup

In an activated Python 3.9+ virtual environment:

```sh
python -m pip install -e '.[test,docs,dev]'
pre-commit install
```

The repository uses `src/adafruit_blinka_raspberry_pi_pwm/` for the Python
package, `src/native/` for its C extension and scheduler, `examples/` for runnable
hardware examples, `tests/` for automated checks, and `docs/` for Sphinx sources
for user documentation. Native sources ship in the source distribution, not as
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

Read [the usage guide](docs/usage.rst) before driving a pin or claiming
performance improvements. Record board, OS/kernel, architecture, Python and
dependency versions, wiring, load, and measurement equipment with results.
Do not use interrupt-timestamp loopback tests as proof of waveform quality.
Preserve the CircuitPython API, independent output ownership, and software
fallback when changing backends. Document any new timing or platform limitations.
