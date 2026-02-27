# auto_test.py
# 自动演示：启动 detector + sender，然后按序运行多个攻击示例，并保存 evidence CSV 到 ../evidence/logs/

import os
import sys
import time
import threading
from datetime import datetime
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

print('auto_test: working dir', HERE)

import detector
import sender
import injector

# Scenario parameters (short demo)
baseline_sec = 5
burst_rounds = 2
burst_interval = 2
burst_duration = 1
id_sweep_count = 2
spoof_count = 10
fuzz_count = 50

# replay from previous logs folder if available
replay_path = os.path.normpath(os.path.join(HERE, '..', 'evidence', 'logs'))

# estimate detector run time: baseline + attacks + small buffer
detector_run_time = baseline_sec + (burst_rounds * (burst_duration + 0.1)) + 3 + 3

# Start detector (non-daemon so we can join)
t_det = threading.Thread(target=lambda: detector.main(run_time=detector_run_time))
# Start sender as daemon
t_snd = threading.Thread(target=sender.main, daemon=True)

print('Starting detector...')
t_det.start()
# give detector time to initialize
time.sleep(0.5)
print('Starting sender...')
t_snd.start()

# Baseline
print(f'Collecting baseline for {baseline_sec} seconds...')
time.sleep(baseline_sec)

# 1) Burst Flood
print(f'Running Burst Flood: {burst_rounds} rounds, {burst_duration}s each')
try:
    bbus = injector.make_bus()
    injector.burst_flood(bbus, arb_id=0x100, burst_interval=burst_interval, burst_duration=burst_duration, hz=200, rounds=burst_rounds)
    try:
        bbus.shutdown()
    except Exception:
        pass
except Exception as e:
    print('burst_flood error:', e)

# small pause
time.sleep(0.5)

# 2) ID Sweep (small range)
print('Running ID Sweep 0x100-0x10F')
try:
    sbus = injector.make_bus()
    injector.id_sweep(sbus, start_id=0x100, end_id=0x10F, count_per_id=id_sweep_count, delay=0.005)
    try:
        sbus.shutdown()
    except Exception:
        pass
except Exception as e:
    print('id_sweep error:', e)

# small pause
time.sleep(0.5)

# 3) Spoofing
print('Running Spoofing on 0x200')
try:
    spbus = injector.make_bus()
    injector.spoofing(spbus, arb_id=0x200, spoof_value=250, count=spoof_count, delay=0.05)
    try:
        spbus.shutdown()
    except Exception:
        pass
except Exception as e:
    print('spoofing error:', e)

# small pause
time.sleep(0.5)

# 4) Fuzzing
print('Running Fuzzing on 0x300')
try:
    fbus = injector.make_bus()
    injector.fuzzing(fbus, arb_id=0x300, base_payload=[1] * 8, count=fuzz_count, mutation_rate=0.3, delay=0.01)
    try:
        fbus.shutdown()
    except Exception:
        pass
except Exception as e:
    print('fuzzing error:', e)

# small pause
time.sleep(0.5)

# 5) Replay (if previous evidence exists)
prev_logs = []
if os.path.isdir(replay_path):
    for fn in os.listdir(replay_path):
        if fn.endswith('.csv'):
            prev_logs.append(os.path.join(replay_path, fn))
    prev_logs.sort()
if prev_logs:
    last = prev_logs[-1]
    print('Replaying from', last)
    try:
        rbus = injector.make_bus()
        injector.replay(rbus, last)
        try:
            rbus.shutdown()
        except Exception:
            pass
    except Exception as e:
        print('replay error:', e)
else:
    print('No previous logs to replay in', replay_path)

# Wait for detector to finish
print('Waiting for detector to finish...')
# join with timeout slightly larger than detector_run_time
t_det.join(timeout=detector_run_time + 2)

# move evidence_log.csv to evidence/logs with timestamp
src = os.path.join(HERE, 'evidence_log.csv')
if os.path.exists(src):
    dst_dir = os.path.normpath(os.path.join(HERE, '..', 'evidence', 'logs'))
    os.makedirs(dst_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(dst_dir, f'evidence_log_demo_{ts}.csv')
    try:
        try:
            os.replace(src, dst)
        except Exception:
            shutil.copy(src, dst)
            os.remove(src)
        print('Moved evidence to', dst)
    except Exception as e:
        print('Failed to move evidence file:', e)
else:
    print('No evidence_log.csv found in', HERE)

print('auto_test completed.')
