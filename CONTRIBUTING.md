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

## Releases

The version lives in `src/adafruit_blinka_raspberry_pi_pwm/_version.py` with the
Adafruit development placeholder `0.0.0+auto.0`. Package metadata and the runtime
`__version__` both read that file. Do not manually bump project metadata.

After merging release preparation, publish a new GitHub release from a tag such
as `1.0.1` (or `v1.0.1`). The release workflow stages its normalized PEP 440
version in the build checkout, checks distribution metadata, and publishes the
source distribution using the repository's `pypi_username` and `pypi_password`
Actions secrets, matching Stemma Detect. A maintainer must grant this repository
access to those publishing credentials; do not put credentials in files or PRs.
Push/PR checks exercise release packaging with a synthetic tag but cannot publish.

Only source distributions are published initially. Linux installs compile the
native extension and need a C compiler and Python development headers; native
wheels need a separate platform-specific build setup. Existing releases/tags
are not changed, and a tag predating this version module cannot use this workflow.

## Hardware validation

Read [the usage guide](docs/usage.rst) before driving a pin or claiming
performance improvements. Record board, OS/kernel, architecture, Python and
dependency versions, wiring, load, and measurement equipment with results.
Do not use interrupt-timestamp loopback tests as proof of waveform quality.
Preserve the CircuitPython API, independent output ownership, and software
fallback when changing backends. Document any new timing or platform limitations.
