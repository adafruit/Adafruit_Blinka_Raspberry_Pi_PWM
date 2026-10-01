"""Exercise production extension startup with injected syscalls, never GPIO."""

import errno
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD_SCRIPT = """
import sys
from pathlib import Path
from setuptools import Extension, setup

root, output = map(Path, sys.argv[1:])
setup(
    name="pwm-startup-regression",
    ext_modules=[Extension(
        "_native",
        sources=[str(root / path) for path in (
            "src/native/module.c", "src/native/pwm_engine.c",
            "tests/native_startup_shim.c",
        )],
        include_dirs=[str(root / "src/native")],
        define_macros=[("_POSIX_C_SOURCE", "200809L"),
                       ("ioctl", "pwm_test_ioctl"),
                       ("pthread_create", "pwm_test_pthread_create")],
        extra_compile_args=["-std=c11", "-Wall", "-Wextra", "-pthread"],
        extra_link_args=["-pthread"],
    )],
    script_args=["build_ext", "--build-lib", str(output),
                 "--build-temp", str(output / "build")],
)
"""

CHECK_SCRIPT = """
import os
import sys

sys.path.insert(0, sys.argv[1])
import _native

duty, expected_errno = map(int, sys.argv[2:])
read_fd, write_fd = os.pipe()
try:
    try:
        _native.start(write_fd, 500, duty)
    except OSError as error:
        assert error.errno == expected_errno, error
    else:
        raise AssertionError("injected startup failure was not reported")
finally:
    os.close(write_fd)

try:
    os.set_blocking(read_fd, False)
    expected = b"10" if duty == 65535 else b"00"
    assert os.read(read_fd, 2) == expected, "startup must attempt a low write"
    # EOF proves the extension also closed its duplicated descriptor.
    assert os.read(read_fd, 1) == b"", "duplicated descriptor was not closed"
finally:
    os.close(read_fd)
"""


@pytest.fixture(scope="module")
def startup_extension(tmp_path_factory):
    if shutil.which(os.environ.get("CC", "cc")) is None:
        pytest.skip("native startup test needs a C compiler")
    root = Path(__file__).resolve().parents[1]
    output = tmp_path_factory.mktemp("startup-extension")
    subprocess.run(
        [sys.executable, "-c", BUILD_SCRIPT, str(root), str(output)],
        cwd=output,
        check=True,
        timeout=30,
    )
    return output


@pytest.mark.parametrize(
    "duty,low_failure,initial_failure",
    [
        (0, False, False),
        (32768, False, False),
        (65535, False, False),
        (65535, True, False),
        (65535, True, True),
    ],
)
def test_failed_startup_attempts_low_and_preserves_error(
    startup_extension, duty, low_failure, initial_failure
):
    environment = os.environ.copy()
    for name, enabled in (
        ("PWM_TEST_LOW_FAILURE", low_failure),
        ("PWM_TEST_INITIAL_FAILURE", initial_failure),
    ):
        environment.pop(name, None)
        if enabled:
            environment[name] = "1"
    expected_errno = errno.EPERM if initial_failure else errno.EAGAIN
    subprocess.run(
        [
            sys.executable,
            "-c",
            CHECK_SCRIPT,
            str(startup_extension),
            str(duty),
            str(expected_errno),
        ],
        env=environment,
        check=True,
        timeout=10,
    )
