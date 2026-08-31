# -*- coding: utf-8 -*-
"""Daily health check across every page's queue.

The queue_check that runs after each post only sees the queue it just touched, and
only notices when a queue is nearly empty. It cannot see the failure that actually
bit us: posting silently falling below target because GitHub dropped most of the
scheduled runs (3 of 7 delivered on 2026-08-30), or a workflow being disabled and
nobody noticing for eight days (post-x, 2026-08-21).

This looks at outcomes instead — how many posts actually went out in the last 24h
versus what each page is meant to publish — so a page going quiet is caught here
rather than by spotting a gap on Facebook.

Usage: python scripts/health_check.py            (prints a report, always exits 0)
       python scripts/health_check.py --strict   (exit 1 if anything is unhealthy)
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# queue file, posts expected per day, label, item type counted for runway (None = all)
PAGES = [
    ("scheduled_ss/content.json", 7, "Speaking from soul", "reel"),
    ("scheduled_pt/content.json", 10, "Psychology Tube", None),
    ("scheduled_mh/content.json", 3, "Mamun Hossain", None),
]
LOW_RUNWAY_DAYS = 3.0
# A page is flagged when it publishes less than this share of its target. Kept below
# 1.0 on purpose: GitHub drops runs routinely, so demanding a perfect day would cry
# wolf every morning and get ignored — which is how a real outage slips through.
MIN_HEALTHY_RATIO = 0.6


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def check_page(rel: str, per_day: int, label: str, runway_type):
    items = load(ROOT / rel)
    if items is None:
        return [f"{label}: queue file {rel} is missing"], []

    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    recent = 0
    latest = None
    for it in items:
        stamp = it.get("posted_at")
        if not stamp:
            continue
        try:
            when = datetime.fromisoformat(str(stamp))
        except ValueError:
            continue
        if when > now + timedelta(hours=1):
            continue  # a stamp from another timezone; ignore rather than trust
        if latest is None or when > latest:
            latest = when
        if when >= cutoff:
            recent += 1

    unposted = [i for i in items if not i.get("posted_at")]
    if runway_type:
        unposted = [i for i in unposted if i.get("type") == runway_type]
    runway = len(unposted) / per_day if per_day else 0

    problems, notes = [], []
    ratio = recent / per_day if per_day else 1
    notes.append(f"{label}: {recent}/{per_day} posts in 24h, "
                 f"{len(unposted)} queued (~{runway:.1f} days)")

    if ratio < MIN_HEALTHY_RATIO:
        problems.append(f"{label}: only {recent} of {per_day} posts in the last 24h")
    if latest is None:
        problems.append(f"{label}: nothing has ever been posted")
    else:
        quiet = (now - latest).total_seconds() / 3600
        notes.append(f"{label}: last post {quiet:.1f}h ago")
        # Well past any single gap, so this means posting has stopped, not drifted.
        if quiet > 12:
            problems.append(f"{label}: silent for {quiet:.0f}h")
    if runway < LOW_RUNWAY_DAYS:
        problems.append(f"{label}: only {runway:.1f} days of content left - refill needed")
    return problems, notes


def main() -> int:
    all_problems, all_notes = [], []
    for rel, per_day, label, rtype in PAGES:
        p, n = check_page(rel, per_day, label, rtype)
        all_problems += p
        all_notes += n

    print("=== queue health ===")
    for n in all_notes:
        print("  " + n)
    print()
    if all_problems:
        print("PROBLEMS:")
        for p in all_problems:
            print("  ! " + p)
    else:
        print("All pages healthy.")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        body = "\\n".join(f"- {p}" for p in all_problems) or "none"
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"unhealthy={'true' if all_problems else 'false'}\n")
            fh.write(f"summary={body}\n")

    return 1 if (all_problems and "--strict" in sys.argv) else 0


if __name__ == "__main__":
    raise SystemExit(main())
