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
            "src/native/module.c", "src/native/pwm_engine.c", "src/native/pwm_shared.c",
            "tests/native_startup_shim.c",
        )],
        include_dirs=[str(root / "src/native")],
        define_macros=[("_POSIX_C_SOURCE", "200809L"),
                       ("ioctl", "pwm_test_ioctl"),
                       ("prctl", "pwm_test_prctl"),
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

duty, expected_errno, shared = map(int, sys.argv[2:])
read_fd, write_fd = os.pipe()
try:
    try:
        _native.start(write_fd, 500, duty, False, bool(shared))
    except OSError as error:
        assert error.errno == expected_errno, error
    else:
        raise AssertionError("injected startup failure was not reported")
finally:
    os.close(write_fd)

try:
    os.set_blocking(read_fd, False)
    expected = b"10" if duty == 65535 else b"00"
    if os.environ.get("PWM_TEST_TIMER_FAILURE"):
        expected += b"0"  # Worker cleanup, then extension cleanup.
    assert os.read(read_fd, len(expected)) == expected, "startup must attempt a low write"
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
@pytest.mark.parametrize("shared", [False, True])
def test_failed_startup_attempts_low_and_preserves_error(
    startup_extension, duty, low_failure, initial_failure, shared
):
    environment = os.environ.copy()
    for name, enabled in (
        ("PWM_TEST_LOW_FAILURE", low_failure),
        ("PWM_TEST_INITIAL_FAILURE", initial_failure),
        ("PWM_TEST_TIMER_FAILURE", False),
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
            str(int(shared)),
        ],
        env=environment,
        check=True,
        timeout=10,
    )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux worker timer slack")
@pytest.mark.parametrize(
    "duty,low_failure", [(0, False), (65535, False), (65535, True)]
)
@pytest.mark.parametrize("shared", [False, True])
def test_failed_timer_setup_is_reported_during_startup(
    startup_extension, duty, low_failure, shared
):
    environment = os.environ.copy()
    environment.pop("PWM_TEST_INITIAL_FAILURE", None)
    environment.pop("PWM_TEST_LOW_FAILURE", None)
    environment["PWM_TEST_TIMER_FAILURE"] = "1"
    if low_failure:
        environment["PWM_TEST_LOW_FAILURE"] = "1"
    subprocess.run(
        [
            sys.executable,
            "-c",
            CHECK_SCRIPT,
            str(startup_extension),
            str(duty),
            str(errno.EACCES),
            str(int(shared)),
        ],
        env=environment,
        check=True,
        timeout=10,
    )
