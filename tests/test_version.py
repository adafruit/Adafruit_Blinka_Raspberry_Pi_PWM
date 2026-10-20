# SPDX-FileCopyrightText: 2026 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Package version resolution must not require GPIO or the native extension."""

import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
IMPORT_GUARD = """
import importlib.abc
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".")
               for name in forbidden):
            raise AssertionError("Unexpected runtime import: " + fullname)

sys.meta_path.insert(0, BlockImports())
"""


def _run_python(code):
    result = subprocess.run(
        [sys.executable, "-c", IMPORT_GUARD + code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_runtime_version_comes_from_version_module_without_gpio():
    runtime, source, reloaded = _run_python(
        """
forbidden = ("gpiod", "adafruit_blinka_raspberry_pi_pwm._native")
import importlib
import adafruit_blinka_raspberry_pi_pwm as package
from adafruit_blinka_raspberry_pi_pwm import _version

runtime = package.__version__
source = _version.__version__
_version.__version__ = "987.654.321"
importlib.reload(package)
print(json.dumps([runtime, source, package.__version__]))
"""
    )
    assert runtime == source
    assert str(Version(source)) == source
    assert reloaded == "987.654.321"


def test_metadata_version_resolves_without_importing_package():
    metadata, source = _run_python(
        """
forbidden = ("gpiod", "adafruit_blinka_raspberry_pi_pwm")
from setuptools.config.pyprojecttoml import read_configuration
import runpy

config = read_configuration("pyproject.toml")
source = runpy.run_path("src/adafruit_blinka_raspberry_pi_pwm/_version.py")
print(json.dumps([config["project"]["version"], source["__version__"]]))
"""
    )
    assert Version(metadata) == Version(source)


def test_configured_hardware_output_does_not_import_gpio_bindings():
    frequency, duty, closed = _run_python(
        """
forbidden = ("gpiod", "adafruit_blinka_raspberry_pi_pwm._native",
             "adafruit_blinka_raspberry_pi_pwm._gpiod_compat")
import adafruit_blinka_raspberry_pi_pwm as package

class Hardware:
    closed = False
    def __init__(self, route, frequency, duty):
        self.settings = (frequency, duty)
    def check(self):
        pass
    def close(self):
        self.closed = True

package.discover = lambda pin: object()
package.HardwarePWM = Hardware
with package.PWMOut(18, frequency=25000, duty_cycle=32768) as output:
    frequency, duty = output.frequency, output.duty_cycle
    engine = output._engine
print(json.dumps([frequency, duty, engine.closed]))
"""
    )
    assert (frequency, duty, closed) == (25000, 32768, True)


@pytest.fixture
def release_helpers():
    return runpy.run_path(str(ROOT / "scripts" / "set_release_version.py"))


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("1.0.1", "1.0.1"),
        ("v1.0.1", "1.0.1"),
        ("v1.0.1-rc.1", "1.0.1rc1"),
        ("v1.0.1.dev1", "1.0.1.dev1"),
        ("1.0.1.post1", "1.0.1.post1"),
    ],
)
def test_release_tag_is_normalized(release_helpers, tag, expected):
    assert release_helpers["release_version"](tag) == expected


@pytest.mark.parametrize(
    "tag",
    ["", "v", "not-a-version", "1.0.1+local", "0.0.0+auto.0", "v0.0.0+auto.0"],
)
def test_invalid_or_local_release_tag_is_rejected(release_helpers, tag):
    with pytest.raises(ValueError):
        release_helpers["release_version"](tag)


@pytest.mark.parametrize("quote", ["'", '"'])
def test_release_version_replaces_only_placeholder(release_helpers, tmp_path, quote):
    path = tmp_path / "_version.py"
    prefix = '# SPDX-License-Identifier: MIT\n"""Package version."""\n\n'
    suffix = "\n# Keep this content.\n"
    path.write_text(
        f"{prefix}__version__ = {quote}0.0.0+auto.0{quote}{suffix}",
        encoding="utf-8",
    )

    release_helpers["set_release_version"]("v1.0.1", path)

    contents = path.read_text(encoding="utf-8")
    assert runpy.run_path(str(path))["__version__"] == "1.0.1"
    assert contents.startswith(prefix)
    assert contents.endswith(suffix)
    assert contents.count("__version__") == 1


@pytest.mark.parametrize(
    "contents",
    [
        '__version__ = "1.0.1"\n',
        'unrelated = "0.0.0+auto.0"\n',
        '__version__ = "0.0.0+auto.0"\n__version__ = "0.0.0+auto.0"\n',
    ],
)
def test_missing_or_duplicate_placeholder_is_unchanged(
    release_helpers, tmp_path, contents
):
    path = tmp_path / "_version.py"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError):
        release_helpers["set_release_version"]("1.0.2", path)

    assert path.read_text(encoding="utf-8") == contents
