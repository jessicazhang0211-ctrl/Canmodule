from __future__ import annotations

import csv
from collections import defaultdict, deque
from pathlib import Path

import matplotlib.pyplot as plt


def _mono(row) -> float:
    return float(row["mono_ts"])


def plot_counts_and_alerts(csv_path: Path, out_png: Path, window_s: float = 2.0):
    frames_by_id = defaultdict(list)
    alert_points = []

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["event_type"] == "FRAME":
                frames_by_id[row["arb_id_hex"]].append(_mono(row))
            elif row["event_type"] == "ALERT":
                alert_points.append((_mono(row), row["arb_id_hex"], row.get("alert_type", "")))

    # sliding window count per id -> time series
    series = {}
    for arb, ts_list in frames_by_id.items():
        ts_list.sort()
        dq = deque()
        xs, ys = [], []
        for t in ts_list:
            dq.append(t)
            cutoff = t - window_s
            while dq and dq[0] < cutoff:
                dq.popleft()
            xs.append(t)
            ys.append(len(dq))
        series[arb] = (xs, ys)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    for arb, (xs, ys) in series.items():
        ax.plot(xs, ys, label=arb)

    for t, arb, _atype in alert_points:
        ax.axvline(t, linestyle="--")

    ax.set_title(f"Sliding-window counts (window={window_s}s) and alert markers")
    ax.set_xlabel("monotonic time (s)")
    ax.set_ylabel("count in window")
    ax.legend(loc="upper right", fontsize="small")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)


if __name__ == "__main__":
    import sys
    plot_counts_and_alerts(Path(sys.argv[1]), Path(sys.argv[2]), window_s=float(sys.argv[3]) if len(sys.argv) > 3 else 2.0)
