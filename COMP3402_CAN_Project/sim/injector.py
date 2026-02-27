from __future__ import annotations

import time
import can


def flood(
    bus: can.BusABC,
    arb_id: int,
    duration_s: float,
    rate_hz: int,
    data_byte: int = 0x63,
) -> None:
    """
    Flood frames at fixed rate on a given arbitration id.

    SAFETY: controller should ensure this runs only on vcan0 unless explicitly allowed.
    """
    interval = 1.0 / float(rate_hz)
    payload = bytes([int(data_byte) & 0xFF] * 8)
    end_t = time.monotonic() + float(duration_s)

    msg = can.Message(arbitration_id=int(arb_id), is_extended_id=False, data=payload)

    while time.monotonic() < end_t:
        try:
            bus.send(msg)
        except can.CanError:
            pass
        time.sleep(interval)
