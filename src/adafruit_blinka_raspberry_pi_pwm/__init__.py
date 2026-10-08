# SPDX-License-Identifier: MIT
"""Experimental Raspberry Pi implementation of CircuitPython's PWMOut API."""

import atexit
import operator
import weakref

from ._hardware import HardwarePWM, discover
from ._software import SoftwarePWM

__version__ = "0.0.1.dev0"
__all__ = ["PWMOut"]

_outputs = weakref.WeakSet()


def _integer(value, name, minimum, maximum):
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    try:
        value = operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer") from None
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _engine_for(pin, frequency, duty_cycle):
    """Choose once; a busy/failed hardware route is never a software fallback."""
    route = discover(pin)
    if route is not None:
        return HardwarePWM(route, frequency, duty_cycle)
    _integer(frequency, "frequency", 1, 10000)
    return SoftwarePWM(pin, frequency, duty_cycle)


class PWMOut:
    """PWM on a Blinka Pin or BCM GPIO number.

    Duty cycle has the CircuitPython 0..65535 range. Frequency is writable
    only when variable_frequency=True. Already-configured BCM/RP1 hardware PWM
    is preferred; other pins use software PWM with a 1..10000 Hz configuration
    range, not a timing guarantee. Hardware limits come from its controller.
    """

    def __init__(self, pin, *, duty_cycle=0, frequency=500, variable_frequency=False):
        self._engine = None
        duty_cycle = _integer(duty_cycle, "duty_cycle", 0, 65535)
        frequency = _integer(frequency, "frequency", 1, 1000000000)
        if not isinstance(variable_frequency, bool):
            raise TypeError("variable_frequency must be bool")
        self._variable_frequency = variable_frequency
        self._frequency = frequency
        self._duty_cycle = duty_cycle
        self._engine = _engine_for(pin, frequency, duty_cycle)
        _outputs.add(self)

    def _check(self):
        if self._engine is None:
            raise ValueError("Object has been deinitialized")
        self._engine.check()

    @property
    def duty_cycle(self):
        """16-bit fraction of the period spent high; endpoints are steady levels."""
        self._check()
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value):
        self._check()
        value = _integer(value, "duty_cycle", 0, 65535)
        self._engine.configure(self._frequency, value)
        self._duty_cycle = value

    @property
    def frequency(self):
        """Configured frequency in Hz, rounded to the nearest integer."""
        self._check()
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        self._check()
        if not self._variable_frequency:
            raise AttributeError(
                "frequency is read-only unless variable_frequency=True"
            )
        value = _integer(value, "frequency", 1, 1000000000)
        self._engine.configure(value, self._duty_cycle)
        self._frequency = value

    def deinit(self):
        """Stop output and release ownership, without changing hardware pinmux."""
        engine = self._engine
        if engine is not None:
            try:
                engine.close()
            finally:
                # Failed hardware cleanup can still own an export. Retain it
                # for an explicit retry instead of abandoning the live output.
                if getattr(engine, "closed", True):
                    self._engine = None
                    _outputs.discard(self)

    @property
    def deinitialized(self):
        """Whether cleanup released the output; failed hardware close can retry."""
        return self._engine is None

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.deinit()

    def __del__(self):
        try:
            self.deinit()
        except Exception:
            # Explicit deinit reports I/O errors; destructors cannot reliably do so.
            pass


def _cleanup():
    for output in list(_outputs):
        try:
            output.deinit()
        except Exception:
            pass


atexit.register(_cleanup)
