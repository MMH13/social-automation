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
from .media.narrated_video import make_narrated
from .media.reel_maker import make_reel
from .publishers import facebook_publisher, instagram_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_pt" / "content.json"

# Set 2026-08-28: NARRATED REELS ONLY, 10/day. Nothing else posts.
# Explicitly no fallback to meme/psych/status/reel items - if the narrated pool runs
# dry the page goes quiet rather than posting a different format. The ~50 remaining
# non-narrated items stay in the queue untouched (not deleted) in case the mix is ever
# wanted again. The low-queue alert is the safety net here: it warns before the pool
# empties, since nothing else will cover the gap.
DAILY_TARGET = {"narrated": 10}
POST_TYPE = "narrated"


def category(item) -> str:
    return "narrated" if item["type"] == "narrated" else "other"


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def save(queue) -> None:
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def pick_next(queue):
    """Pick the next unposted narrated item. Narrated-only by design: other formats
    are never selected, even when the narrated pool is empty - the page stays quiet
    instead of silently switching format."""
    item = next((m for m in queue
                 if not m.get("posted_at") and m["type"] == POST_TYPE), None)
    if item is None:
        other_left = sum(1 for m in queue
                         if not m.get("posted_at") and m["type"] != POST_TYPE)
        log(f"post_pt: no {POST_TYPE} items left "
            f"({other_left} non-{POST_TYPE} item(s) in the queue are intentionally skipped)")
    return item


def main() -> int:
    load_dotenv(ROOT / ".env")
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    item = pick_next(queue)
    if item is None:
        log("post_pt: queue empty - nothing to post")
        return 0
    if not facebook_publisher.configured():
        log("post_pt: facebook credentials missing")
        return 1

    kind, iid = item["type"], item["id"]
    media_dir = ROOT / "output" / "pt"

    # A queue-builder bug once truncated 5 psych cards to a single character and they
    # published as "A" with the caption "n". Refuse to post obvious garbage.
    body = item.get("title") if kind == "narrated" else item.get("text")
    if not body or len(body.strip()) < 12:
        log(f"post_pt item{iid} ({kind}): text looks corrupted ({body!r}) - refusing to post")
        return 1

    if kind in ("reel", "narrated"):
        video = media_dir / f"item{iid:02d}.mp4"
        if not video.exists():
            if kind == "narrated":
                built = make_narrated(
                    item["title"], item["points"], video,
                    variant=item.get("variant", 0),
                    bg_query=item.get("bg_query"),
                    outro=item.get("outro", "Save this. Follow for more."),
                )
            else:
                built = make_reel(
                    item["text"], item.get("variant", 0), video, item.get("bg_query")
                )
            if built is None:
                log(f"post_pt item{iid}: {kind} render failed")
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
        log(f"post_pt item{iid} ({kind}): FB {fb_url}")
        try:
            ig = instagram_publisher.publish_reel(item["ig_caption"], video)
            item["ig_url"] = ig
            log(f"post_pt item{iid} ({kind}): IG {ig}")
        except Exception as e:
            item["ig_url"] = f"skipped: {e}"
            log(f"post_pt item{iid} ({kind}): IG skipped: {e}")
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
