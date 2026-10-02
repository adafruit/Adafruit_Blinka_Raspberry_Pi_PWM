"""Compile and exercise the production scheduler without GPIO or Python mocks."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("shared", [False, True])
def test_native_scheduler(tmp_path, shared):
    compiler = shutil.which(os.environ.get("CC", "cc"))
    if compiler is None:
        pytest.skip("native scheduler test needs a C compiler")
    root = Path(__file__).resolve().parents[1]
    executable = tmp_path / "native-engine-test"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-D_POSIX_C_SOURCE=200809L",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pthread",
            *(["-DPWM_TEST_SHARED"] if shared else []),
            "-I",
            str(root / "src/native"),
            str(root / ("src/native/pwm_shared.c" if shared else "src/native/pwm_engine.c")),
            str(root / "tests/native_engine_test.c"),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run([str(executable)], check=True, timeout=10)


@pytest.fixture(scope="module", params=[False, True], ids=["per-output", "shared"])
def slice_executable(tmp_path_factory, request):
    if sys.platform != "linux":
        pytest.skip("Linux scheduling syscalls")
    compiler = shutil.which(os.environ.get("CC", "cc"))
    if compiler is None:
        pytest.skip("slice tests need a C compiler")
    root = Path(__file__).resolve().parents[1]
    executable = tmp_path_factory.mktemp("native-slice") / "slice-test"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-D_POSIX_C_SOURCE=200809L",
            "-Dsyscall=pwm_test_syscall",
            *(["-DPWM_TEST_SHARED"] if request.param else []),
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pthread",
            "-I",
            str(root / "src/native"),
            str(root / ("src/native/pwm_shared.c" if request.param else "src/native/pwm_engine.c")),
            str(root / "tests/native_slice_test.c"),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    return executable


@pytest.mark.parametrize(
    "scenario",
    [
        "disabled",
        "success",
        "get-unsupported",
        "get-denied",
        "set-unsupported",
        "set-denied",
        "non-normal",
        "future-abi",
    ],
)
def test_optional_worker_slice(slice_executable, scenario):
    subprocess.run([str(slice_executable), scenario], check=True, timeout=10)
