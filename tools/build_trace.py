"""Build a lab-only _native into an isolated SOURCE COPY, never the real checkout.

Run on Linux: python tools/build_trace.py /tmp/lab/source/src/adafruit_blinka_raspberry_pi_pwm
Use PYTHONPATH=/tmp/lab/source/src only for the diagnostic subprocess. Nothing in
setup.py or the installable package enables these wrappers.
"""

import hashlib
import json
import shlex
import subprocess
import sys
import sysconfig
from pathlib import Path


def main():
    if sys.platform != "linux" or len(sys.argv) != 2:
        raise SystemExit("Requires Linux and an isolated package output directory")
    root = Path(__file__).resolve().parents[1]
    directory = Path(sys.argv[1]).resolve(strict=True)
    if not directory.is_dir() or directory.name != "adafruit_blinka_raspberry_pi_pwm":
        raise SystemExit("Output must be an existing isolated package directory")
    if not str(directory).startswith("/tmp/"):
        raise SystemExit(
            "Diagnostic build is restricted to an isolated /tmp source copy"
        )
    output = directory / ("_native" + sysconfig.get_config_var("EXT_SUFFIX"))
    if output.exists():
        raise SystemExit(f"Refusing to overwrite {output}")
    sources = [
        root / "src/native" / name
        for name in ("module.c", "pwm_engine.c", "pwm_shared.c")
    ]
    sources.append(root / "tools/native_trace.c")
    command = shlex.split(sysconfig.get_config_var("LDSHARED"))
    command += shlex.split(sysconfig.get_config_var("CFLAGS") or "")
    command += shlex.split(sysconfig.get_config_var("CCSHARED") or "")
    command += [
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-pthread",
        "-D_POSIX_C_SOURCE=200809L",
        "-Dioctl=pwm_trace_ioctl",
        "-Dpthread_cond_timedwait=pwm_trace_wait",
        "-I" + sysconfig.get_paths()["include"],
        "-I" + str(root / "src/native"),
    ]
    command += [str(path) for path in sources] + ["-o", str(output)]
    subprocess.run(command, check=True)
    print(
        json.dumps(
            {
                "output": str(output),
                "command": command,
                "sources_sha256": {
                    str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sources
                },
                "extension_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
