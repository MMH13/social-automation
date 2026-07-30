"""Publish the next APPROVED YouTube item from youtube_queue/ (Data API v3).

Usage: python -m src.post_yt

Only touches items whose metadata.json status is "approved" (set via
scripts/review_youtube.py --approve <id>) — items still "pending_review" are left
alone. Marks the item "posted" right after the upload call succeeds, then deletes
the local video.mp4 (it's safely on YouTube now) to keep the repo lean.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .publishers import youtube_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "youtube_queue"
HISTORY_FILE = ROOT / "state" / "history.jsonl"


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def main() -> int:
    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    privacy_status = cfg.get("youtube", {}).get("privacy_status", "private")

    if not QUEUE_DIR.exists():
        log("post_yt: youtube_queue/ missing - nothing to post")
        return 0

    meta_paths = sorted(QUEUE_DIR.glob("item*/metadata.json"))
    approved = None
    for meta_path in meta_paths:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["status"] == "approved":
            approved = (meta, meta_path)
            break

    if approved is None:
        log("post_yt: no approved items - nothing to post")
        return 0

    meta, meta_path = approved
    folder = meta_path.parent
    video_path, thumb_path = folder / "video.mp4", folder / "thumbnail.jpg"

    if not youtube_publisher.configured():
        log("post_yt: YouTube credentials missing in .env")
        return 1
    if not video_path.exists():
        log(f"post_yt item{meta['id']}: video.mp4 missing - refusing to post")
        return 1

    try:
        url = youtube_publisher.publish_video(
            video_path, thumb_path if thumb_path.exists() else None,
            meta["title"], meta["description"], meta.get("tags", []),
            privacy_status=privacy_status,
        )
    except Exception as e:
        log(f"post_yt item{meta['id']}: FAILED ({e})")
        return 1

    meta["status"] = "posted"
    meta["posted_at"] = datetime.now().isoformat(timespec="seconds")
    meta["url"] = url
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "stamp": datetime.now().strftime("%Y%m%d_%H%M"),
            "platform": "youtube", "topic": meta["title"], "url": url,
        }, ensure_ascii=False) + "\n")

    video_path.unlink(missing_ok=True)  # it's on YouTube now - keep the repo lean
    log(f"post_yt item{meta['id']} ({meta['format']}): posted -> {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
