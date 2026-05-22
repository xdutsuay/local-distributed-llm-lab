#!/usr/bin/env python3
"""
Benchmark POST /chat latency against a running coordinator.

Example:
  python scripts/benchmark_chat.py --prompt "2+2" --repeat 3
  python scripts/benchmark_chat.py --prompt "2+2" --repeat 3 --force-local
"""
import argparse
import statistics
import sys
import time

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Time POST /chat requests")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Coordinator base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--prompt", default="2+2", help="Chat prompt to send")
    parser.add_argument("--repeat", type=int, default=1, help="Number of timed requests")
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-request timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Print note: coordinator must be started with FORCE_LOCAL_WORKER=1",
    )
    args = parser.parse_args()

    if args.repeat < 1:
        print("error: --repeat must be >= 1", file=sys.stderr)
        return 1

    if args.force_local:
        print(
            "Note: restart coordinator with FORCE_LOCAL_WORKER=1 before benchmarking "
            "(e.g. FORCE_LOCAL_WORKER=1 ./scripts/start_coordinator.sh)"
        )

    url = f"{args.base_url.rstrip('/')}/chat"
    latencies: list[float] = []

    for i in range(args.repeat):
        start = time.perf_counter()
        try:
            response = requests.post(
                url,
                json={"prompt": args.prompt},
                timeout=args.timeout,
            )
        except requests.RequestException as exc:
            print(f"run {i + 1}/{args.repeat}: request failed: {exc}", file=sys.stderr)
            return 1

        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        if response.status_code != 200:
            try:
                body = response.json()
                err = body.get("error") or body.get("detail") or response.text
            except ValueError:
                err = response.text
            print(
                f"run {i + 1}/{args.repeat}: HTTP {response.status_code} "
                f"({elapsed:.2f}s) — {err}",
                file=sys.stderr,
            )
            return 1

        print(f"run {i + 1}/{args.repeat}: {elapsed:.2f}s OK")

    if len(latencies) == 1:
        print(f"total: {latencies[0]:.2f}s")
    else:
        print(
            f"stats ({len(latencies)} runs): "
            f"min={min(latencies):.2f}s "
            f"p50={statistics.median(latencies):.2f}s "
            f"max={max(latencies):.2f}s "
            f"mean={statistics.mean(latencies):.2f}s"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
