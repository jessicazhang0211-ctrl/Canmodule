from __future__ import annotations

import subprocess
import sys

from sim.auto_test import main


def _print_vcan_setup_hint() -> None:
    print(
        "If you haven't created vcan0 yet, run:\n"
        "  sudo modprobe vcan\n"
        "  sudo ip link add dev vcan0 type vcan\n"
        "  sudo ip link set vcan0 up\n"
    )


def try_show_vcan0() -> None:
    try:
        subprocess.run(["ip", "link", "show", "vcan0"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        _print_vcan_setup_hint()


if __name__ == "__main__":
    try_show_vcan0()
    # Forward CLI args to sim.auto_test
    raise SystemExit(main(sys.argv[1:]))
# run_demo.py
# 一键演示（占位文件）

# TODO: 实现演示脚本入口（placeholder）

if __name__ == "__main__":
    print("run_demo.py placeholder")
