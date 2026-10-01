"""Compile and exercise the production scheduler without GPIO or Python mocks."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def test_native_scheduler(tmp_path):
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
            "-I",
            str(root / "native"),
            str(root / "native/pwm_engine.c"),
            str(root / "tests/native_engine_test.c"),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run([str(executable)], check=True, timeout=10)
