from pathlib import Path
import can
from sim.logger import CsvLogger
from sim.detector import Alert


def test_csv_logger_writes(tmp_path: Path):
    out = tmp_path / "log.csv"
    lg = CsvLogger(out)

    msg = can.Message(arbitration_id=0x123, is_extended_id=False, data=b"\x11" * 8)
    lg.log_frame(msg, phase="baseline")

    alert = Alert(alert_type="FREQ_ANOMALY", arb_id=0x123, window_s=2.0, count_in_window=81, threshold=80, timestamp=1.23)
    lg.log_alert(alert, phase="attack")

    lg.close()
    assert out.exists()
    assert out.read_text(encoding="utf-8").count("\n") >= 3
