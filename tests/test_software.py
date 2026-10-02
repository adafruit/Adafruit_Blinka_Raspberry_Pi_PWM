"""Pin discovery and resource ownership contracts without changing hardware."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from adafruit_blinka_raspberry_pi_pwm import _software


@pytest.mark.parametrize(
    "pin,expected",
    [
        (18, (None, 18)),
        (SimpleNamespace(id=12), (None, 12)),
        (SimpleNamespace(id=(4, 13)), ("/dev/gpiochip4", 13)),
        (SimpleNamespace(id=("/dev/gpiochip0", 19)), ("/dev/gpiochip0", 19)),
    ],
)
def test_pin_identity(pin, expected):
    assert _software._pin_id(pin) == expected


@pytest.mark.parametrize("pin", [True, "18", -1, 1.5, (True, 18), ("bad", 18)])
def test_invalid_pin_identity(pin):
    with pytest.raises((TypeError, ValueError)):
        _software._pin_id(pin)


class FakeChip:
    def __init__(self, path, chips):
        self.path = path
        self.chips = chips

    def __enter__(self):
        if isinstance(self.chips[self.path], Exception):
            raise self.chips[self.path]
        return self

    def __exit__(self, *args):
        pass

    def get_info(self):
        return self.chips[self.path]


def fake_gpiod(chips):
    return SimpleNamespace(Chip=lambda path: FakeChip(path, chips))


def test_pi5_chip_discovery_does_not_assume_index(monkeypatch):
    chips = {
        "/dev/gpiochip0": SimpleNamespace(label="gpio-brcmstb", num_lines=32),
        "/dev/gpiochip10": SimpleNamespace(label="pinctrl-rp1", num_lines=54),
    }
    monkeypatch.setattr(Path, "glob", lambda *args: map(Path, chips))
    assert _software._find_chip(fake_gpiod(chips), 18) == "/dev/gpiochip10"


def test_gpiochip_aliases_are_not_ambiguous(tmp_path, monkeypatch):
    controller = tmp_path / "gpiochip0"
    controller.touch()
    alias = tmp_path / "gpiochip4"
    alias.symlink_to(controller)
    chips = {str(controller): SimpleNamespace(label="pinctrl-rp1", num_lines=54)}
    monkeypatch.setattr(Path, "glob", lambda *args: [controller, alias])
    assert _software._find_chip(fake_gpiod(chips), 18) == str(controller)


def test_distinct_matching_chips_remain_ambiguous(monkeypatch):
    chips = {
        "/dev/gpiochip0": SimpleNamespace(label="pinctrl-rp1", num_lines=54),
        "/dev/gpiochip10": SimpleNamespace(label="pinctrl-rp1", num_lines=54),
    }
    monkeypatch.setattr(Path, "glob", lambda *args: map(Path, chips))
    with pytest.raises(RuntimeError, match="Multiple"):
        _software._find_chip(fake_gpiod(chips), 18)


@pytest.mark.parametrize("label", ["pinctrl-bcm2835", "pinctrl-bcm2711"])
def test_earlier_pi_discovery(label):
    chips = {"/dev/gpiochip0": SimpleNamespace(label=label, num_lines=54)}
    assert (
        _software._find_chip(fake_gpiod(chips), 18, "/dev/gpiochip0")
        == "/dev/gpiochip0"
    )
    with pytest.raises(ValueError):
        _software._find_chip(fake_gpiod(chips), 100, "/dev/gpiochip0")


def test_discovery_permission_failure():
    chips = {"/dev/gpiochip0": PermissionError("denied")}
    with pytest.raises(PermissionError, match="gpio group"):
        _software._find_chip(fake_gpiod(chips), 18, "/dev/gpiochip0")


def test_native_start_failure_releases_request(monkeypatch):
    request = SimpleNamespace(fd=99, released=False)
    request.release = lambda: setattr(request, "released", True)

    def fail(*args):
        raise OSError("native startup failure")

    native = SimpleNamespace(start=fail)
    fake = SimpleNamespace(
        request_lines=lambda *args, **kwargs: request,
        LineSettings=lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "gpiod", fake)
    monkeypatch.setitem(
        sys.modules,
        "gpiod.line",
        SimpleNamespace(
            Direction=SimpleNamespace(OUTPUT=1), Value=SimpleNamespace(INACTIVE=0)
        ),
    )
    monkeypatch.setitem(sys.modules, "adafruit_blinka_raspberry_pi_pwm._native", native)
    import adafruit_blinka_raspberry_pi_pwm

    monkeypatch.setattr(
        adafruit_blinka_raspberry_pi_pwm, "_native", native, raising=False
    )
    monkeypatch.setattr(_software, "_find_chip", lambda *args: "/dev/gpiochip0")
    with pytest.raises(OSError, match="startup"):
        _software.SoftwarePWM(18, 500, 0)
    assert request.released


@pytest.mark.parametrize(
    "setting,enabled",
    [(None, False), ("1", True), ("0", False), ("true", False), ("", False)],
)
@pytest.mark.parametrize(
    "shared_setting,shared_enabled",
    [(None, False), ("1", True), ("0", False), ("true", False), ("", False)],
)
def test_scheduler_options_are_explicit_opt_ins(
    monkeypatch, setting, enabled, shared_setting, shared_enabled
):
    calls = []
    request = SimpleNamespace(fd=99, release=lambda: None)
    native = SimpleNamespace(start=lambda *args: calls.append(args))
    fake = SimpleNamespace(
        request_lines=lambda *args, **kwargs: request,
        LineSettings=lambda **kwargs: kwargs,
    )
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "gpiod", fake)
    monkeypatch.setitem(
        sys.modules,
        "gpiod.line",
        SimpleNamespace(
            Direction=SimpleNamespace(OUTPUT=1), Value=SimpleNamespace(INACTIVE=0)
        ),
    )
    import adafruit_blinka_raspberry_pi_pwm

    monkeypatch.setattr(
        adafruit_blinka_raspberry_pi_pwm, "_native", native, raising=False
    )
    monkeypatch.setattr(_software, "_find_chip", lambda *args: "/dev/gpiochip0")
    if setting is None:
        monkeypatch.delenv("BLINKA_PWM_SHORT_SLICE", raising=False)
    else:
        monkeypatch.setenv("BLINKA_PWM_SHORT_SLICE", setting)
    if shared_setting is None:
        monkeypatch.delenv("BLINKA_PWM_SHARED", raising=False)
    else:
        monkeypatch.setenv("BLINKA_PWM_SHARED", shared_setting)
    _software.SoftwarePWM(18, 500, 0)
    assert calls == [(99, 500, 0, enabled, shared_enabled)]
