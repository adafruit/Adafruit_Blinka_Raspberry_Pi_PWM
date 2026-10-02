# SPDX-License-Identifier: MIT
"""Own a gpiod v2 line request while the native worker drives its descriptor."""

import operator
import os
import sys
from pathlib import Path

_LABELS = {"pinctrl-bcm2835", "pinctrl-bcm2711", "pinctrl-rp1"}


def _pin_id(pin):
    identity = getattr(pin, "id", pin)
    chip = None
    if isinstance(identity, tuple) and len(identity) == 2:
        chip, identity = identity
        if isinstance(chip, int) and not isinstance(chip, bool) and chip >= 0:
            chip = f"/dev/gpiochip{chip}"
        elif not isinstance(chip, str) or not chip.startswith("/dev/gpiochip"):
            raise TypeError("pin chip must be a gpiochip number or /dev/gpiochip path")
    if isinstance(identity, bool):
        raise TypeError("pin must be a Blinka Pin or BCM GPIO number")
    try:
        offset = operator.index(identity)
    except TypeError:
        raise TypeError("pin must be a Blinka Pin or BCM GPIO number") from None
    if offset < 0:
        raise ValueError("GPIO number must be nonnegative")
    return chip, offset


def _find_chip(gpiod, offset, explicit=None):
    """Find the header controller by label, not a kernel-dependent chip index."""
    paths = [Path(explicit)] if explicit else sorted(Path("/dev").glob("gpiochip*"))
    candidates = []
    inaccessible = []
    seen = set()
    for path in paths:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        try:
            with gpiod.Chip(str(path)) as chip:
                info = chip.get_info()
                if info.label in _LABELS and offset < info.num_lines:
                    candidates.append(str(path))
        except PermissionError:
            inaccessible.append(str(path))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise RuntimeError("Multiple Raspberry Pi GPIO controllers match this pin")
    if inaccessible:
        raise PermissionError(
            "Cannot inspect GPIO controllers: "
            + ", ".join(inaccessible)
            + ". Grant this user access to the gpio group and log in again."
        )
    raise ValueError(f"No Raspberry Pi GPIO controller exposes GPIO {offset}")


class SoftwarePWM:
    """Backend contract: configure(), check(), close(); no Blinka dependency."""

    def __init__(self, pin, frequency, duty_cycle):
        self._request = None
        self._handle = None
        if sys.platform != "linux":
            raise RuntimeError("Raspberry Pi PWM requires Linux")
        try:
            from . import _native
        except ImportError as error:
            raise RuntimeError(
                "Native PWM extension is missing; reinstall the package"
            ) from error
        import gpiod
        from gpiod.line import Direction, Value

        self._native = _native
        explicit, offset = _pin_id(pin)
        path = _find_chip(gpiod, offset, explicit)
        try:
            self._request = gpiod.request_lines(
                path,
                consumer="adafruit-blinka-pwm",
                config={
                    offset: gpiod.LineSettings(
                        direction=Direction.OUTPUT, output_value=Value.INACTIVE
                    )
                },
            )
            self._handle = _native.start(
                self._request.fd,
                frequency,
                duty_cycle,
                os.environ.get("BLINKA_PWM_SHORT_SLICE") == "1",
                os.environ.get("BLINKA_PWM_SHARED") == "1",
            )
        except BaseException:
            if self._request is not None:
                self._request.release()
                self._request = None
            raise

    def configure(self, frequency, duty_cycle):
        self._native.configure(self._handle, frequency, duty_cycle)

    def check(self):
        self._native.check(self._handle)

    def close(self):
        try:
            if self._handle is not None:
                self._native.stop(self._handle)
        finally:
            self._handle = None
            if self._request is not None:
                self._request.release()
                self._request = None
