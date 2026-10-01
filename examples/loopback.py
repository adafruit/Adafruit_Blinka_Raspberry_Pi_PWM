"""Compare draft and existing Blinka using two free GPIOs joined by a jumper.

python examples/loopback.py --output 18 --input 23 --frequency 500 --backend draft
Repeat with --backend blinka in an environment using the existing backend.
This is an interrupt-timestamp smoke test, not an external waveform measurement.
"""

import argparse
import json
import statistics
import threading
import time
from datetime import timedelta

import gpiod
from gpiod.line import Direction, Edge

from adafruit_blinka_raspberry_pi_pwm import PWMOut
from adafruit_blinka_raspberry_pi_pwm._software import _find_chip


def capture(request, stopped, events, errors):
    try:
        while not stopped.is_set():
            if request.wait_edge_events(timedelta(milliseconds=50)):
                events.extend(request.read_edge_events(max_events=1024))
    except Exception as error:
        errors.append(str(error))


def describe(samples):
    if not samples:
        return None
    ordered = sorted(samples)
    return {
        "count": len(samples),
        "min_ns": min(samples),
        "median_ns": statistics.median(samples),
        "p99_ns": ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))],
        "max_ns": max(samples),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=int, required=True, help="free BCM GPIO to drive"
    )
    parser.add_argument(
        "--input", type=int, required=True, help="jumpered free BCM GPIO"
    )
    parser.add_argument("--frequency", type=int, default=500)
    parser.add_argument("--duty-cycle", type=int, default=32768)
    parser.add_argument("--seconds", type=float, default=2)
    parser.add_argument("--backend", choices=("draft", "blinka"), default="draft")
    args = parser.parse_args()
    if args.output == args.input or min(args.output, args.input) < 0:
        parser.error("input/output must be distinct nonnegative GPIO numbers")
    if not 1 <= args.frequency <= 10000 or not 0 <= args.duty_cycle <= 65535:
        parser.error("frequency must be 1..10000 and duty-cycle 0..65535")
    if not 0 < args.seconds <= 60:
        parser.error("seconds must be greater than zero and at most 60")

    output_type, pin = PWMOut, args.output
    if args.backend == "blinka":
        import board
        import pwmio

        output_type, pin = pwmio.PWMOut, getattr(board, f"D{args.output}")
    events, errors = [], []
    stopped = threading.Event()
    path = _find_chip(gpiod, args.input)
    with gpiod.request_lines(
        path,
        consumer="blinka-pwm-loopback",
        config={
            args.input: gpiod.LineSettings(
                direction=Direction.INPUT, edge_detection=Edge.BOTH
            )
        },
        event_buffer_size=1024,
    ) as request:
        reader = threading.Thread(
            target=capture, args=(request, stopped, events, errors)
        )
        reader.start()
        try:
            with output_type(pin, frequency=args.frequency, duty_cycle=args.duty_cycle):
                time.sleep(args.seconds)
        finally:
            stopped.set()
            reader.join()

    rises, periods, highs, gaps = [], [], [], 0
    previous_sequence, last_rise = None, None
    for event in events:
        if previous_sequence is not None:
            gaps += max(0, event.line_seqno - previous_sequence - 1)
        previous_sequence = event.line_seqno
        if event.event_type == gpiod.EdgeEvent.Type.RISING_EDGE:
            if rises:
                periods.append(event.timestamp_ns - rises[-1])
            rises.append(event.timestamp_ns)
            last_rise = event.timestamp_ns
        elif last_rise is not None:
            highs.append(event.timestamp_ns - last_rise)
            last_rise = None
    report = {
        "backend": args.backend,
        "requested_frequency_hz": args.frequency,
        "requested_duty_cycle": args.duty_cycle,
        "edge_count": len(events),
        "lost_events": gaps,
        "capture_errors": errors,
        "period": describe(periods),
        "high_pulse": describe(highs),
        "measured_average_frequency_hz": (
            1e9 / statistics.mean(periods) if periods else None
        ),
        "measurement": "kernel edge timestamps; verify with an external analyzer",
    }
    print(json.dumps(report, indent=2))
    if errors or gaps or (0 < args.duty_cycle < 65535 and len(periods) < 2):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
