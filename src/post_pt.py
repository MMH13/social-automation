"""Post the next queued Psychology Tube item (meme / psych card / status / reel) to FB + IG.

Usage: python -m src.post_pt
Replaces post_meme as the page's queue consumer. Renders media per type, posts to
Facebook first, then Instagram (CDN reuse for images; Cloudinary for reels when
configured). Marks the item posted right after the FB publish so nothing double-posts.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .media.image_maker import make_gradient_status, make_minimal_dark, make_psych_card
from .media.reel_maker import make_reel
from .publishers import facebook_publisher, instagram_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_pt" / "content.json"


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def save(queue) -> None:
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    load_dotenv(ROOT / ".env")
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    item = next((m for m in queue if not m.get("posted_at")), None)
    if item is None:
        log("post_pt: queue empty - nothing to post")
        return 0
    if not facebook_publisher.configured():
        log("post_pt: facebook credentials missing")
        return 1

    kind, iid = item["type"], item["id"]
    media_dir = ROOT / "output" / "pt"

    if kind == "reel":
        video = media_dir / f"item{iid:02d}.mp4"
        if not video.exists() and make_reel(item["text"], item.get("variant", 0), video) is None:
            log(f"post_pt item{iid}: reel render failed")
            return 1
        try:
            fb_url = facebook_publisher.publish_reel(item["ig_caption"], video)
        except Exception as e:
            log(f"post_pt item{iid}: FB reel failed ({e}); trying plain video")
            try:
                fb_url = facebook_publisher.publish_video(item["ig_caption"], video)
            except Exception as e2:
                log(f"post_pt item{iid}: FB video FAILED: {e2}")
                return 1
        item["posted_at"] = datetime.now().isoformat(timespec="seconds")
        item["fb_url"] = fb_url
        save(queue)
        log(f"post_pt item{iid} (reel): FB {fb_url}")
        try:
            ig = instagram_publisher.publish_reel(item["ig_caption"], video)
            item["ig_url"] = ig
            log(f"post_pt item{iid} (reel): IG {ig}")
        except Exception as e:
            item["ig_url"] = f"skipped: {e}"
            log(f"post_pt item{iid} (reel): IG skipped: {e}")
        save(queue)
    else:
        image = media_dir / f"item{iid:02d}.jpg"
        if not image.exists():
            if kind == "meme":
                make_minimal_dark(item["text"], image)
            elif kind == "psych":
                make_psych_card(item["text"], image)
            else:  # status
                make_gradient_status(item["text"], item.get("variant", 0), image)
        try:
            fb_url = facebook_publisher.publish(item["fb_caption"], image)
        except Exception as e:
            log(f"post_pt item{iid}: FB FAILED: {e}")
            return 1
        item["posted_at"] = datetime.now().isoformat(timespec="seconds")
        item["fb_url"] = fb_url
        save(queue)
        log(f"post_pt item{iid} ({kind}): FB {fb_url}")
        try:
            fb_post_id = fb_url.rsplit("/", 1)[-1]
            ig = instagram_publisher.publish(item["ig_caption"], image, fb_post_id=fb_post_id)
            item["ig_url"] = ig
            log(f"post_pt item{iid} ({kind}): IG {ig}")
        except Exception as e:
            item["ig_url"] = f"FAILED: {e}"
            log(f"post_pt item{iid} ({kind}): IG FAILED: {e}")
        save(queue)

    with open(ROOT / "state" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": datetime.now().strftime("%Y%m%d_%H%M"), "platform": "fb+ig",
                            "topic": f"pt queue #{iid} ({kind})", "url": item["fb_url"]},
                           ensure_ascii=False) + "\n")
    remaining = sum(1 for m in queue if not m.get("posted_at"))
    log(f"post_pt: {remaining} item(s) left in queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
