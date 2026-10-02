"""Build the Linux native engine; other hosts can run the Python contract tests."""

import sys

from setuptools import Extension, setup

setup(
    ext_modules=(
        [
            Extension(
                "adafruit_blinka_raspberry_pi_pwm._native",
                sources=[
                    "src/native/module.c",
                    "src/native/pwm_engine.c",
                    "src/native/pwm_shared.c",
                ],
                include_dirs=["src/native"],
                define_macros=[("_POSIX_C_SOURCE", "200809L")],
                extra_compile_args=["-std=c11", "-Wall", "-Wextra", "-pthread"],
                extra_link_args=["-pthread"],
            )
        ]
        if sys.platform == "linux"
        else []
    )
)
