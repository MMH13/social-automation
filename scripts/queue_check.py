# -*- coding: utf-8 -*-
"""Report how many unposted items are left in a queue file.

Usage: python scripts/queue_check.py <queue.json> <per_day> <label>
Prints a GitHub Actions warning + sets outputs when the queue runs low.
"""
import json
import os
import sys
from pathlib import Path

LOW_DAYS = 2.0  # warn when less than this many days of content remain


def main() -> int:
    path, per_day, label = Path(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    items = json.loads(path.read_text(encoding="utf-8"))
    left = sum(1 for i in items if not i.get("posted_at"))
    days = left / per_day
    low = days < LOW_DAYS

    print(f"{label} queue: {left} item(s) left ({days:.1f} days at {per_day:g}/day)")
    if low:
        print(f"::warning title={label} queue low::"
              f"Only {left} item(s) (~{days:.1f} days) left in {path.as_posix()}. Refill it.")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"left={left}\n")
            fh.write(f"days={days:.1f}\n")
            fh.write(f"low={'true' if low else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
