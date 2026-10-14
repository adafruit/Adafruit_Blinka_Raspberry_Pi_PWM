# SPDX-FileCopyrightText: 2026 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Stage a release tag in the version module without importing GPIO backends."""

import argparse
import re
from pathlib import Path

from packaging.version import InvalidVersion, Version

_PLACEHOLDER = re.compile(
    r"^(__version__\s*=\s*)([\"'])0\.0\.0\+auto\.0\2$", re.MULTILINE
)


def release_version(tag):
    """Normalize a PEP 440 tag, accepting a leading v but not local versions."""
    try:
        version = Version(tag)
    except (InvalidVersion, TypeError) as error:
        raise ValueError(f"Invalid release tag: {tag!r}") from error
    if version.local is not None:
        raise ValueError("PyPI releases cannot use local version identifiers")
    return str(version)


def set_release_version(tag, path):
    """Replace exactly one placeholder; never overwrite an already staged version."""
    version = release_version(tag)
    source = path.read_text(encoding="utf-8")
    staged, count = _PLACEHOLDER.subn(
        lambda match: f"{match[1]}{match[2]}{version}{match[2]}", source
    )
    if count != 1:
        raise ValueError("Expected exactly one unstaged version placeholder")
    path.write_text(staged, encoding="utf-8")
    return version


def main():
    """Set the version in this checkout from a maintainer-provided release tag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Published release tag, such as 1.0.1 or v1.0.1")
    arguments = parser.parse_args()
    path = (
        Path(__file__).resolve().parents[1]
        / "src/adafruit_blinka_raspberry_pi_pwm/_version.py"
    )
    try:
        version = set_release_version(arguments.tag, path)
    except ValueError as error:
        parser.error(str(error))
    print(f"Staged package version {version}")


if __name__ == "__main__":
    main()
