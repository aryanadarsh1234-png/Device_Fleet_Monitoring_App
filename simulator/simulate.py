
"""
Usage:
    python simulator/simulate.py                       # 5 devices, sents hearbeat every 5 seconds
    python simulator/simulate.py --stop device-03 --stop-after 20
        # device-03 stops sending after 20s -> OFFLINE Status 30 seconds later
"""
import argparse
import random
import threading
import time
from datetime import datetime, timezone

import requests


def register(base, device_id, name):
    r = requests.post(f"{base}/devices", json={"id": device_id, "name": name}, timeout=5)
    if r.status_code not in (201, 409):  # 409 = already registered, fine
        r.raise_for_status()


def run_device(base, device_id, interval, stop_event):
    while not stop_event.is_set():
        payload = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "OK",
            "cpu_usage": random.randint(10, 90),
            "signal_strength": random.randint(-90, -50),
        }
        try:
            requests.post(f"{base}/devices/{device_id}/heartbeat", json=payload, timeout=5)
            print(f"{device_id} -> heartbeat sent")
        except requests.RequestException as exc:
            print(f"{device_id} -> failed: {exc}")
        stop_event.wait(interval)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--devices", type=int, default=5)
    p.add_argument("--interval", type=float, default=5)
    p.add_argument("--stop", help="device id to stop, e.g. device-03")
    p.add_argument("--stop-after", type=float, default=20, help="seconds before stopping --stop device")
    args = p.parse_args()

    events = {}
    for i in range(1, args.devices + 1):
        did = f"device-{i:02d}"
        register(args.url, did, f"Lab Device {i:02d}")
        events[did] = threading.Event()
        threading.Thread(target=run_device, args=(args.url, did, args.interval, events[did]), daemon=True).start()

    start = time.time()
    try:
        while True:
            time.sleep(1)
            if args.stop in events and not events[args.stop].is_set() and time.time() - start >= args.stop_after:
                events[args.stop].set()
                print(f"*** {args.stop} stopped; expect OFFLINE in ~30s ***")
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()