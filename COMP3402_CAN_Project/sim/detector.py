# detector.py
import time
import csv
import can
from collections import deque, defaultdict
from config import USE_KVASER, KVASER_CHANNEL, BITRATE

WHITELIST = {0x100, 0x200, 0x300}

# 频率检测参数：窗口 2 秒，若某 ID 在窗口内计数超过阈值则报警
WINDOW_SEC = 2.0
FREQ_THRESH = {
    0x100: 80,  # 正常20Hz，2秒约40，阈值80 -> flooding会触发
    0x200: 40,  # 正常10Hz，2秒约20
    0x300: 20,  # 正常5Hz，2秒约10
}

# payload 规则：对 0x200 的 byte0 做范围约束
PAYLOAD_RULES = {
    0x200: {"byte_index": 0, "min": 0, "max": 50}
}


def make_bus():
    if USE_KVASER:
        return can.Bus(interface="kvaser", channel=KVASER_CHANNEL, bitrate=BITRATE)
    return can.Bus(interface="virtual", channel="vcan0", bitrate=BITRATE)


def main(run_time=None):
    """Run detector loop.

    If run_time (seconds) is provided, the detector will stop after that many seconds.
    """
    bus = make_bus()
    print("Detector running... Ctrl+C to stop")

    # 记录每个 ID 的到达时间戳队列
    tsq = defaultdict(lambda: deque())

    # 证据：写CSV
    start_ts = time.time()
    with open("evidence_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "arb_id", "data_hex", "alert_type", "detail"])

        try:
            while True:
                # 如果指定了 run_time，运行到时长后退出
                if run_time is not None and (time.time() - start_ts) > float(run_time):
                    print('Detector runtime elapsed, exiting')
                    break
                msg = bus.recv(timeout=1.0)
                if msg is None:
                    continue

                now = time.time()
                arb_id = msg.arbitration_id
                data_hex = msg.data.hex()

                alert_type = ""
                detail = ""

                # 1) 新 ID（白名单外）
                if arb_id not in WHITELIST:
                    alert_type = "NEW_ID"
                    detail = f"Unknown arbitration_id=0x{arb_id:X}"

                # 2) 频率异常（flooding）
                q = tsq[arb_id]
                q.append(now)
                # 移除窗口外
                while q and (now - q[0]) > WINDOW_SEC:
                    q.popleft()
                if arb_id in FREQ_THRESH and len(q) > FREQ_THRESH[arb_id]:
                    alert_type = "FREQ_ANOMALY"
                    detail = f"count_in_{WINDOW_SEC:.1f}s={len(q)} thresh={FREQ_THRESH[arb_id]}"

                # 3) payload 越界
                if arb_id in PAYLOAD_RULES:
                    rule = PAYLOAD_RULES[arb_id]
                    b = msg.data[rule["byte_index"]]
                    if b < rule["min"] or b > rule["max"]:
                        alert_type = "PAYLOAD_SPIKE"
                        detail = f"byte{rule['byte_index']}={b} out_of[{rule['min']},{rule['max']}]"

                # 输出与记录
                if alert_type:
                    print(f"[ALERT] {alert_type} id=0x{arb_id:X} data={data_hex} {detail}")

                writer.writerow([now, f"0x{arb_id:X}", data_hex, alert_type, detail])
                f.flush()

        except KeyboardInterrupt:
            pass
        finally:
            try:
                bus.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    main()
