"""Typed daily slot plan - which kind of post is owed right now. Standard library only.

2026-11-19: Speaking from soul went from 3 evenly spaced reels to 3 reels + 2 photocards.
Evenly spaced, untyped slots cannot express that, so the plan lives in a small JSON file
(scheduled_ss/slots.json) read by BOTH the cheap workflow gate (scripts/is_due.py) and the
poster (src/post_ss.py) - one source of truth, no cron/offset arithmetic to keep in step.

Rules:
- each kind is counted separately: posting a card never satisfies a reel slot;
- owed slots are served oldest first;
- a kind only posts when its own minimum gap has passed since the last post of that kind,
  and the shared minimum gap has passed since the last post of any kind (no bunching).
Times are the runner's clock (UTC on GitHub).
"""
import json
from datetime import datetime
from pathlib import Path


def load(path: Path) -> dict:
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    slots = []
    for s in plan["slots"]:
        hh, mm = s["at"].split(":")
        slots.append((int(hh) * 60 + int(mm), s["kind"]))
    plan["slots"] = sorted(slots)
    return plan


def kind_of(item: dict, plan: dict) -> str | None:
    """Map an item's type to the plan kind it fills (e.g. reel + reel2 -> reel2)."""
    for kind, spec in plan["kinds"].items():
        if item.get("type") in spec["types"]:
            return kind
    return None


def _stamp(item) -> datetime | None:
    try:
        return datetime.fromisoformat(str(item["posted_at"]))
    except (KeyError, ValueError):
        return None


def _since(stamps: list[datetime], now: datetime) -> float:
    # A stamp in the future came from another timezone (a --force run on the Dhaka laptop
    # stamps +6h); treat it as "no recent post" rather than stalling every slot.
    past = [s for s in stamps if s <= now]
    return (now - max(past)).total_seconds() if past else float("inf")


def decide(items: list[dict], plan: dict, now: datetime | None = None) -> tuple[str | None, str]:
    """Return (kind to post now or None, one-line reason)."""
    now = now or datetime.now()
    today = now.strftime("%Y-%m-%d")
    minute = now.hour * 60 + now.minute

    posted = {k: 0 for k in plan["kinds"]}
    stamps = {k: [] for k in plan["kinds"]}
    all_stamps = []
    stock = {k: 0 for k in plan["kinds"]}
    for it in items:
        k = kind_of(it, plan)
        when = _stamp(it) if it.get("posted_at") else None
        if when:
            all_stamps.append(when)
        if k is None:
            continue
        if when:
            stamps[k].append(when)
            if str(it["posted_at"]).startswith(today):
                posted[k] += 1
        elif not it.get("skip"):
            stock[k] += 1

    # Oldest-first list of slots that have opened today but are not yet filled.
    used = dict(posted)
    owed = []
    for at, k in plan["slots"]:
        if at > minute:
            continue
        if used.get(k, 0) > 0:
            used[k] -= 1
        else:
            owed.append(k)
    if not owed:
        return None, f"nothing owed ({posted})"

    any_gap = plan.get("min_gap_any_minutes", 0) * 60
    since_any = _since(all_stamps, now)
    reasons = []
    for k in dict.fromkeys(owed):          # each owed kind once, oldest slot first
        if stock[k] == 0:
            reasons.append(f"{k} owed but queue empty")
            continue
        own_gap = plan["kinds"][k].get("min_gap_minutes", 0) * 60
        since_own = _since(stamps[k], now)
        if since_own < own_gap:
            reasons.append(f"{k} owed but last {k} {since_own/60:.0f}min ago")
            continue
        if since_any < any_gap:
            reasons.append(f"{k} owed but last post {since_any/60:.0f}min ago")
            continue
        return k, f"{k} owed (posted today {posted})"
    return None, "; ".join(reasons)
