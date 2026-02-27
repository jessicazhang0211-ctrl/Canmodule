from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

import can


@dataclass(frozen=True)
class Alert:
    alert_type: str
    arb_id: int
    window_s: float
    count_in_window: int
    threshold: int
    timestamp: float  # monotonic time


class SlidingWindowFreqDetector:
    def __init__(self, window_s: float, threshold: int):
        self.window_s = float(window_s)
        self.threshold = int(threshold)
        self._ts_by_id: Dict[int, Deque[float]] = defaultdict(deque)
        self._last_alert_at: Dict[int, float] = {}  # rate-limit alerts per ID

    def observe(self, msg: can.Message, now: Optional[float] = None) -> List[Alert]:
        """
        Observe one message and possibly emit alerts.

        Alert rate-limited to at most 1 per (window_s/2) per arb_id to reduce log spam.
        """
        if now is None:
            now = time.monotonic()

        arb = int(msg.arbitration_id)
        dq = self._ts_by_id[arb]
        dq.append(now)

        cutoff = now - self.window_s
        while dq and dq[0] < cutoff:
            dq.popleft()

        alerts: List[Alert] = []
        count = len(dq)
        if count > self.threshold:
            last = self._last_alert_at.get(arb, 0.0)
            if (now - last) >= (self.window_s / 2.0):
                self._last_alert_at[arb] = now
                alerts.append(
                    Alert(
                        alert_type="FREQ_ANOMALY",
                        arb_id=arb,
                        window_s=self.window_s,
                        count_in_window=count,
                        threshold=self.threshold,
                        timestamp=now,
                    )
                )
        return alerts
