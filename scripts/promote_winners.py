# -*- coding: utf-8 -*-
"""Promote the queue siblings of a breakout reel to the front of the Psychology Tube queue.

Reel views are a power law here: ~8% of reels broke out (800-5,400 plays) while the median
stayed ~200, and the breakouts were not explained by watch time or shares. So the one lever
we have is to react fast: when a recent reel passes THRESHOLD plays, pull the next unposted
reels on the same theme to the front so the page rides that interest while it is live.

Usage: python scripts/promote_winners.py [--dry-run]
Needs FB_PAGE_ACCESS_TOKEN in the environment (or .env). Safe to re-run: a reel is only
acted on once (item["promoted"]), and the queue is only rewritten when something moved.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "scheduled_pt" / "content.json"
GRAPH = "https://graph.facebook.com/v21.0"

THRESHOLD = 1000            # plays that count as a breakout
LOOKBACK_HOURS = 96         # only reels posted this recently can trigger a promotion
SIBLINGS_PER_WINNER = 3
MAX_WINNERS_PER_RUN = 2

THEMES = {
    "letting_go": r"let go|past|miss |missing|goodbye|come back|apolog|closure|holding on|left|nostalg|grudge|forgive|over someone|walk away|move on",
    "healing": r"heal|rebuild|recover|burnout|trying harder|cry|growing|grow |backwards|hard year|numb|strong",
    "anxiety_calm": r"anxious|calm|peace|overthink|restless|unsettled|rest|quiet|slow|bad news|problems",
    "relationships": r"attract|wrong people|attached|trust|love|relationship|close to|pull away|lonely|alone|choose|stay",
}


def theme_of(item) -> str:
    if item.get("theme"):
        return item["theme"]
    t = item.get("title", "").lower()
    for name, pat in THEMES.items():
        if re.search(pat, t):
            return name
    return "other"


def plays(reel_id: str, token: str) -> int | None:
    r = requests.get(f"{GRAPH}/{reel_id}/video_insights",
                     params={"access_token": token, "metric": "blue_reels_play_count"}, timeout=40)
    try:
        return r.json()["data"][0]["values"][0]["value"]
    except (KeyError, IndexError, ValueError):
        return None


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main() -> int:
    dry = "--dry-run" in sys.argv
    load_env()
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    if not token:
        print("promote_winners: FB_PAGE_ACCESS_TOKEN missing")
        return 1

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=LOOKBACK_HOURS)

    recent = []
    for it in queue:
        if it.get("type") != "narrated" or not it.get("posted_at") or it.get("promoted"):
            continue
        try:
            if datetime.fromisoformat(it["posted_at"]) < cutoff:
                continue
        except ValueError:
            continue
        m = re.search(r"/reel/(\d+)", it.get("fb_url") or "")
        if m:
            recent.append((it, m.group(1)))

    winners = []
    for it, rid in recent:
        n = plays(rid, token)
        print(f"  #{it['id']} {n} plays  {it['title'][:50]}")
        if n is not None and n >= THRESHOLD:
            winners.append((n, it))
    winners.sort(key=lambda w: -w[0])
    print(f"promote_winners: {len(recent)} recent reel(s), {len(winners)} at or above {THRESHOLD}")

    moved = 0
    for n, win in winners[:MAX_WINNERS_PER_RUN]:
        theme = theme_of(win)
        unposted = [i for i in queue if i.get("type") == "narrated" and not i.get("posted_at")]
        front = {id(i) for i in unposted[:SIBLINGS_PER_WINNER]}
        sibs = [i for i in unposted if theme_of(i) == theme and id(i) not in front][:SIBLINGS_PER_WINNER]
        print(f"  winner #{win['id']} ({n} plays, theme={theme}): pulling "
              f"{[s['id'] for s in sibs]} to the front")
        win["promoted"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        if sibs:
            ids = {id(s) for s in sibs}
            queue = [i for i in queue if id(i) not in ids]
            first = next(k for k, i in enumerate(queue)
                         if i.get("type") == "narrated" and not i.get("posted_at"))
            queue[first:first] = sibs
            moved += len(sibs)

    if winners and not dry:
        QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"promote_winners: queue rewritten, {moved} item(s) moved")
    elif winners:
        print(f"promote_winners: dry run, {moved} item(s) would move")
    return 0


if __name__ == "__main__":
    sys.exit(main())
