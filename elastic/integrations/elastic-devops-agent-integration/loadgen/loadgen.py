"""Steady traffic generator for payment-service (stdlib only).

Usage: python loadgen.py --targets http://127.0.0.1:8001,http://127.0.0.1:8002 --rps 8 [--duration 0]
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request
from collections import Counter
import threading
from concurrent.futures import ThreadPoolExecutor


def _post(url: str) -> int:
    body = json.dumps({"amount": round(random.uniform(5, 500), 2), "currency": "USD"}).encode()
    req = urllib.request.Request(f"{url}/payments", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:  # noqa: BLE001 - connection refused, timeouts, ...
        return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True, help="comma-separated base URLs")
    ap.add_argument("--rps", type=float, default=8.0, help="requests per second per target")
    ap.add_argument("--duration", type=int, default=0, help="seconds; 0 = run forever")
    args = ap.parse_args()

    targets = [t.strip().rstrip("/") for t in args.targets.split(",") if t.strip()]
    interval = 1.0 / args.rps
    stats: Counter = Counter()
    lock = threading.Lock()

    def hit(u: str) -> None:
        code = _post(u)
        with lock:
            stats[(u, code)] += 1

    start = last_report = time.time()
    with ThreadPoolExecutor(max_workers=64) as pool:
        while not args.duration or time.time() - start < args.duration:
            for t in targets:
                pool.submit(hit, t)
            time.sleep(interval)
            if time.time() - last_report >= 15:
                with lock:
                    print(time.strftime("%H:%M:%S"), dict(sorted(stats.items())), flush=True)
                    stats.clear()
                last_report = time.time()


if __name__ == "__main__":
    main()
