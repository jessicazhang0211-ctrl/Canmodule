from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import List

import can

from sim.config import ECUConfig


def _hex8_to_bytes(data_hex: str) -> bytes:
    s = (data_hex or "").strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if len(s) % 2 == 1:
        s = "0" + s
    b = bytes.fromhex(s)
    # pad or truncate to 8 bytes (Classical CAN)
    return (b + b"\x00" * 8)[:8]


@dataclass
class PeriodicECUNode:
    ecu: ECUConfig
    bus: can.BusABC

    _stop: threading.Event = threading.Event()
    _thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"ECU-{self.ecu.name}", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        payload = _hex8_to_bytes(self.ecu.data_hex)
        msg = can.Message(
            arbitration_id=self.ecu.arb_id,
            is_extended_id=False,
            data=payload,
        )
        period = float(self.ecu.period_s)
        next_t = time.monotonic()

        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_t:
                try:
                    self.bus.send(msg)
                except can.CanError:
                    # in simulation we just continue; in real system you may want retries
                    pass
                next_t += period
            else:
                # sleep a little to reduce CPU; do not oversleep too long
                time.sleep(min(0.001, max(0.0, next_t - now)))


def start_ecu_fleet(bus: can.BusABC, ecu_cfgs: List[ECUConfig]) -> List[PeriodicECUNode]:
    nodes: List[PeriodicECUNode] = []
    for ec in ecu_cfgs:
        n = PeriodicECUNode(ecu=ec, bus=bus)
        n.start()
        nodes.append(n)
    return nodes


def stop_ecu_fleet(nodes: List[PeriodicECUNode]) -> None:
    for n in nodes:
        n.stop()
