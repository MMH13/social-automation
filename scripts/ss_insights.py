# -*- coding: utf-8 -*-
"""Pull per-reel engagement for the Speaking from soul page into a JSON file.

For every posted reel it records plays, average watch time, followers gained by that
reel, reactions, and how much of the audience is still watching at 3s / 5s / 10s. Used to
decide which themes, hooks and runtimes to write more of - not run by any workflow.

Usage: python scripts/ss_insights.py <out.json> [--since=YYYY-MM-DD] [--types=reel,reel2]
Needs SS_FB_PAGE_ACCESS_TOKEN in .env (read-only calls).
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
GRAPH = "https://graph.facebook.com/v21.0"
METRICS = {
    "plays": "blue_reels_play_count",
    "avg_watch_ms": "post_video_avg_time_watched",
    "followers_gained": "post_video_followers",
    "reactions": "post_video_likes_by_reaction_type",
    "retention": "post_video_retention_graph",
    "social": "post_video_social_actions",
}


def metric(vid: str, name: str, token: str):
    for attempt in range(3):
        try:
            r = requests.get(f"{GRAPH}/{vid}/video_insights",
                             params={"metric": name, "access_token": token}, timeout=40)
        except requests.RequestException:
            time.sleep(2)
            continue
        if r.ok and r.json().get("data"):
            return r.json()["data"][0]["values"][0]["value"]
        if r.status_code in (400, 403):
            return None
        time.sleep(1.5)
    return None


def fetch(item: dict, token: str) -> dict:
    vid = item["fb_url"].rstrip("/").split("/")[-1]
    out = {"id": item["id"], "type": item["type"], "posted_at": item["posted_at"], "video_id": vid}
    for key, name in METRICS.items():
        out[key] = metric(vid, name, token)
    ret = out.get("retention") or {}
    for sec in (3, 5, 10):
        out[f"ret_{sec}s"] = ret.get(str(sec))
    out["reactions_total"] = sum((out.get("reactions") or {}).values()) if isinstance(out.get("reactions"), dict) else None
    out["shares"] = (out.get("social") or {}).get("SHARE") if isinstance(out.get("social"), dict) else None
    out["comments"] = (out.get("social") or {}).get("COMMENT") if isinstance(out.get("social"), dict) else None
    out.pop("retention", None)
    return out


def main() -> int:
    load_dotenv(ROOT / ".env")
    token = os.environ["SS_FB_PAGE_ACCESS_TOKEN"]
    out_path = Path(sys.argv[1])
    since = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--since=")), "0000")
    types = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--types=")), "reel,reel2").split(",")
    queue = json.loads((ROOT / "scheduled_ss" / "content.json").read_text(encoding="utf-8"))
    todo = [m for m in queue if m.get("posted_at", "") >= since and m["type"] in types
            and str(m.get("fb_url", "")).startswith("https://www.facebook.com/reel/")]
    print(f"fetching insights for {len(todo)} reels")
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(lambda m: fetch(m, token), todo))
    out_path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {out_path} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
