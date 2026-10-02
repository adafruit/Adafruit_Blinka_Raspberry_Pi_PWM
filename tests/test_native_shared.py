"""Production shared scheduler checks without GPIO access."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("scenario", ["deadline", "stress"])
def test_shared_scheduler(tmp_path, scenario):
    compiler = shutil.which(os.environ.get("CC", "cc"))
    if compiler is None:
        pytest.skip("shared scheduler checks need a C compiler")
    root = Path(__file__).resolve().parents[1]
    executable = tmp_path / "shared-deadlines"
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
            str(root / "src/native"),
            *(
                [str(root / "tests/native_shared_deadline_test.c")]
                if scenario == "deadline"
                else [
                    str(root / "src/native/pwm_shared.c"),
                    str(root / "tests/native_shared_stress_test.c"),
                ]
            ),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run([str(executable)], check=True, timeout=10)
