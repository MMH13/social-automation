# -*- coding: utf-8 -*-
"""Cheap 'is a post due right now?' check — standard library only, no pip install.

GitHub delivers only a fraction of scheduled runs and delivers them ~2h late, so
asking for 7 runs a day and hoping loses most of them. The workflows instead poll
every 15 minutes and this decides whether the run has anything to do.

That only stays affordable because this check needs no dependencies: a run with
nothing due finishes in ~20 seconds on a bare checkout, and only a run that will
actually publish pays for Python packages, ffmpeg and the TTS model.

Usage: python scripts/is_due.py <queue.json> <slot_count> [--type=reel]
Writes due=true|false to GITHUB_OUTPUT.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path, slots = Path(args[0]), int(args[1])
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--type=")), None)

    items = json.loads(path.read_text(encoding="utf-8"))
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    posted_today = sum(1 for i in items if str(i.get("posted_at", "")).startswith(today))

    # Evenly spaced slots across the day, same rule the posters use.
    gap = 86400 // slots
    slot_minutes = [(i * gap) // 60 for i in range(slots)]
    due = sum(1 for s in slot_minutes if now.hour * 60 + now.minute >= s)

    remaining = [i for i in items if not i.get("posted_at")]
    if only:
        remaining = [i for i in remaining if i.get("type") == only]

    is_due = due > posted_today and bool(remaining)
    print(f"{path.name}: {posted_today} posted today, {due}/{slots} due by now, "
          f"{len(remaining)} left -> {'POST' if is_due else 'nothing to do'}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"due={'true' if is_due else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
