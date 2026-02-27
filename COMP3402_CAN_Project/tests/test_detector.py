import time
import can
from sim.detector import SlidingWindowFreqDetector


def test_freq_detector_triggers():
    det = SlidingWindowFreqDetector(window_s=1.0, threshold=3)

    # create a fake CAN message
    msg = can.Message(arbitration_id=0x100, is_extended_id=False, data=b"\x00" * 8)

    t0 = time.monotonic()
    alerts = []
    # 4 messages within 1s => should trigger once
    for i in range(4):
        alerts.extend(det.observe(msg, now=t0 + 0.01 * i))

    assert any(a.alert_type == "FREQ_ANOMALY" for a in alerts)
