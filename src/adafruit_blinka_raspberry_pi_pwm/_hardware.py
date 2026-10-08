# SPDX-License-Identifier: MIT
"""Bound, preconfigured BCM/RP1 header PWM, without changing overlays or pinmux.

Sysfs exports are global state, not crash-safe file-descriptor leases. The
captured directory identity detects replacement exports, but cannot exclude
noncooperating sysfs writers. Readbacks describe cached requests, not measured
electrical state. Scalar configuration updates may produce transient glitches.
RP1 HIGH uses inverse-zero, not the driver's notched normal-full duty. Its
clock metadata is an OF request, not a measured or guaranteed runtime rate.
PIO, software PWM providers, fan and audio controllers are not supported here.
"""

import atexit
import operator
import os
import struct
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ._software import _pin_id

SYSFS_PWM = Path("/sys/class/pwm")
DEVICE_TREE = Path("/sys/firmware/devicetree/base")
EXPORT_READY_SECONDS = 1.0
RP1_CLEANUP_GUARD_SECONDS = 0.001
RP1_MAX_PERIOD_NS = 1_000_000_000  # The public minimum frequency is 1 Hz.
_CHANNELS = {12: 0, 13: 1, 18: 0, 19: 1}
_RP1_CHANNELS = {12: 0, 13: 1, 14: 2, 15: 3, 18: 2, 19: 3}
_RP1_PINS = {12: "alt0", 13: "alt0", 14: "alt0", 15: "alt0", 18: "alt3", 19: "alt3"}
_RP1_LEGACY = {12: 4, 13: 4, 18: 2, 19: 2}
# Include non-header aliases when checking for unintended electrical fanout.
_MUX = {
    12: (0, 4),
    18: (0, 2),
    40: (0, 4),
    52: (0, 5),
    13: (1, 4),
    19: (1, 2),
    41: (1, 4),
    45: (1, 4),
    53: (1, 5),
}
_GENERIC_FUNCTIONS = {
    "gpio_in": 0,
    "gpio_out": 1,
    "alt5": 2,
    "alt4": 3,
    "alt0": 4,
    "alt1": 5,
    "alt2": 6,
    "alt3": 7,
}
_GPIO_COMPATIBLE = {"brcm,bcm2835-gpio", "brcm,bcm2711-gpio"}
_SOC_COMPATIBLE = {"brcm,bcm2835", "brcm,bcm2836", "brcm,bcm2837", "brcm,bcm2711"}
_owners = set()
_owners_lock = threading.RLock()


class HardwareError(RuntimeError):
    """A configured hardware route could not safely be used."""


@dataclass(frozen=True)
class Route:
    """A default pinctrl route and, for RP1, requested (not measured) clock."""

    gpio: int
    chip: Path
    of_node: Path
    channel: int
    gpio_node: Path
    pinctrl_nodes: tuple
    controller: str = "bcm"
    clock_rate_hz: int = None
    clock_node: Path = None
    clock_id: int = None

    @property
    def path(self):
        return self.chip / f"pwm{self.channel}"


def _strings(path):
    data = path.read_bytes()
    try:
        if not data or not data.endswith(b"\0"):
            raise ValueError("unterminated string property")
        values = data[:-1].decode("ascii").split("\0")
        if any(not value for value in values):
            raise ValueError("empty string property")
        return values
    except (UnicodeError, ValueError) as exc:
        raise HardwareError(f"Malformed OF string property: {path}") from exc


def _cells(path):
    data = path.read_bytes()
    if not data or len(data) % 4:
        raise HardwareError(f"Malformed big-endian OF cells: {path}")
    return struct.unpack(">" + "I" * (len(data) // 4), data)


def _phandle_nodes(root, handles):
    matches = {handle: set() for handle in handles}
    for name in ("phandle", "linux,phandle"):
        for prop in root.rglob(name):
            values = _cells(prop)
            if len(values) != 1 or values[0] == 0:
                raise HardwareError(f"Malformed OF phandle: {prop}")
            if values[0] in matches:
                matches[values[0]].add(prop.parent)
    if any(len(nodes) != 1 for nodes in matches.values()):
        raise HardwareError("Missing or ambiguous OF phandle")
    nodes = tuple(next(iter(matches[handle])) for handle in handles)
    for node, handle in zip(nodes, handles):
        for name in ("phandle", "linux,phandle"):
            prop = node / name
            if prop.exists() and _cells(prop) != (handle,):
                raise HardwareError("Inconsistent OF phandle aliases")
    return nodes


def _gpio_parent(node, root, rp1=False):
    approved = {"raspberrypi,rp1-gpio"} if rp1 else _GPIO_COMPATIBLE
    for parent in (node, *node.parents):
        if parent == root.parent:
            break
        compatible = parent / "compatible"
        if compatible.exists() and approved.intersection(_strings(compatible)):
            return parent
    raise HardwareError(
        f"Default pinctrl group is not on a BCM GPIO controller: {node}"
    )


def _pin_functions(node, rp1=False):
    """Decode a single mux group; pinconf-only groups do not establish a route."""
    legacy = node / "brcm,pins"
    generic = node / "pins"
    if (node / "groups").exists():
        if generic.exists():
            raise HardwareError(f"Ambiguous generic pins/groups: {node}")
        generic = node / "groups"
    if legacy.exists() and generic.exists():
        raise HardwareError(f"Ambiguous legacy/generic pinctrl properties: {node}")
    if legacy.exists():
        pins = _cells(legacy)
        function = node / "brcm,function"
        if not function.exists():
            if rp1 and (node / "function").exists():
                functions = _strings(node / "function")
                if len(functions) != 1:
                    raise HardwareError(f"Malformed RP1 function: {node}")
                return tuple((pin, functions[0]) for pin in pins)
            return ()
        functions = _cells(function)
        if len(functions) == 1:
            functions *= len(pins)
        if len(functions) != len(pins) or any(value > 7 for value in functions):
            raise HardwareError(f"Malformed BCM pinctrl function list: {node}")
        return tuple(zip(pins, functions))
    if generic.exists():
        names = _strings(generic)
        try:
            if any(
                not name.startswith("gpio") or not name[4:].isdigit() for name in names
            ):
                raise ValueError("unexpected pin name")
            pins = [int(name[4:]) for name in names]
        except ValueError as exc:
            raise HardwareError(f"Malformed generic BCM pin names: {node}") from exc
        function = node / "function"
        if not function.exists():
            return ()
        functions = _strings(function)
        if len(functions) != 1:
            raise HardwareError(f"Unknown generic BCM mux function: {node}")
        if rp1:
            return tuple((pin, functions[0]) for pin in pins)
        if functions[0] not in _GENERIC_FUNCTIONS:
            raise HardwareError(f"Unknown generic BCM mux function: {node}")
        return tuple((pin, _GENERIC_FUNCTIONS[functions[0]]) for pin in pins)
    if (node / "brcm,function").exists() or (node / "function").exists():
        raise HardwareError(f"Mux function without pins: {node}")
    return ()


def _default_functions(node, root, rp1=False):
    names_path = node / "pinctrl-names"
    if not names_path.exists():
        return None
    names = _strings(names_path)
    if names.count("default") != 1:
        raise HardwareError("PWM provider must have one default pinctrl state")
    prop = node / f"pinctrl-{names.index('default')}"
    handles = _cells(prop)
    if 0 in handles or len(set(handles)) != len(handles):
        raise HardwareError("Malformed default pinctrl handle list")
    groups = _phandle_nodes(root, handles)
    routes = {}
    gpio_nodes = set()
    for group in groups:
        controller = _gpio_parent(group, root, rp1)
        if controller.parent != node.parent:
            raise HardwareError(
                "PWM and default GPIO pinctrl are not on the same BCM bus"
            )
        gpio_nodes.add(controller)
        children = tuple(
            child
            for child in group.iterdir()
            if child.is_dir()
            and (
                not (child / "status").exists()
                or _strings(child / "status") in (["okay"], ["ok"])
            )
        )
        # Generic mappings cover this node and available immediate children only.
        # BCM generic maps take precedence over legacy maps; reject mixed forms
        # instead of claiming a legacy route the kernel actually ignores.
        nodes = (group, *children)
        generic = any(
            (child / name).exists() for child in nodes for name in ("pins", "groups")
        )
        legacy = any((child / "brcm,pins").exists() for child in nodes)
        if generic and legacy:
            raise HardwareError("Mixed generic/legacy default pinctrl interpretation")
        if not generic:
            if any((child / "brcm,pins").exists() for child in children):
                raise HardwareError(
                    "Legacy mux children do not establish an active route"
                )
            nodes = (group,)
        for child in nodes:
            for pin, function in _pin_functions(child, rp1):
                if pin in routes:
                    raise HardwareError(
                        f"Duplicate or conflicting default mux for GPIO{pin}"
                    )
                routes[pin] = function
    if len(gpio_nodes) != 1:
        raise HardwareError("Ambiguous default BCM GPIO controller")
    return routes, next(iter(gpio_nodes)), groups


def _rp1_mux(pin, function):
    return pin in _RP1_CHANNELS and (
        function in ("pwm0", _RP1_PINS[pin])
        or (pin in _RP1_LEGACY and function == _RP1_LEGACY[pin])
    )


def _clock_references(path, root):
    """Parse OF clock specifiers, including zero assignment placeholders."""
    values, references, offset = _cells(path), [], 0
    while offset < len(values):
        handle = values[offset]
        offset += 1
        if handle == 0:
            references.append(None)
            continue
        provider = _phandle_nodes(root, (handle,))[0]
        count = _cells(provider / "#clock-cells")
        if len(count) != 1 or count[0] > len(values) - offset:
            raise HardwareError(f"Malformed clock specifier: {path}")
        references.append((provider, values[offset : offset + count[0]]))
        offset += count[0]
    return tuple(references)


def _rp1_clock(node, root):
    """Accept the explicit header PWM0 clock assignment only, not a rate guess.

    CCF assignments can fail or be changed by another consumer after discovery.
    This proves the DT request's identity, not its successful/current frequency.
    """
    try:
        clocks = _clock_references(node / "clocks", root)
        assigned = _clock_references(node / "assigned-clocks", root)
        rates = _cells(node / "assigned-clock-rates")
        if any(
            (node / name).exists()
            for name in (
                "assigned-clock-parents",
                "assigned-clock-rates-u64",
                "assigned-clock-sscs",
            )
        ):
            raise HardwareError("Unsupported RP1 clock assignment metadata")
        if len(clocks) != 1 or clocks[0] is None or assigned != clocks:
            raise HardwareError("RP1 needs one matching assigned PWM0 clock")
        provider, arguments = clocks[0]
        if (
            provider.name != "clocks@18000"
            or provider.parent != node.parent
            or "raspberrypi,rp1-clocks" not in _strings(provider / "compatible")
            or _cells(provider / "#clock-cells") != (1,)
            or arguments != (17,)  # dt-bindings/clock/rp1.h: RP1_CLK_PWM0.
            or len(rates) != 1
            or rates[0] == 0
        ):
            raise HardwareError("Unproven RP1 PWM0 clock identity or assigned rate")
        status = provider / "status"
        if status.exists() and _strings(status) not in (["okay"], ["ok"]):
            raise HardwareError("RP1 clock provider is not available")
        for prop in root.rglob("assigned-clocks"):
            if prop.parent != node and clocks[0] in _clock_references(prop, root):
                raise HardwareError("Ambiguous RP1 PWM0 clock assignments")
        # Match the driver's integer nanosecond tick calculation. Too high an
        # assigned rate would make its divisor zero, not a usable PWM clock.
        if (1_000_000_000 + rates[0] // 2) // rates[0] == 0:
            raise HardwareError("RP1 assigned clock has no positive driver tick")
        return rates[0], provider, arguments[0]
    except FileNotFoundError as exc:
        raise HardwareError("Missing RP1 assigned clock proof") from exc


def _default_route(chip, node, gpio, root, rp1=False):
    configured = _default_functions(node, root, rp1)
    if configured is None:
        return None
    routes, gpio_node, groups = configured
    if rp1:
        if not _rp1_mux(gpio, routes.get(gpio)):
            return None
        channel = _RP1_CHANNELS[gpio]
        aliases = [
            pin
            for pin, selected in routes.items()
            if _rp1_mux(pin, selected) and _RP1_CHANNELS[pin] == channel
        ]
    else:
        channel, function = _MUX[gpio]
        if routes.get(gpio) != function:
            return None
        aliases = [
            pin
            for pin, selected in routes.items()
            if _MUX.get(pin) == (channel, selected)
        ]
    if aliases != [gpio]:
        raise HardwareError(
            f"PWM channel {channel} fans out to multiple pins: {aliases}"
        )
    if rp1:
        rate, clock_node, clock_id = _rp1_clock(node, root)
        return Route(
            gpio,
            chip,
            node,
            channel,
            gpio_node,
            groups,
            "rp1",
            rate,
            clock_node,
            clock_id,
        )
    return Route(gpio, chip, node, channel, gpio_node, groups)


def discover(pin):
    """Return a configured header route or None; errors never mean fallback.

    Explicit gpiochip tuples cannot prove header identity and are declined for
    BCM. A configured RP1 tuple is rejected, not allowed to remux in software.
    Only read the live OF tree and sysfs; no GPIO requests or pinmux changes.
    """
    explicit, gpio = _pin_id(pin)
    if sys.platform != "linux" or gpio not in _CHANNELS.keys() | _RP1_PINS.keys():
        return None
    try:
        compatible = _strings(DEVICE_TREE / "compatible")
    except FileNotFoundError:
        return None
    bcm = bool(_SOC_COMPATIBLE.intersection(compatible))
    rp1 = "brcm,bcm2712" in compatible
    if not (bcm or rp1) or not any(
        value.startswith("raspberrypi,") for value in compatible
    ):
        return None
    root = DEVICE_TREE.resolve(strict=True)
    candidates = {"bcm": [], "rp1": []}
    seen = set()
    for alias in sorted(SYSFS_PWM.glob("pwmchip*")):
        chip = alias.resolve(strict=True)
        if chip in seen:
            continue
        seen.add(chip)
        link = chip / "device" / "of_node"
        if not link.exists():
            continue
        node = link.resolve(strict=True)
        if node.name not in ("pwm@7e20c000", "pwm@98000"):
            continue
        provider = _strings(node / "compatible")
        if (
            bcm
            and explicit is None
            and gpio in _CHANNELS
            and node.name == "pwm@7e20c000"
            and "brcm,bcm2835-pwm" in provider
        ):
            kind, channels = "bcm", 2
        elif rp1 and node.name == "pwm@98000" and "raspberrypi,rp1-pwm" in provider:
            kind, channels = "rp1", 4
        else:
            continue
        try:
            node.relative_to(root)
        except ValueError as exc:
            raise HardwareError("PWM OF node is outside the live device tree") from exc
        if not (chip / "device" / "driver").exists():
            raise HardwareError("Header PWM provider is not bound to a driver")
        driver = (chip / "device" / "driver").resolve(strict=True).name
        expected_driver = "bcm2835-pwm" if kind == "bcm" else "rpi-pwm"
        if driver != expected_driver:
            raise HardwareError(
                f"Unexpected bound PWM driver {driver!r}; expected {expected_driver!r}"
            )
        status = node / "status"
        if status.exists() and _strings(status) not in (["okay"], ["ok"]):
            raise HardwareError("Bound header PWM provider has inconsistent OF status")
        if int((chip / "npwm").read_text()) != channels:
            raise HardwareError("Unexpected header PWM channel count")
        candidates[kind].append((chip, node))
    if any(len(found) > 1 for found in candidates.values()):
        raise HardwareError("Multiple header PWM providers")
    if candidates["rp1"]:
        route = _default_route(*candidates["rp1"][0], gpio, root, rp1=True)
        if route is not None and explicit is not None:
            raise HardwareError("Unproven RP1 gpiochip tuple; refusing software remux")
    elif candidates["bcm"]:
        route = _default_route(*candidates["bcm"][0], gpio, root)
    else:
        return None
    if route is not None and route.path.exists():
        raise HardwareError(f"Refusing pre-existing PWM export: {route.path}")
    return route


def _integer(value, name, minimum, maximum=None):
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    value = operator.index(value)
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"Invalid {name}: {value}")
    return value


def _state(frequency, duty):
    frequency = _integer(frequency, "frequency", 1)
    duty = _integer(duty, "duty_cycle", 0, 65535)
    period = (1_000_000_000 + frequency // 2) // frequency
    if period <= 0:
        raise ValueError(
            "Frequency cannot be represented by a positive nanosecond period"
        )
    return frequency, duty, period, period * duty // 65535


def _rp1_counter_period_ns(route, period, duty_ns=0):
    """Validate inferred driver counts and estimate inclusive-counter period."""
    rate = _integer(route.clock_rate_hz, "RP1 assigned clock rate", 1)
    tick = (1_000_000_000 + rate // 2) // rate
    if tick <= 0:
        raise ValueError("RP1 assigned clock has no positive driver tick")
    ticks = (period + tick // 2) // tick
    duty_ticks = (duty_ns + tick // 2) // tick
    if (
        not 0 < period <= RP1_MAX_PERIOD_NS
        or not 1 <= ticks <= 0xFFFFFFFF
        or not 0 <= duty_ns <= period
        or not 0 <= duty_ticks <= ticks
    ):
        raise ValueError(
            "PWM state cannot be represented by the RP1 driver clock/counts"
        )
    return ((ticks + 1) * 1_000_000_000 + rate - 1) // rate


def _write_text(path, value):
    path.write_text(str(value) + "\n", encoding="ascii")


class HardwarePWM:
    """Independent fresh-export owner; failed cleanup remains retryable."""

    def __init__(self, route, frequency, duty):
        self._pid = os.getpid()
        self._lock = threading.RLock()
        self.route = route
        self.closed = False
        self._owned = False
        self._identity = None
        self._error = None
        self._cleanup_error = None
        frequency, duty, period, duty_ns = _state(frequency, duty)
        self.frequency = self.duty_cycle = self.period_ns = None
        self._polarity = None
        self._cleanup_period_ns = 0
        self._initial_period_ns = period
        if sys.platform != "linux":
            raise HardwareError("Kernel PWM requires Linux")
        if (
            not isinstance(route, Route)
            or route.controller not in ("bcm", "rp1")
            or (
                route.controller == "bcm"
                and (
                    route.gpio not in _CHANNELS
                    or route.channel != _CHANNELS[route.gpio]
                    or route.of_node.name != "pwm@7e20c000"
                )
            )
            or (
                route.controller == "rp1"
                and (
                    route.gpio not in _RP1_CHANNELS
                    or route.channel != _RP1_CHANNELS[route.gpio]
                    or route.of_node.name != "pwm@98000"
                    or route.clock_node is None
                    or route.clock_node.name != "clocks@18000"
                    or route.clock_node.parent != route.of_node.parent
                    or route.clock_id != 17
                )
            )
        ):
            raise HardwareError("Only an approved BCM/RP1 header route may be exported")
        polarity = "normal"
        if route.controller == "rp1":
            if duty == 65535:
                duty_ns, polarity = 0, "inversed"
            self._record_rp1_period(period, duty_ns)
        if route.path.exists():
            raise HardwareError(f"Refusing pre-existing PWM export: {route.path}")
        with _owners_lock:
            _owners.add(self)
        try:
            _write_text(route.chip / "export", route.channel)
            self._owned = True
            info = route.path.stat()
            self._identity = (info.st_dev, info.st_ino)
            deadline = time.monotonic() + EXPORT_READY_SECONDS
            attributes = [
                route.path / name
                for name in ("period", "duty_cycle", "polarity", "enable")
            ]
            while not all(
                path.exists() and os.access(path, os.R_OK | os.W_OK)
                for path in attributes
            ):
                self._assert_identity()
                if time.monotonic() >= deadline:
                    raise PermissionError(f"Export attributes not ready: {route.path}")
                time.sleep(0.005)
            current = self._read_state()
            if (
                current["period"] < 0
                or current["duty_cycle"] < 0
                or current["duty_cycle"] > current["period"]
                or current["enable"] not in (0, 1)
                or current["polarity"] not in ("normal", "inversed")
            ):
                raise HardwareError("Invalid cached state on fresh export")
            if route.controller == "rp1" and current["period"] > 0:
                self._record_rp1_period(current["period"], current["duty_cycle"])
            if current["enable"] or route.controller == "rp1":
                self._write("enable", 0)
                if self._read_state()["enable"] != 0:
                    raise HardwareError("Could not disable newly exported channel")
            if current["period"] > 0 and current["duty_cycle"] > 0:
                self._write("duty_cycle", 0)
            # Fresh zero-period states must establish a valid period before
            # changing polarity/duty. Export can also retain an earlier duty;
            # clear that at its old positive period before any period shrink.
            self._write("period", period)
            self._write("polarity", "normal")
            if route.controller == "rp1":
                self._write("duty_cycle", 0)
                self._verify(period, 0, 0)
                self._write("polarity", polarity)
            self._write("duty_cycle", duty_ns)
            if route.controller == "rp1":
                self._verify(period, duty_ns, 0, polarity)
            self._write("enable", 1)
            self._verify(period, duty_ns, 1, polarity)
            self.frequency, self.duty_cycle, self.period_ns = frequency, duty, period
            self._polarity = polarity
        except BaseException as exc:
            self._error = exc
            try:
                self.close()
            except BaseException as cleanup_exc:
                self._cleanup_error = cleanup_exc
                if hasattr(exc, "add_note"):
                    exc.add_note(
                        f"PWM cleanup failed; ownership retained: {cleanup_exc}"
                    )
            raise

    def _pid_guard(self):
        if self._pid != os.getpid():
            raise HardwareError(
                "PWM objects cannot be used after fork; create them in the child"
            )

    def _record_rp1_period(self, period, duty_ns=0):
        inferred = _rp1_counter_period_ns(self.route, period, duty_ns)
        self._cleanup_period_ns = max(self._cleanup_period_ns, period, inferred)

    def _assert_identity(self):
        if not self._owned or self._identity is None:
            raise HardwareError("PWM export ownership is not established")
        try:
            info = self.route.path.stat()
        except OSError as exc:
            raise HardwareError(
                "Owned PWM export disappeared; refusing further writes"
            ) from exc
        if (info.st_dev, info.st_ino) != self._identity:
            raise HardwareError(
                "PWM export was replaced; refusing to touch its new owner"
            )

    def _write(self, name, value):
        self._assert_identity()
        _write_text(self.route.path / name, value)

    def _read_state(self):
        result = {}
        for name in ("period", "duty_cycle", "polarity", "enable"):
            self._assert_identity()
            value = (self.route.path / name).read_text(encoding="ascii").strip()
            result[name] = value if name == "polarity" else int(value)
        return result

    def _verify(self, period, duty_ns, enable, polarity="normal"):
        expected = {
            "period": period,
            "duty_cycle": duty_ns,
            "polarity": polarity,
            "enable": enable,
        }
        actual = self._read_state()
        if actual != expected:
            raise HardwareError(
                f"Unexpected cached PWM state: {actual}, expected {expected}"
            )

    def _check_locked(self):
        if self.closed:
            raise ValueError("Object has been deinitialized")
        if self._error is not None:
            raise self._error
        try:
            self._assert_identity()
        except BaseException as exc:
            self._error = exc
            raise

    def check(self):
        self._pid_guard()
        with self._lock:
            self._check_locked()

    def configure(self, frequency, duty):
        self._pid_guard()
        frequency, duty, period, duty_ns = _state(frequency, duty)
        polarity = "normal"
        if self.route.controller == "rp1":
            if duty == 65535:
                duty_ns, polarity = 0, "inversed"
            # Validate before any sysfs action; no silent/hot software fallback.
            _rp1_counter_period_ns(self.route, period, duty_ns)
        with self._lock:
            self._check_locked()
            try:
                if self.route.controller == "rp1" and (
                    period != self.period_ns or polarity != self._polarity
                ):
                    # Fast scalar transition: disabled updates may truncate the
                    # outgoing pulse. There is deliberately no setter wait.
                    self._write("enable", 0)
                    self._write("duty_cycle", 0)
                    self._record_rp1_period(period, duty_ns)
                    self._write("period", period)
                    self._write("polarity", polarity)
                    self._write("duty_cycle", duty_ns)
                    self._verify(period, duty_ns, 0, polarity)
                    self._write("enable", 1)
                elif period != self.period_ns:
                    # Zero before shrinking even while enabled; scalar writes are
                    # not an atomic state update and may introduce a quiet gap.
                    self._write("duty_cycle", 0)
                    self._write("period", period)
                    self._write("duty_cycle", duty_ns)
                else:
                    self._write("duty_cycle", duty_ns)
                self._verify(period, duty_ns, 1, polarity)
            except BaseException as exc:
                self._error = exc
                raise
            self.frequency, self.duty_cycle, self.period_ns = frequency, duty, period
            self._polarity = polarity

    def close(self):
        self._pid_guard()
        with self._lock:
            if self.closed:
                return
            if not self._owned:
                self.closed = True
            else:
                try:
                    current = self._read_state()
                    period = current["period"]
                    if self.route.controller == "rp1" and period > 0:
                        self._record_rp1_period(period, current["duty_cycle"])
                    if period <= 0:
                        period = max(self._initial_period_ns, current["duty_cycle"])
                        if self.route.controller == "rp1":
                            self._record_rp1_period(period)
                        self._write("period", period)
                    if current["polarity"] != "normal":
                        self._write("enable", 0)
                        self._write("polarity", "normal")
                    self._write("duty_cycle", 0)
                    self._write("enable", 1)
                    self._verify(period, 0, 1)
                    if self.route.controller == "rp1":
                        # A qualification-pending, period-derived guard, NOT a
                        # latch acknowledgment/electrical proof. Covers prior
                        # accepted or ambiguous updates and inclusive counting.
                        time.sleep(
                            2 * self._cleanup_period_ns / 1_000_000_000
                            + RP1_CLEANUP_GUARD_SECONDS
                        )
                        self._verify(period, 0, 1)
                    self._write("enable", 0)
                    self._verify(period, 0, 0)
                    self._assert_identity()
                    _write_text(self.route.chip / "unexport", self.route.channel)
                    if self.route.path.exists():
                        raise HardwareError("PWM export remains present after unexport")
                    self._owned = False
                    self.closed = True
                except BaseException as exc:
                    # Best effort to stop a prior active waveform even if low
                    # preparation failed. Identity checks still protect a foreign
                    # replacement, and failure never permits unsafe unexport.
                    try:
                        self._write("enable", 0)
                    except BaseException as disable_exc:
                        if hasattr(exc, "add_note"):
                            exc.add_note(f"Final disable also failed: {disable_exc}")
                    self._cleanup_error = exc
                    if self._error is None:
                        self._error = exc
                    # Never unexport after an unconfirmed low or disable.
                    raise
            with _owners_lock:
                _owners.discard(self)


def _cleanup():
    # The registry also retains failed constructors and discarded wrappers.
    for owner in list(_owners):
        if owner._pid == os.getpid():
            try:
                owner.close()
            except Exception:
                pass


def _after_fork_child():
    global _owners, _owners_lock
    _owners = set()
    _owners_lock = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork_child)
atexit.register(_cleanup)
