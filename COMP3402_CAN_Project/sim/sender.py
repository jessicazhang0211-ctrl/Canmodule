# sender.py
import time
import can
from config import USE_KVASER, KVASER_CHANNEL, BITRATE


def make_bus():
    if USE_KVASER:
        return can.Bus(interface="kvaser", channel=KVASER_CHANNEL, bitrate=BITRATE)
    # 纯软件虚拟总线：不用硬件也能跑
    return can.Bus(interface="virtual", channel="vcan0", bitrate=BITRATE)


def main():
    bus = make_bus()

    # 3 个“正常节点”消息（ID 白名单）
    msgs = [
        (0x100, [10, 0, 0, 0, 0, 0, 0, 0], 0.050),  # 20Hz
        (0x200, [0, 1, 2, 3, 4, 5, 6, 7], 0.100),   # 10Hz
        (0x300, [1, 1, 1, 1, 1, 1, 1, 1], 0.200),   # 5Hz
    ]

    next_ts = [time.time()] * len(msgs)
    print("Sender running... Ctrl+C to stop")
    try:
        while True:
            now = time.time()
            for i, (arb_id, data, period) in enumerate(msgs):
                if now >= next_ts[i]:
                    m = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
                    bus.send(m)
                    next_ts[i] = now + period
            time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            bus.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
