from __future__ import annotations

import csv
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import can

from sim.detector import Alert


class CsvLogger:
    """
    CSV logger for both frames and alerts.

    One row per event; event_type is either 'FRAME' or 'ALERT'.
    """
    HEADER = [
        "unix_ts",
        "mono_ts",
        "phase",
        "event_type",
        "direction",         # "rx" or "tx" (optional)
        "source",            # "ecu" / "injector" / "unknown"
        "arb_id_hex",
        "is_extended_id",
        "dlc",
        "data_hex",
        "alert_type",
        "window_s",
        "count_in_window",
        "threshold",
        "note",
    ]

    def __init__(self, out_csv: Path):
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        self._f = out_csv.open("w", newline="", encoding="utf-8")
        self._w = csv.DictWriter(self._f, fieldnames=self.HEADER)
        self._w.writeheader()
        self._f.flush()

    def close(self) -> None:
        try:
            self._f.flush()
        finally:
            self._f.close()

    @staticmethod
    def _to_hex_id(arb_id: int) -> str:
        return f"0x{arb_id:03X}"

    @staticmethod
    def _to_hex_data(msg: can.Message) -> str:
        b = bytes(msg.data or b"")
        return b.hex()

    def log_frame(
        self,
        msg: can.Message,
        phase: str,
        direction: str = "rx",
        source: str = "unknown",
        note: str = "",
    ) -> None:
        row = dict.fromkeys(self.HEADER, "")
        row["unix_ts"] = f"{time.time():.6f}"
        row["mono_ts"] = f"{time.monotonic():.6f}"
        row["phase"] = phase
        row["event_type"] = "FRAME"
        row["direction"] = direction
        row["source"] = source
        row["arb_id_hex"] = self._to_hex_id(int(msg.arbitration_id))
        row["is_extended_id"] = str(bool(msg.is_extended_id))
        row["dlc"] = str(int(msg.dlc))
        row["data_hex"] = self._to_hex_data(msg)
        row["note"] = note
        self._w.writerow(row)

    def log_alert(self, alert: Alert, phase: str, note: str = "") -> None:
        row = dict.fromkeys(self.HEADER, "")
        row["unix_ts"] = f"{time.time():.6f}"
        row["mono_ts"] = f"{alert.timestamp:.6f}"
        row["phase"] = phase
        row["event_type"] = "ALERT"
        row["alert_type"] = alert.alert_type
        row["arb_id_hex"] = self._to_hex_id(int(alert.arb_id))
        row["window_s"] = str(alert.window_s)
        row["count_in_window"] = str(alert.count_in_window)
        row["threshold"] = str(alert.threshold)
        row["note"] = note
        self._w.writerow(row)
