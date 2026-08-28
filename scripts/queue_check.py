# -*- coding: utf-8 -*-
"""Report how many unposted items are left in a queue file.

Usage: python scripts/queue_check.py <queue.json> <per_day> <label> [--pt-buckets] [--only-type=X]

--pt-buckets additionally checks the Psychology Tube narrated/other split
(post_pt.py targets 5/5 per day) so a starved bucket gets caught even while
the total count still looks healthy - it did, silently, until this existed.

--only-type=X counts just that item type. Speaking from soul needs it: the page
posts reels only, so counting the skipped quote-card items too would overstate
the runway by roughly half and delay the low-queue warning past the point of use.
"""
import json
import os
import sys
from pathlib import Path

LOW_DAYS = 2.0  # warn when less than this many days of content remain
PT_BUCKET_TARGETS = {"narrated": 5, "other": 5}


def category(item) -> str:
    return "narrated" if item["type"] == "narrated" else "other"


def check(label: str, left: int, per_day: float) -> bool:
    days = left / per_day if per_day else 0
    low = days < LOW_DAYS
    print(f"{label}: {left} item(s) left ({days:.1f} days at {per_day:g}/day)")
    if low:
        print(f"::warning title={label} low::"
              f"Only {left} item(s) (~{days:.1f} days) left for {label}. Refill it.")
    return low


def write_outputs(prefix: str, left: int, days: float, low: bool) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(f"{prefix}left={left}\n")
        fh.write(f"{prefix}days={days:.1f}\n")
        fh.write(f"{prefix}low={'true' if low else 'false'}\n")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path, per_day, label = Path(args[0]), float(args[1]), args[2]
    items = json.loads(path.read_text(encoding="utf-8"))
    unposted = [i for i in items if not i.get("posted_at")]

    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only-type=")), None)
    if only:
        unposted = [i for i in unposted if i["type"] == only]
        label = f"{label} ({only}s)"

    left = len(unposted)
    days = left / per_day if per_day else 0
    low = check(label, left, per_day)
    write_outputs("", left, days, low)

    any_low = low
    if "--pt-buckets" in sys.argv:
        for cat, target in PT_BUCKET_TARGETS.items():
            cat_left = sum(1 for i in unposted if category(i) == cat)
            cat_low = check(f"{label} ({cat})", cat_left, target)
            write_outputs(f"{cat}_", cat_left, cat_left / target if target else 0, cat_low)
            any_low = any_low or cat_low

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"any_low={'true' if any_low else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
