# SPDX-FileCopyrightText: 2026 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Resolver metadata must not replace the software backend's binding checks."""

import importlib.metadata
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.requirements import Requirement
from setuptools.config.pyprojecttoml import read_configuration

from adafruit_blinka_raspberry_pi_pwm import _software


@pytest.fixture
def bindings(monkeypatch):
    calls = []

    def unexpected(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Validation must not access GPIOs")

    module = SimpleNamespace(
        __version__="2.2.2",
        Chip=unexpected,
        LineSettings=unexpected,
        request_lines=unexpected,
    )
    state = SimpleNamespace(version="2.2.2", system=False, checks=0, calls=calls)

    def version(name):
        assert name == "gpiod"
        if state.version is None:
            raise importlib.metadata.PackageNotFoundError(name)
        return state.version

    def supported_system():
        state.checks += 1
        return state.system

    monkeypatch.setattr(importlib.metadata, "version", version)
    monkeypatch.setitem(sys.modules, "gpiod", module)
    monkeypatch.setitem(
        sys.modules,
        "adafruit_blinka_raspberry_pi_pwm._gpiod_compat",
        SimpleNamespace(is_supported_system_gpiod=supported_system),
    )
    return module, state


@pytest.mark.parametrize("version", ["2.2.2", "2.2.3", "2.3.0", "2.99.1"])
def test_supported_pypi_versions_do_not_need_system_exception(bindings, version):
    module, state = bindings
    state.version = version
    assert _software._load_gpiod() is module
    assert state.checks == 0
    assert state.calls == []


@pytest.mark.parametrize(
    "version", [None, "unknown", "1.6.4", "2.1.3", "2.2.0", "2.2.1", "3.0.0"]
)
def test_unsupported_versions_fail_before_gpio_access(bindings, monkeypatch, version):
    _, state = bindings
    state.version = version
    monkeypatch.setattr(sys, "executable", "/path with spaces/python")
    with pytest.raises(RuntimeError, match="Unsupported gpiod version") as error:
        _software._load_gpiod()
    assert (
        "'/path with spaces/python' -m pip install --upgrade 'gpiod>=2.2.2,<3'"
        in str(error.value)
    )
    assert "restart Python" in str(error.value)
    assert state.checks == 1
    assert state.calls == []


def test_verified_maintained_system_build_is_accepted(bindings):
    module, state = bindings
    state.version = "2.2.0"
    module.__version__ = "2.2.0"
    state.system = True
    assert _software._load_gpiod() is module
    assert state.checks == 1
    assert state.calls == []


@pytest.mark.parametrize(
    "loaded", [None, "unknown", "1.6.4", "2.2.0", "2.2.1", "3.0.0"]
)
def test_new_metadata_does_not_accept_stale_or_unknown_loaded_bindings(
    bindings, loaded
):
    module, state = bindings
    if loaded is None:
        del module.__version__
    else:
        module.__version__ = loaded
    with pytest.raises(RuntimeError, match="loaded module") as error:
        _software._load_gpiod()
    assert "restart Python" in str(error.value)
    assert state.calls == []


@pytest.mark.parametrize("missing", ["Chip", "LineSettings", "request_lines"])
def test_supported_version_still_requires_modern_api(bindings, missing):
    module, state = bindings
    delattr(module, missing)
    with pytest.raises(RuntimeError, match="required v2 API"):
        _software._load_gpiod()
    assert state.calls == []


def test_missing_bindings_give_current_interpreter_guidance(bindings, monkeypatch):
    _, state = bindings

    def missing(name):
        assert name == "gpiod"
        raise ModuleNotFoundError("No module named 'gpiod'", name="gpiod")

    monkeypatch.setattr(_software.importlib, "import_module", missing)
    with pytest.raises(RuntimeError, match="Software PWM requires") as error:
        _software._load_gpiod()
    assert "-m pip install --upgrade 'gpiod>=2.2.2,<3'" in str(error.value)
    assert state.checks == 0
    assert state.calls == []


def test_missing_transitive_import_is_not_reported_as_missing_gpiod(
    bindings, monkeypatch
):
    def missing(name):
        raise ModuleNotFoundError("No module named 'other'", name="other")

    monkeypatch.setattr(_software.importlib, "import_module", missing)
    with pytest.raises(ModuleNotFoundError) as error:
        _software._load_gpiod()
    assert error.value.name == "other"


def test_constructor_rejects_old_bindings_before_discovery_or_native_start(
    bindings, monkeypatch
):
    _, state = bindings
    state.version = "2.2.0"
    monkeypatch.setattr(sys, "platform", "linux")

    def unexpected(*args):
        raise AssertionError(
            "Incompatible bindings must fail before GPIO/native access"
        )

    monkeypatch.setattr(_software, "_find_chip", unexpected)
    monkeypatch.setitem(
        sys.modules,
        "adafruit_blinka_raspberry_pi_pwm._native",
        SimpleNamespace(start=unexpected),
    )
    with pytest.raises(RuntimeError, match="Unsupported gpiod version"):
        _software.SoftwarePWM(23, 500, 0)
    assert state.calls == []


def test_metadata_resolver_accepts_system_label_without_lowering_runtime_policy():
    root = Path(__file__).resolve().parents[1]
    config = read_configuration(str(root / "pyproject.toml"))
    requirements = {
        requirement.name: requirement
        for requirement in map(Requirement, config["project"]["dependencies"])
    }
    assert requirements["gpiod"].specifier.contains("2.2.0")
    assert not requirements["gpiod"].specifier.contains("2.1.9")
    assert not requirements["gpiod"].specifier.contains("3.0.0")
    assert requirements["gpiod"].marker.evaluate({"sys_platform": "linux"})
    assert not requirements["gpiod"].marker.evaluate({"sys_platform": "darwin"})
    assert requirements["packaging"].specifier.contains("20.0")
