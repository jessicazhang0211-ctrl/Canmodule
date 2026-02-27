from __future__ import annotations

import argparse
import threading
import time

from sim.bus import create_bus
from sim.config import ExperimentConfig, default_experiment
from sim.detector import SlidingWindowFreqDetector
from sim.ecu_nodes import start_ecu_fleet, stop_ecu_fleet
from sim.injector import flood
from sim.logger import CsvLogger


def run_experiment(cfg: ExperimentConfig) -> dict:
    out_csv = cfg.out_dir / f"evidence_log_{cfg.run_tag}_{time.strftime('%Y%m%d_%H%M%S')}.csv"

    bus = create_bus(cfg.bus, allow_real_can=cfg.allow_real_can)
    logger = CsvLogger(out_csv)
    detector = SlidingWindowFreqDetector(window_s=cfg.detector.window_s, threshold=cfg.detector.threshold)

    ecu_nodes = start_ecu_fleet(bus, cfg.ecus)

    alerts_total = 0

    def recv_loop(duration_s: float, phase: str) -> None:
        nonlocal alerts_total
        end = time.monotonic() + float(duration_s)
        while time.monotonic() < end:
            msg = bus.recv(timeout=0.05)
            if msg is None:
                continue
            logger.log_frame(msg, phase=phase, direction="rx", source="bus")
            for alert in detector.observe(msg):
                alerts_total += 1
                logger.log_alert(alert, phase=phase)

    try:
        # baseline
        recv_loop(cfg.baseline_s, phase="baseline")

        # attack: run flood concurrently while receiving
        if cfg.flood.enabled:
            t = threading.Thread(
                target=flood,
                kwargs=dict(
                    bus=bus,
                    arb_id=cfg.flood.arb_id,
                    duration_s=cfg.flood.duration_s,
                    rate_hz=cfg.flood.rate_hz,
                    data_byte=cfg.flood.data_byte,
                ),
                daemon=True,
            )
            t.start()
            recv_loop(cfg.flood.duration_s, phase="attack")
            t.join(timeout=1.0)

        # recovery
        recv_loop(cfg.recovery_s, phase="recovery")

    finally:
        stop_ecu_fleet(ecu_nodes)
        # optional safety flush
        try:
            logger._f.flush()
        except Exception:
            pass
        logger.close()
        try:
            bus.shutdown()
        except Exception:
            pass

    return {
        "out_csv": str(out_csv),
        "alerts_total": alerts_total,
        "window_s": cfg.detector.window_s,
        "threshold": cfg.detector.threshold,
        "baseline_s": cfg.baseline_s,
        "recovery_s": cfg.recovery_s,
        "flood_enabled": cfg.flood.enabled,
        "flood_rate_hz": cfg.flood.rate_hz,
        "flood_duration_s": cfg.flood.duration_s,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--channel", default="vcan0")
    p.add_argument("--interface", default="socketcan")
    p.add_argument("--baseline-s", type=float, default=8.0)
    p.add_argument("--recovery-s", type=float, default=5.0)
    p.add_argument("--window-s", type=float, default=2.0)
    p.add_argument("--threshold", type=int, default=80)
    p.add_argument("--flood", action="store_true")
    p.add_argument("--flood-id", default="0x100")
    p.add_argument("--flood-rate-hz", type=int, default=200)
    p.add_argument("--flood-duration-s", type=float, default=5.0)
    p.add_argument("--run-tag", default="demo")
    p.add_argument("--allow-real-can", action="store_true")
    args = p.parse_args(argv)

    cfg = default_experiment()

    cfg = ExperimentConfig(
        bus=cfg.bus.__class__(
            interface=args.interface,
            channel=args.channel,
            bitrate=cfg.bus.bitrate,
            receive_own_messages=cfg.bus.receive_own_messages,
        ),
        ecus=cfg.ecus,
        detector=cfg.detector.__class__(window_s=args.window_s, threshold=args.threshold),
        flood=cfg.flood.__class__(
            enabled=bool(args.flood),
            arb_id=int(args.flood_id, 16) if str(args.flood_id).startswith("0x") else int(args.flood_id),
            rate_hz=args.flood_rate_hz,
            duration_s=args.flood_duration_s,
            data_byte=0x63,
        ),
        baseline_s=args.baseline_s,
        recovery_s=args.recovery_s,
        out_dir=cfg.out_dir,
        run_tag=args.run_tag,
        allow_real_can=bool(args.allow_real_can),
    )

    summary = run_experiment(cfg)
    print("SUMMARY:", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
