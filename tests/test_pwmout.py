"""Public API tests: no GPIO access, including actual CircuitPython consumers."""

import errno
import gc
import sys
from types import SimpleNamespace

import pytest

import adafruit_blinka_raspberry_pi_pwm as pwm


class FakeEngine:
    def __init__(self, pin, frequency, duty):
        self.pin = pin
        self.settings = (frequency, duty)
        self.closed = False
        self.error = None

    def check(self):
        if self.error:
            raise self.error

    def configure(self, frequency, duty):
        self.check()
        if not 1 <= frequency <= 10000:
            raise ValueError("software frequency out of range")
        self.settings = (frequency, duty)

    def close(self):
        self.closed = True
        self.check()


@pytest.fixture(autouse=True)
def engine(monkeypatch):
    monkeypatch.setattr(pwm, "SoftwarePWM", FakeEngine)
    # Simulate Blinka's planned export while importing the real consumer modules.
    monkeypatch.setitem(sys.modules, "pwmio", SimpleNamespace(PWMOut=pwm.PWMOut))


def test_defaults_and_duty_endpoints():
    with pwm.PWMOut(SimpleNamespace(id=18)) as output:
        assert output.frequency == 500
        assert output.duty_cycle == 0
        output.duty_cycle = 65535
        assert output.duty_cycle == 65535
        output.duty_cycle = 1
        assert output.duty_cycle == 1  # No rounding down to integer percent.


def test_fixed_and_variable_frequency():
    with pwm.PWMOut(12) as fixed:
        with pytest.raises(AttributeError):
            fixed.frequency = 50
    with pwm.PWMOut(13, duty_cycle=1234, variable_frequency=True) as variable:
        variable.frequency = 440
        assert variable.frequency == 440
        assert variable.duty_cycle == 1234


@pytest.mark.parametrize(
    "name,value,exception",
    [
        ("duty_cycle", -1, ValueError),
        ("duty_cycle", 65536, ValueError),
        ("duty_cycle", 0.5, TypeError),
        ("duty_cycle", True, TypeError),
        ("frequency", 0, ValueError),
        ("frequency", 10001, ValueError),
        ("frequency", float("nan"), TypeError),
        ("frequency", "500", TypeError),
        ("variable_frequency", 1, TypeError),
    ],
)
def test_invalid_construction(name, value, exception):
    with pytest.raises(exception):
        pwm.PWMOut(12, **{name: value})


def test_invalid_updates_preserve_settings():
    with pwm.PWMOut(12, duty_cycle=2345, variable_frequency=True) as output:
        with pytest.raises(ValueError):
            output.duty_cycle = -1
        with pytest.raises(ValueError):
            output.frequency = 0
        assert (output.frequency, output.duty_cycle) == (500, 2345)


def test_lifecycle_and_context_exception():
    output = pwm.PWMOut(12)
    worker = output._engine
    with pytest.raises(LookupError):
        with output:
            raise LookupError("application error")
    assert worker.closed
    output.deinit()  # Idempotent.
    for operation in (
        lambda: output.frequency,
        lambda: output.duty_cycle,
        lambda: setattr(output, "duty_cycle", 0),
        lambda: setattr(output, "frequency", 50),
        output.__enter__,
    ):
        with pytest.raises(ValueError, match="deinitialized"):
            operation()


def test_failure_surfaces_and_cleanup_still_releases():
    output = pwm.PWMOut(12)
    worker = output._engine
    worker.error = OSError(errno.EIO, "injected output failure")
    with pytest.raises(OSError):
        output.duty_cycle = 1000
    with pytest.raises(OSError):
        output.deinit()
    assert worker.closed
    output.deinit()


def test_independent_outputs_and_collection():
    first = pwm.PWMOut(12, frequency=50)
    second = pwm.PWMOut(13, frequency=1000)
    worker = first._engine
    del first
    gc.collect()
    assert worker.closed
    assert second.frequency == 1000
    second.deinit()


def test_motor_servo_consumer():
    # This is the real Adafruit library, not a locally reconstructed consumer.
    from adafruit_motor.servo import Servo

    with pwm.PWMOut(12, frequency=50) as output:
        servo = Servo(output)
        servo.angle = 90
        assert 0 < output.duty_cycle < 65535
        assert servo.angle == pytest.approx(90, abs=1)
        servo.angle = None
        assert output.duty_cycle == 0


def test_motor_dc_consumer():
    from adafruit_motor.motor import DCMotor

    with (
        pwm.PWMOut(12, frequency=1000) as first,
        pwm.PWMOut(13, frequency=1000) as second,
    ):
        motor = DCMotor(first, second)
        motor.throttle = 0.5
        assert 0 < first.duty_cycle < 65535 or 0 < second.duty_cycle < 65535
        motor.throttle = -0.5
        motor.throttle = None
        assert first.duty_cycle == second.duty_cycle == 0


def test_hardware_selection_and_backend_specific_frequency(monkeypatch):
    route = object()

    class Hardware(FakeEngine):
        def configure(self, frequency, duty):
            self.check()
            self.settings = (frequency, duty)

    monkeypatch.setattr(pwm, "discover", lambda pin: route)
    monkeypatch.setattr(pwm, "HardwarePWM", Hardware)
    with pwm.PWMOut(18, frequency=25000, variable_frequency=True) as output:
        assert output._engine.pin is route
        output.frequency = 20000
        assert output.frequency == 20000


def test_hardware_failure_does_not_fall_back(monkeypatch):
    attempts = []

    def hardware(*args):
        attempts.append("hardware")
        raise OSError(errno.EBUSY, "owned hardware channel")

    monkeypatch.setattr(pwm, "discover", lambda pin: object())
    monkeypatch.setattr(pwm, "HardwarePWM", hardware)
    monkeypatch.setattr(pwm, "SoftwarePWM", lambda *args: attempts.append("software"))
    with pytest.raises(OSError) as error:
        pwm.PWMOut(18)
    assert error.value.errno == errno.EBUSY
    assert attempts == ["hardware"]


def test_software_frequency_update_still_has_10khz_limit():
    with pwm.PWMOut(23, variable_frequency=True) as output:
        with pytest.raises(ValueError):
            output.frequency = 10001
        assert output.frequency == 500


def test_failed_hardware_close_retains_owner_for_retry(monkeypatch):
    class Hardware(FakeEngine):
        def close(self):
            if not getattr(self, "attempted", False):
                self.attempted = True
                raise OSError(errno.EIO, "failed low write")
            self.closed = True

    monkeypatch.setattr(pwm, "discover", lambda pin: object())
    monkeypatch.setattr(pwm, "HardwarePWM", Hardware)
    output = pwm.PWMOut(18)
    owner = output._engine
    with pytest.raises(OSError):
        output.deinit()
    assert output._engine is owner
    assert not output.deinitialized
    output.deinit()
    assert output.deinitialized
    output.deinit()
