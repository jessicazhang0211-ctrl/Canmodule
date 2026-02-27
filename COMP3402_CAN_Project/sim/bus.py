from __future__ import annotations

import can
from sim.config import BusConfig


def assert_safe_channel(cfg: BusConfig, allow_real_can: bool) -> None:
    """
    SAFETY GUARD: prevent accidentally running on real car interfaces (e.g., can0).
    This project is intended for simulation on vcan*.
    """
    ch = (cfg.channel or "").lower()
    if ch.startswith("vcan"):
        return
    if allow_real_can:
        return
    raise RuntimeError(
        f"Refusing to open non-vcan channel '{cfg.channel}'. "
        "Use vcan0 for simulation or pass --allow-real-can if you really mean it."
    )


def create_bus(cfg: BusConfig, allow_real_can: bool = False) -> can.BusABC:
    """
    Create a python-can bus.

    For Linux SocketCAN + vcan0:
        can.Bus(interface='socketcan', channel='vcan0')

    receive_own_messages typically False; local loopback behavior depends on SocketCAN settings.
    """
    assert_safe_channel(cfg, allow_real_can=allow_real_can)

    kwargs = dict(receive_own_messages=cfg.receive_own_messages)

    # Note: For socketcan, bitrate is set via `ip link`, not by python-can. Kept for metadata only.
    bus = can.Bus(interface=cfg.interface, channel=cfg.channel, **kwargs)
    return bus
