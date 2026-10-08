"""BCM/RP1 backend contracts using temporary files, never GPIO or real sysfs."""

import errno
import os
import struct
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from adafruit_blinka_raspberry_pi_pwm import _hardware as hw


def strings(path, *values):
    path.write_bytes(b"\0".join(value.encode("ascii") for value in values) + b"\0")


def cells(path, *values):
    path.write_bytes(struct.pack(">" + "I" * len(values), *values))


@pytest.fixture
def bench(tmp_path, monkeypatch):
    dt = tmp_path / "of"
    dt.mkdir()
    strings(dt / "compatible", "raspberrypi,4-model-b", "brcm,bcm2711")
    soc = dt / "soc"
    soc.mkdir()
    gpio = soc / "gpio@7e200000"
    gpio.mkdir()
    strings(gpio / "compatible", "brcm,bcm2711-gpio")
    group = gpio / "pwm_pins"
    group.mkdir()
    cells(group / "phandle", 55)
    cells(group / "brcm,pins", 18, 13)
    cells(group / "brcm,function", 2, 4)
    node = soc / "pwm@7e20c000"
    node.mkdir()
    strings(node / "compatible", "brcm,bcm2835-pwm")
    strings(node / "status", "okay")
    strings(node / "pinctrl-names", "default")
    cells(node / "pinctrl-0", 55)
    sysfs = tmp_path / "pwm"
    sysfs.mkdir()
    driver = tmp_path / "bcm2835-pwm"
    driver.mkdir()
    chip = sysfs / "pwmchip42"
    (chip / "device").mkdir(parents=True)
    (chip / "device" / "of_node").symlink_to(node, target_is_directory=True)
    (chip / "device" / "driver").symlink_to(driver, target_is_directory=True)
    (chip / "npwm").write_text("2")
    (chip / "export").touch()
    (chip / "unexport").touch()
    monkeypatch.setattr(hw, "DEVICE_TREE", dt)
    monkeypatch.setattr(hw, "SYSFS_PWM", sysfs)
    monkeypatch.setattr(hw.sys, "platform", "linux")
    monkeypatch.setattr(hw, "_owners", set())
    return SimpleNamespace(
        dt=dt, gpio=gpio, group=group, node=node, sysfs=sysfs, chip=chip, driver=driver
    )


class FakeSysfs:
    def __init__(self):
        self.calls = []
        self.failure = None
        self.busy = False
        self.initial = {"period": 0, "duty_cycle": 0, "polarity": "normal", "enable": 0}

    def write(self, path, value):
        self.calls.append((path, value))
        if self.failure is not None and self.failure(path, value):
            raise OSError(errno.EIO, "injected write failure")
        if path.name == "export":
            if self.busy:
                raise OSError(errno.EBUSY, "already requested")
            channel = path.parent / f"pwm{value}"
            channel.mkdir()
            for name, initial in self.initial.items():
                (channel / name).write_text(str(initial))
        elif path.name == "unexport":
            channel = path.parent / f"pwm{value}"
            for name in ("period", "duty_cycle", "polarity", "enable"):
                (channel / name).unlink()
            channel.rmdir()
        else:
            state = {name: (path.parent / name).read_text() for name in self.initial}
            updated = {**state, path.name: str(value)}
            # Model BCM driver validation even for disabled states. An unchanged
            # cached request can be a no-op, but any driver apply needs a valid
            # positive period and duty <= period. This catches zero-period
            # polarity applies and inherited-duty period-shrink ordering.
            if updated != state and (
                int(updated["period"]) <= 0
                or int(updated["duty_cycle"]) > int(updated["period"])
            ):
                raise OSError(errno.EINVAL, "invalid driver apply")
            path.write_text(str(value))


@pytest.fixture
def io(monkeypatch):
    fake = FakeSysfs()
    monkeypatch.setattr(hw, "_write_text", fake.write)
    return fake


@pytest.mark.parametrize(
    "gpio,channel,function", [(12, 0, 4), (13, 1, 4), (18, 0, 2), (19, 1, 2)]
)
def test_discovery_correct_aliases_without_chip_number_assumptions(
    bench, gpio, channel, function
):
    cells(bench.group / "brcm,pins", gpio)
    cells(bench.group / "brcm,function", function)
    route = hw.discover(SimpleNamespace(id=gpio))
    assert route.gpio == gpio and route.channel == channel
    assert route.chip == bench.chip and route.of_node == bench.node
    assert route.gpio_node == bench.gpio and route.pinctrl_nodes == (bench.group,)
    with pytest.raises(FrozenInstanceError):
        route.channel = 7


def test_generic_default_mux_supports_children_and_default_index(bench):
    (bench.group / "brcm,pins").unlink()
    (bench.group / "brcm,function").unlink()
    child = bench.group / "mux"
    child.mkdir()
    strings(child / "pins", "gpio12", "gpio13")
    strings(child / "function", "alt0")
    strings(bench.node / "pinctrl-names", "idle", "default")
    (bench.node / "pinctrl-0").unlink()
    cells(bench.node / "pinctrl-1", 55)
    assert hw.discover(12).channel == 0
    assert hw.discover(13).channel == 1
    assert hw.discover(18) is None


def test_generic_grandchildren_are_not_an_active_kernel_mux(bench):
    (bench.group / "brcm,pins").unlink()
    (bench.group / "brcm,function").unlink()
    ignored = bench.group / "wrapper" / "ignored"
    ignored.mkdir(parents=True)
    strings(ignored / "pins", "gpio18")
    strings(ignored / "function", "alt5")
    assert hw.discover(18) is None


def test_mixed_legacy_parent_and_generic_child_do_not_claim_ignored_legacy(bench):
    child = bench.group / "generic"
    child.mkdir()
    strings(child / "pins", "gpio23")
    strings(child / "function", "gpio_out")
    with pytest.raises(hw.HardwareError, match="Mixed generic/legacy"):
        hw.discover(18)


def test_missing_route_and_explicit_tuple_are_software_eligible(bench):
    assert hw.discover(12) is None
    assert hw.discover(23) is None
    assert hw.discover((0, 18)) is None
    (bench.node / "pinctrl-names").unlink()
    assert hw.discover(18) is None


@pytest.mark.parametrize("other", [12, 40, 52])
def test_channel_fanout_is_a_hard_conflict_not_fallback(bench, other):
    function = hw._MUX[other][1]
    cells(bench.group / "brcm,pins", 18, other)
    cells(bench.group / "brcm,function", 2, function)
    with pytest.raises(hw.HardwareError, match="fans out"):
        hw.discover(18)


@pytest.mark.parametrize(
    "compatible,node_name,npwm",
    [
        ("raspberrypi,rp1-pwm", "pwm@98000", 4),
        ("raspberrypi,rp1-pwm", "pwm@9c000", 4),
        ("raspberrypi,rp1-pio", "pwm@7e20c000", 2),
        ("brcm,bcm2835-pwm", "pwm@7e20c800", 2),
        ("pwm-gpio", "pwm@7e20c000", 1),
    ],
)
def test_rp1_fan_audio_pio_and_software_providers_are_not_selected(
    bench, compatible, node_name, npwm
):
    strings(bench.node / "compatible", compatible)
    (bench.chip / "npwm").write_text(str(npwm))
    if node_name != bench.node.name:
        replacement = bench.node.with_name(node_name)
        bench.node.rename(replacement)
        (bench.chip / "device" / "of_node").unlink()
        (bench.chip / "device" / "of_node").symlink_to(
            replacement, target_is_directory=True
        )
    assert hw.discover(18) is None


def test_pi5_declines_even_with_a_bcm_looking_fake_controller(bench):
    strings(bench.dt / "compatible", "raspberrypi,5-model-b", "brcm,bcm2712")
    assert hw.discover(18) is None


@pytest.mark.parametrize(
    "corruption", ["handle", "duplicate", "functions", "cells", "binding"]
)
def test_malformed_ambiguous_or_unbound_proof_is_not_fallback(bench, corruption):
    if corruption == "handle":
        cells(bench.node / "pinctrl-0", 999)
    elif corruption == "duplicate":
        duplicate = bench.gpio / "duplicate"
        duplicate.mkdir()
        cells(duplicate / "phandle", 55)
    elif corruption == "functions":
        cells(bench.group / "brcm,function", 2, 4, 2)
    elif corruption == "cells":
        (bench.group / "brcm,pins").write_bytes(b"broken")
    else:
        (bench.chip / "device" / "driver").unlink()
    with pytest.raises(hw.HardwareError):
        hw.discover(18)


def test_duplicate_header_provider_and_preexport_are_conflicts(bench):
    second = bench.sysfs / "pwmchip7"
    (second / "device").mkdir(parents=True)
    (second / "device" / "of_node").symlink_to(bench.node, target_is_directory=True)
    (second / "device" / "driver").symlink_to(bench.driver, target_is_directory=True)
    (second / "npwm").write_text("2")
    with pytest.raises(hw.HardwareError, match="Multiple"):
        hw.discover(18)
    (second / "device" / "of_node").unlink()
    (second / "device" / "driver").unlink()
    (second / "npwm").unlink()
    (second / "device").rmdir()
    second.rmdir()
    (bench.chip / "pwm0").mkdir()
    with pytest.raises(hw.HardwareError, match="pre-existing"):
        hw.discover(18)


def test_aliases_of_same_physical_pwmchip_are_not_ambiguous(bench):
    (bench.sysfs / "pwmchip7").symlink_to(bench.chip, target_is_directory=True)
    assert hw.discover(18).chip == bench.chip


def rp1_provider(bench):
    strings(bench.dt / "compatible", "raspberrypi,5-model-b", "brcm,bcm2712")
    strings(bench.gpio / "compatible", "raspberrypi,rp1-gpio")
    new_node = bench.node.with_name("pwm@98000")
    bench.node.rename(new_node)
    bench.node = new_node
    strings(new_node / "compatible", "raspberrypi,rp1-pwm")
    (bench.chip / "device" / "of_node").unlink()
    (bench.chip / "device" / "of_node").symlink_to(new_node, target_is_directory=True)
    (bench.chip / "npwm").write_text("4")
    bench.driver = bench.driver.with_name("rpi-pwm")
    bench.driver.mkdir()
    (bench.chip / "device" / "driver").unlink()
    (bench.chip / "device" / "driver").symlink_to(
        bench.driver, target_is_directory=True
    )
    clock = bench.node.parent / "clocks@18000"
    clock.mkdir()
    strings(clock / "compatible", "raspberrypi,rp1-clocks")
    cells(clock / "phandle", 77)
    cells(clock / "#clock-cells", 1)
    cells(bench.node / "clocks", 77, 17)
    cells(bench.node / "assigned-clocks", 77, 17)
    cells(bench.node / "assigned-clock-rates", 50_000_000)
    bench.clock = clock


@pytest.fixture
def rp1bench(bench, monkeypatch):
    rp1_provider(bench)
    bench.sleeps = []
    monkeypatch.setattr(hw.time, "sleep", bench.sleeps.append)
    return bench


@pytest.mark.parametrize("rp1", [False, True])
def test_mismatched_bound_driver_is_a_hard_error_not_fallback(bench, rp1):
    if rp1:
        rp1_provider(bench)
    unexpected = bench.driver.with_name("unexpected-pwm")
    unexpected.mkdir()
    (bench.chip / "device" / "driver").unlink()
    (bench.chip / "device" / "driver").symlink_to(unexpected, target_is_directory=True)
    with pytest.raises(hw.HardwareError, match="Unexpected bound PWM driver"):
        hw.discover(18)


@pytest.mark.parametrize("gpio,function", [(12, 4), (13, 4), (18, 2), (19, 2)])
@pytest.mark.parametrize("style", ["legacy", "generic", "hybrid"])
def test_configured_rp1_pin_selects_hardware_read_only(
    bench, gpio, function, style, io
):
    rp1_provider(bench)
    cells(bench.group / "brcm,pins", gpio)
    cells(bench.group / "brcm,function", function)
    if style != "legacy":
        (bench.group / "brcm,function").unlink()
        strings(bench.group / "function", "pwm0")
    if style == "generic":
        (bench.group / "brcm,pins").unlink()
        strings(bench.group / "pins", f"gpio{gpio}")
    route = hw.discover(gpio)
    assert route.controller == "rp1" and route.channel == hw._RP1_CHANNELS[gpio]
    assert route.clock_rate_hz == 50_000_000 and route.clock_node == bench.clock
    assert route.clock_id == 17
    assert io.calls == []


@pytest.mark.parametrize("gpio,alt", [(14, "alt0"), (15, "alt0"), (18, "alt3")])
def test_rp1_generic_alt_routes_are_selected(bench, gpio, alt):
    rp1_provider(bench)
    (bench.group / "brcm,pins").unlink()
    (bench.group / "brcm,function").unlink()
    strings(bench.group / "pins", f"gpio{gpio}")
    strings(bench.group / "function", alt)
    assert hw.discover(gpio).channel == hw._RP1_CHANNELS[gpio]


def test_rp1_tuple_offset_guard_and_unrouted_pins(bench):
    rp1_provider(bench)
    cells(bench.group / "brcm,pins", 18)
    cells(bench.group / "brcm,function", 2)
    with pytest.raises(hw.HardwareError, match="RP1"):
        hw.discover((0, 18))
    assert hw.discover(12) is None
    assert hw.discover(23) is None


def test_rp1_fan_only_never_blocks_unrouted_header_software(bench):
    rp1_provider(bench)
    fan = bench.node.with_name("pwm@9c000")
    bench.node.rename(fan)
    (bench.chip / "device" / "of_node").unlink()
    (bench.chip / "device" / "of_node").symlink_to(fan, target_is_directory=True)
    assert hw.discover(18) is None


def test_constructor_and_setters_above_ten_khz_have_no_sleep(bench, io, monkeypatch):
    monkeypatch.setattr(
        hw.time, "sleep", lambda _delay: pytest.fail("unexpected sleep")
    )
    output = hw.HardwarePWM(hw.discover(18), 20_000, 65535)
    assert (output.frequency, output.duty_cycle, output.period_ns) == (
        20_000,
        65535,
        50_000,
    )
    assert [(path.name, value) for path, value in io.calls] == [
        ("export", 0),
        ("period", 50_000),
        ("polarity", "normal"),
        ("duty_cycle", 50_000),
        ("enable", 1),
    ]
    io.calls.clear()
    output.configure(40_000, 32768)
    assert [(path.name, value) for path, value in io.calls] == [
        ("duty_cycle", 0),
        ("period", 25_000),
        ("duty_cycle", 12_500),
    ]
    output.configure(40_000, 0)
    output.close()
    assert output.closed and output not in hw._owners
    assert not output.route.path.exists()


@pytest.mark.parametrize("polarity", ["normal", "inversed"])
def test_fresh_zero_period_establishes_period_before_any_changed_polarity(
    bench, io, polarity
):
    io.initial["polarity"] = polarity
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)
    operations = [(path.name, value) for path, value in io.calls]
    assert operations[1] == ("period", 2_000_000)
    assert operations.index(("polarity", "normal")) > operations.index(
        ("period", 2_000_000)
    )
    output.close()


@pytest.mark.parametrize(
    "polarity,enabled", [("normal", 0), ("normal", 1), ("inversed", 0), ("inversed", 1)]
)
def test_inherited_full_duty_cleared_before_smaller_period(
    bench, io, polarity, enabled
):
    io.initial = {
        "period": 20_000_000,
        "duty_cycle": 20_000_000,
        "polarity": polarity,
        "enable": enabled,
    }
    output = hw.HardwarePWM(hw.discover(18), 500, 65535)
    operations = [(path.name, value) for path, value in io.calls]
    assert operations.index(("duty_cycle", 0)) < operations.index(("period", 2_000_000))
    if enabled:
        assert operations.index(("enable", 0)) < operations.index(("duty_cycle", 0))
    assert output._read_state() == {
        "period": 2_000_000,
        "duty_cycle": 2_000_000,
        "polarity": "normal",
        "enable": 1,
    }
    output.close()


@pytest.mark.parametrize(
    "frequency,duty,exception",
    [
        (True, 0, TypeError),
        (0, 0, ValueError),
        (-1, 0, ValueError),
        (2_000_000_001, 0, ValueError),
        (1.5, 0, TypeError),
        (500, True, TypeError),
        (500, 65536, ValueError),
    ],
)
def test_invalid_configuration_has_no_writes(bench, io, frequency, duty, exception):
    with pytest.raises(exception):
        hw.HardwarePWM(hw.discover(18), frequency, duty)
    assert io.calls == [] and hw._owners == set()


def test_export_ebusy_is_not_borrowed_or_unexported(bench, io):
    io.busy = True
    with pytest.raises(OSError) as error:
        hw.HardwarePWM(hw.discover(18), 500, 0)
    assert error.value.errno == errno.EBUSY
    assert [(path.name, value) for path, value in io.calls] == [("export", 0)]
    assert hw._owners == set()


def test_partial_update_latches_error_and_preserves_cached_request(bench, io):
    output = hw.HardwarePWM(hw.discover(18), 50, 32768)
    io.failure = lambda path, _value: path.name == "period"
    with pytest.raises(OSError, match="injected"):
        output.configure(500, 4915)
    assert (output.frequency, output.duty_cycle, output.period_ns) == (
        50,
        32768,
        20_000_000,
    )
    with pytest.raises(OSError, match="injected"):
        output.check()
    before = len(io.calls)
    with pytest.raises(OSError):
        output.configure(50, 0)
    assert len(io.calls) == before
    io.failure = None
    output.close()
    assert output.closed


@pytest.mark.parametrize("failure", ["duty_cycle", "enable", "unexport"])
def test_cleanup_failure_retains_owner_for_retry_and_does_not_hot_release(
    bench, io, failure
):
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)
    io.calls.clear()
    io.failure = lambda path, value: (
        path.name == failure and (path.name != "enable" or value == 0)
    )
    with pytest.raises(OSError):
        output.close()
    assert not output.closed and output in hw._owners and output.route.path.exists()
    if failure != "unexport":
        assert all(path.name != "unexport" for path, _value in io.calls)
    io.failure = None
    output.close()
    assert output.closed and output not in hw._owners
    before = len(io.calls)
    output.close()
    assert len(io.calls) == before


def test_low_write_failure_attempts_disable_preserving_first_error(
    bench, io, monkeypatch
):
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)
    first_error = OSError(errno.EIO, "first low failure")
    second_error = OSError(errno.EPERM, "secondary disable failure")
    original = io.write
    io.calls.clear()

    def fail(path, value):
        if path.name == "duty_cycle" and value == 0:
            io.calls.append((path, value))
            raise first_error
        if path.name == "enable" and value == 0:
            io.calls.append((path, value))
            raise second_error
        original(path, value)

    monkeypatch.setattr(hw, "_write_text", fail)
    with pytest.raises(OSError) as error:
        output.close()
    assert error.value is first_error
    assert output._cleanup_error is first_error and output._error is first_error
    assert [(path.name, value) for path, value in io.calls] == [
        ("duty_cycle", 0),
        ("enable", 0),
    ]
    assert not output.closed and output in hw._owners and output.route.path.exists()
    monkeypatch.setattr(hw, "_write_text", original)
    output.close()
    assert output.closed


def test_failed_constructor_and_failed_rollback_remain_owned_for_atexit_retry(
    bench, io
):
    io.failure = lambda path, _value: path.name in ("period", "unexport")
    with pytest.raises(OSError, match="injected"):
        hw.HardwarePWM(hw.discover(18), 500, 12345)
    assert len(hw._owners) == 1
    pending = next(iter(hw._owners))
    assert not pending.closed and pending.route.path.exists()
    assert pending.frequency is None and pending.duty_cycle is None
    io.failure = None
    hw._cleanup()
    assert pending.closed and hw._owners == set()


def test_replaced_export_is_never_written_or_unexported(bench, io):
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)
    old = output.route.path.with_name("previous-export")
    output.route.path.rename(old)
    output.route.path.mkdir()
    for name in ("period", "duty_cycle", "polarity", "enable"):
        (output.route.path / name).write_text("foreign")
    before = len(io.calls)
    with pytest.raises(hw.HardwareError, match="replaced"):
        output.check()
    with pytest.raises(hw.HardwareError, match="replaced"):
        output.close()
    assert len(io.calls) == before and not output.closed
    assert all(path.read_text() == "foreign" for path in output.route.path.iterdir())


def test_fork_child_rejects_before_lock_or_any_filesystem_action(
    bench, io, monkeypatch
):
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)

    class ForbiddenLock:
        def __enter__(self):
            pytest.fail("fork child attempted an inherited lock")

    output._lock = ForbiddenLock()
    monkeypatch.setattr(hw.os, "getpid", lambda: output._pid + 1)
    before = len(io.calls)
    for operation in (output.check, output.close, lambda: output.configure(50, 0)):
        with pytest.raises(hw.HardwareError, match="after fork"):
            operation()
    hw._cleanup()
    assert len(io.calls) == before and not output.closed


def test_independent_channels_release_only_their_own_export(bench, io):
    first = hw.HardwarePWM(hw.discover(18), 50, 4915)
    second = hw.HardwarePWM(hw.discover(13), 500, 32768)
    first.close()
    assert first.closed and second.route.path.exists()
    second.check()
    second.configure(1000, 65535)
    assert second.frequency == 1000
    second.close()
    assert not second.route.path.exists()
    assert hw._owners == set()


def test_readiness_timeout_is_bounded_and_rolls_back_own_export(bench, io, monkeypatch):
    ticks = iter(range(100))
    monkeypatch.setattr(hw.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(hw.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(hw.os, "access", lambda _path, _mode: False)
    with pytest.raises(PermissionError, match="not ready"):
        hw.HardwarePWM(hw.discover(18), 500, 0)
    assert not (bench.chip / "pwm0").exists() and hw._owners == set()


def test_nonlinux_import_and_discovery_need_no_fcntl(bench, monkeypatch):
    monkeypatch.setattr(hw.sys, "platform", "win32")
    assert hw.discover(18) is None


def test_after_fork_discards_inherited_registry_without_touching_exports(bench, io):
    output = hw.HardwarePWM(hw.discover(18), 500, 0)
    before = len(io.calls)
    hw._after_fork_child()
    assert hw._owners == set() and len(io.calls) == before
    # Simulate returning to the parent for this fake-only test's cleanup.
    output.close()


def test_os_pid_is_not_mocked_by_default():
    assert hw.os.getpid() == os.getpid()


@pytest.mark.parametrize(
    "gpio,channel", [(12, 0), (13, 1), (14, 2), (15, 3), (18, 2), (19, 3)]
)
def test_rp1_all_header_aliases_and_fresh_exports(rp1bench, io, gpio, channel):
    cells(rp1bench.group / "brcm,pins", gpio)
    (rp1bench.group / "brcm,function").unlink()
    strings(rp1bench.group / "function", "pwm0")
    route = hw.discover(gpio)
    assert route.channel == channel and route.controller == "rp1"
    output = hw.HardwarePWM(route, 20_000, 65535)
    assert io.calls[0] == (route.chip / "export", channel)
    assert output._read_state() == {
        "period": 50_000,
        "duty_cycle": 0,
        "polarity": "inversed",
        "enable": 1,
    }
    assert rp1bench.sleeps == []
    output.close()
    assert output.closed and route.path.exists() is False
    assert rp1bench.sleeps == pytest.approx([0.00110004])


@pytest.mark.parametrize("pins", [(14, 18), (15, 19)])
def test_rp1_alias_fanout_is_not_software_fallback(rp1bench, pins):
    cells(rp1bench.group / "brcm,pins", *pins)
    (rp1bench.group / "brcm,function").unlink()
    strings(rp1bench.group / "function", "pwm0")
    with pytest.raises(hw.HardwareError, match="fans out"):
        hw.discover(pins[0])


def test_rp1_legacy_uart_selectors_are_not_pwm_routes(rp1bench):
    cells(rp1bench.group / "brcm,pins", 14, 15)
    cells(rp1bench.group / "brcm,function", 4)
    assert hw.discover(14) is None and hw.discover(15) is None


@pytest.mark.parametrize(
    "problem",
    [
        "missing",
        "zero_rate",
        "rate_list",
        "duplicate",
        "wrong_id",
        "wrong_assigned",
        "provider",
        "clock_cells",
        "unavailable",
        "extra_clock",
        "parents",
        "u64",
        "zero_tick",
        "competing",
    ],
)
def test_rp1_clock_proof_failures_refuse_export(rp1bench, io, problem):
    node, clock = rp1bench.node, rp1bench.clock
    if problem == "missing":
        (node / "assigned-clock-rates").unlink()
    elif problem == "zero_rate":
        cells(node / "assigned-clock-rates", 0)
    elif problem == "rate_list":
        cells(node / "assigned-clock-rates", 50_000_000, 50_000_000)
    elif problem == "duplicate":
        other = clock.with_name("other-clock")
        other.mkdir()
        cells(other / "phandle", 77)
    elif problem == "wrong_id":
        cells(node / "clocks", 77, 18)
        cells(node / "assigned-clocks", 77, 18)
    elif problem == "wrong_assigned":
        cells(node / "assigned-clocks", 77, 18)
    elif problem == "provider":
        strings(clock / "compatible", "fixed-clock")
    elif problem == "clock_cells":
        cells(clock / "#clock-cells", 0)
    elif problem == "unavailable":
        strings(clock / "status", "disabled")
    elif problem == "extra_clock":
        cells(node / "clocks", 77, 17, 77, 18)
    elif problem == "parents":
        cells(node / "assigned-clock-parents", 0)
    elif problem == "u64":
        cells(node / "assigned-clock-rates-u64", 0, 50_000_000)
    elif problem == "zero_tick":
        cells(node / "assigned-clock-rates", 4_000_000_000)
    else:
        competing = node.with_name("competing")
        competing.mkdir()
        cells(competing / "assigned-clocks", 77, 17)
    with pytest.raises(hw.HardwareError):
        hw.discover(18)
    assert io.calls == []


def test_rp1_ignores_unrelated_clock_assignments_and_optional_name(rp1bench):
    cells(rp1bench.clock / "assigned-clocks", 77, 0, 77, 13)
    cells(rp1bench.clock / "assigned-clock-rates", 1_000_000_000, 50_000_000)
    strings(rp1bench.node / "clock-names", "anything")
    assert hw.discover(18).clock_rate_hz == 50_000_000


@pytest.mark.parametrize("frequency", [200_000_000, 1_000_000_000])
def test_rp1_zero_quantized_period_rejected_before_export(rp1bench, io, frequency):
    with pytest.raises(ValueError, match="RP1 driver clock/counts"):
        hw.HardwarePWM(hw.discover(18), frequency, 32768)
    assert io.calls == [] and hw._owners == set()


def test_rp1_bounds_mirror_integer_driver_ticks(rp1bench, monkeypatch):
    route = hw.discover(18)
    assert hw._rp1_counter_period_ns(route, 2_000_000) == 2_000_020
    with pytest.raises(ValueError):
        hw._rp1_counter_period_ns(route, 9)
    monkeypatch.setattr(hw, "RP1_MAX_PERIOD_NS", 1 << 40)
    fastest = replace(route, clock_rate_hz=1_000_000_000)
    assert hw._rp1_counter_period_ns(fastest, 0xFFFFFFFF) == 0x100000000
    with pytest.raises(ValueError):
        hw._rp1_counter_period_ns(fastest, 0x100000000)


@pytest.mark.parametrize(
    "polarity,enabled", [("normal", 0), ("normal", 1), ("inversed", 0), ("inversed", 1)]
)
def test_rp1_constructor_prepares_valid_normal_zero_from_stale_full(
    rp1bench, io, polarity, enabled
):
    io.initial = {
        "period": 20_000_000,
        "duty_cycle": 20_000_000,
        "polarity": polarity,
        "enable": enabled,
    }
    output = hw.HardwarePWM(hw.discover(18), 500, 65535)
    operations = [(path.name, value) for path, value in io.calls]
    assert operations[:4] == [
        ("export", 2),
        ("enable", 0),
        ("duty_cycle", 0),
        ("period", 2_000_000),
    ]
    assert operations[4:] == [
        ("polarity", "normal"),
        ("duty_cycle", 0),
        ("polarity", "inversed"),
        ("duty_cycle", 0),
        ("enable", 1),
    ]
    assert rp1bench.sleeps == []
    output.close()
    assert rp1bench.sleeps == pytest.approx([0.04100004])


def test_rp1_fresh_inverse_zero_period_sets_valid_period_first(rp1bench, io):
    io.initial["polarity"] = "inversed"
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)
    operations = [(path.name, value) for path, value in io.calls]
    assert operations[:3] == [("export", 2), ("enable", 0), ("period", 2_000_000)]
    assert operations.index(("polarity", "normal")) > operations.index(
        ("period", 2_000_000)
    )
    output.close()


def test_rp1_fast_normal_high_half_low_frequency_sequence(rp1bench, io):
    output = hw.HardwarePWM(hw.discover(18), 50, 4915)
    io.calls.clear()
    output.configure(50, 65535)
    assert [(path.name, value) for path, value in io.calls] == [
        ("enable", 0),
        ("duty_cycle", 0),
        ("period", 20_000_000),
        ("polarity", "inversed"),
        ("duty_cycle", 0),
        ("enable", 1),
    ]
    io.calls.clear()
    output.configure(50, 32768)
    assert [(path.name, value) for path, value in io.calls] == [
        ("enable", 0),
        ("duty_cycle", 0),
        ("period", 20_000_000),
        ("polarity", "normal"),
        ("duty_cycle", 10_000_152),
        ("enable", 1),
    ]
    io.calls.clear()
    output.configure(50, 0)
    assert [(path.name, value) for path, value in io.calls] == [("duty_cycle", 0)]
    io.calls.clear()
    output.configure(500, 32768)
    assert [(path.name, value) for path, value in io.calls] == [
        ("enable", 0),
        ("duty_cycle", 0),
        ("period", 2_000_000),
        ("polarity", "normal"),
        ("duty_cycle", 1_000_015),
        ("enable", 1),
    ]
    assert rp1bench.sleeps == []
    output.close()
    assert rp1bench.sleeps == pytest.approx([0.04100004])


def test_rp1_period_shrink_zeros_larger_duty_first(rp1bench, io):
    output = hw.HardwarePWM(hw.discover(18), 50, 60000)
    io.calls.clear()
    output.configure(500, 4915)
    operations = [(path.name, value) for path, value in io.calls]
    assert operations.index(("duty_cycle", 0)) < operations.index(("period", 2_000_000))
    assert operations[0] == ("enable", 0)
    output.close()


@pytest.mark.parametrize("failure", ["period", "polarity", "duty_cycle", "enable"])
def test_rp1_partial_update_is_sticky_without_hot_fallback(rp1bench, io, failure):
    output = hw.HardwarePWM(hw.discover(18), 50, 32768)
    io.failure = lambda path, value: (
        path.name == failure and (failure != "enable" or value == 1)
    )
    with pytest.raises(OSError) as primary:
        output.configure(500, 65535)
    assert (
        output.frequency,
        output.duty_cycle,
        output.period_ns,
        output._polarity,
    ) == (50, 32768, 20_000_000, "normal")
    before = len(io.calls)
    with pytest.raises(OSError) as sticky:
        output.configure(50, 0)
    assert sticky.value is primary.value and len(io.calls) == before
    io.failure = None
    output.close()
    assert output.closed


def test_rp1_high_cleanup_restores_normal_zero_before_guard_and_disable(
    rp1bench, io, monkeypatch
):
    output = hw.HardwarePWM(hw.discover(18), 500, 65535)
    io.calls.clear()
    observed = []
    monkeypatch.setattr(
        hw.time, "sleep", lambda delay: observed.append((delay, output._read_state()))
    )
    output.close()
    assert observed == [
        (
            pytest.approx(0.00500004),
            {"period": 2_000_000, "duty_cycle": 0, "polarity": "normal", "enable": 1},
        )
    ]
    assert [(path.name, value) for path, value in io.calls] == [
        ("enable", 0),
        ("polarity", "normal"),
        ("duty_cycle", 0),
        ("enable", 1),
        ("enable", 0),
        ("unexport", 2),
    ]
    assert output.closed and output not in hw._owners


def test_rp1_guard_failure_retains_owner_for_deinit_retry(rp1bench, io, monkeypatch):
    output = hw.HardwarePWM(hw.discover(18), 500, 65535)
    failure = OSError("injected cleanup guard failure")

    def fail(_delay):
        raise failure

    monkeypatch.setattr(hw.time, "sleep", fail)
    io.calls.clear()
    with pytest.raises(OSError) as error:
        output.close()
    assert error.value is failure and output._cleanup_error is failure
    assert not output.closed and output in hw._owners
    assert all(path.name != "unexport" for path, _value in io.calls)
    assert io.calls[-1] == (output.route.path / "enable", 0)
    monkeypatch.setattr(hw.time, "sleep", rp1bench.sleeps.append)
    output.close()
    assert output.closed and output not in hw._owners


def test_rp1_unknown_zero_period_rollback_recovers_then_retries(rp1bench, io):
    io.failure = lambda path, _value: path.name == "period"
    with pytest.raises(OSError):
        hw.HardwarePWM(hw.discover(18), 500, 65535)
    pending = next(iter(hw._owners))
    assert not pending.closed and pending.frequency is None
    assert rp1bench.sleeps == []
    io.failure = None
    pending.close()
    assert pending.closed and rp1bench.sleeps == pytest.approx([0.00500004])


def test_rp1_fork_child_does_no_lock_io_or_sleep(rp1bench, io, monkeypatch):
    output = hw.HardwarePWM(hw.discover(18), 500, 65535)

    class ForbiddenLock:
        def __enter__(self):
            pytest.fail("fork child attempted inherited lock")

    output._lock = ForbiddenLock()
    monkeypatch.setattr(hw.os, "getpid", lambda: output._pid + 1)
    before = len(io.calls)
    for operation in (output.check, output.close, lambda: output.configure(50, 0)):
        with pytest.raises(hw.HardwareError, match="after fork"):
            operation()
    hw._cleanup()
    assert len(io.calls) == before and rp1bench.sleeps == []


def test_rp1_independent_release_preserves_sibling_high(rp1bench, io):
    first = hw.HardwarePWM(hw.discover(18), 50, 4915)
    second = hw.HardwarePWM(hw.discover(13), 500, 65535)
    first.close()
    assert second._read_state() == {
        "period": 2_000_000,
        "duty_cycle": 0,
        "polarity": "inversed",
        "enable": 1,
    }
    second.check()
    second.close()
    assert first.closed and second.closed and hw._owners == set()


def test_rp1_existing_export_and_kernel_consumer_are_hard_conflicts(rp1bench, io):
    output = hw.HardwarePWM(hw.discover(18), 50, 4915)
    before = len(io.calls)
    with pytest.raises(hw.HardwareError, match="pre-existing"):
        hw.discover(18)
    assert len(io.calls) == before
    output.close()
    io.calls.clear()
    io.busy = True
    with pytest.raises(OSError) as error:
        hw.HardwarePWM(hw.discover(18), 500, 0)
    assert error.value.errno == errno.EBUSY
    assert [(path.name, value) for path, value in io.calls] == [("export", 2)]
    assert hw._owners == set()


def test_rp1_invalid_setter_has_no_io_and_does_not_poison_owner(rp1bench, io):
    output = hw.HardwarePWM(hw.discover(18), 20_000, 32768)
    before = len(io.calls)
    with pytest.raises(ValueError, match="RP1 driver clock/counts"):
        output.configure(1_000_000_000, 32768)
    assert len(io.calls) == before and output.frequency == 20_000
    output.check()
    output.close()


def test_rp1_low_write_failure_still_disables_without_releasing(rp1bench, io):
    output = hw.HardwarePWM(hw.discover(18), 500, 65535)
    io.calls.clear()
    io.failure = lambda path, value: path.name == "duty_cycle" and value == 0
    with pytest.raises(OSError) as primary:
        output.close()
    assert output._cleanup_error is primary.value and output._error is primary.value
    assert [(path.name, value) for path, value in io.calls] == [
        ("enable", 0),
        ("polarity", "normal"),
        ("duty_cycle", 0),
        ("enable", 0),
    ]
    assert not output.closed and output in hw._owners and rp1bench.sleeps == []
    io.failure = None
    output.close()
    assert output.closed


def test_rp1_cleanup_guard_cached_readback_failure_retains_export(
    rp1bench, io, monkeypatch
):
    output = hw.HardwarePWM(hw.discover(18), 500, 32768)
    original = output._verify
    checks = []
    failure = hw.HardwareError("injected post-guard readback failure")

    def verify(period, duty, enable, polarity="normal"):
        checks.append((period, duty, enable))
        if len(checks) == 2:
            raise failure
        original(period, duty, enable, polarity)

    monkeypatch.setattr(output, "_verify", verify)
    io.calls.clear()
    with pytest.raises(hw.HardwareError) as error:
        output.close()
    assert error.value is failure and not output.closed and output in hw._owners
    assert all(path.name != "unexport" for path, _value in io.calls)
    assert io.calls[-1] == (output.route.path / "enable", 0)
    monkeypatch.setattr(output, "_verify", original)
    output.close()
    assert output.closed


def test_rp1_unsupported_inherited_period_is_not_unbounded_cleanup(rp1bench, io):
    io.initial = {
        "period": 2_000_000_000,
        "duty_cycle": 0,
        "polarity": "normal",
        "enable": 1,
    }
    with pytest.raises(ValueError, match="RP1 driver clock/counts"):
        hw.HardwarePWM(hw.discover(18), 500, 0)
    pending = next(iter(hw._owners))
    assert not pending.closed and pending.route.path.exists()
    assert [(path.name, value) for path, value in io.calls] == [
        ("export", 2),
        ("enable", 0),
    ]
    assert rp1bench.sleeps == []
