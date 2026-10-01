"""Linux extension failure paths, using ordinary file descriptors, never GPIO."""

import os
import sys

import pytest


@pytest.mark.skipif(sys.platform != "linux", reason="Linux GPIO extension")
def test_invalid_descriptors_do_not_leak():
    from adafruit_blinka_raspberry_pi_pwm import _native

    before = len(os.listdir("/proc/self/fd"))
    with pytest.raises(OSError):
        _native.start(-1, 500, 0)
    read_fd, write_fd = os.pipe()
    try:
        for _ in range(30):
            with pytest.raises(OSError):
                _native.start(write_fd, 500, 0)
    finally:
        os.close(read_fd)
        os.close(write_fd)
    assert len(os.listdir("/proc/self/fd")) == before
