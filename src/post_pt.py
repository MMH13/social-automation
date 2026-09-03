"""Post the next queued Psychology Tube item (meme / psych card / status / reel) to FB + IG.

Usage: python -m src.post_pt
Replaces post_meme as the page's queue consumer. Renders media per type, posts to
Facebook first, then Instagram (CDN reuse for images; Cloudinary for reels when
configured). Marks the item posted right after the FB publish so nothing double-posts.
"""
import json
import sys
import time
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

# 2026-08-31: the daily health check found this page publishing 5 of 10. Same cause as
# Speaking from soul had - GitHub delivers only a fraction of the scheduled slots, and
# one-post-per-run turns every dropped slot into a permanently lost post. A run may now
# catch up on the slots that have already passed.
DAILY_POSTS = 10
GAP_SECONDS = 86400 // DAILY_POSTS                      # 8640s = 2h24m
SLOT_MINUTES = [(i * GAP_SECONDS) // 60 for i in range(DAILY_POSTS)]
# 2026-09-01: the workflow polls every 15 minutes instead of firing at the 10 slots.
# 2026-09-03: even so, this page was still landing at 6-7/10 - GitHub was delivering
# only ~9 scheduled runs/day (measured: Speaking from soul got almost the same 9-10,
# despite asking for fewer posts, which points to a per-repo cap on delivered *
# schedule* events rather than anything specific to this workflow). With cap=1 that
# ceiling IS the daily total. Replaying the actual delivered run times from 2026-09-02
# through the real picker: cap=1 -> 7/10, cap=2 with a 10 min in-run sleep -> 10/10.
MAX_PER_RUN = 2
SPACING_SECONDS = 600
MIN_GAP_SECONDS = 1200


def category(item) -> str:
    return "narrated" if item["type"] == "narrated" else "other"


def _posted_today(queue) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for m in queue if str(m.get("posted_at", "")).startswith(today))


def _due_by_now() -> int:
    now = datetime.now()
    return sum(1 for s in SLOT_MINUTES if now.hour * 60 + now.minute >= s)


def _seconds_since_last(queue) -> float:
    stamps = [m["posted_at"] for m in queue if m.get("posted_at")]
    if not stamps:
        return float("inf")
    try:
        last = datetime.fromisoformat(max(stamps))
    except ValueError:
        return float("inf")
    gap = (datetime.now() - last).total_seconds()
    # A stamp from a laptop in another timezone reads as "just posted" and would
    # otherwise block every slot until the runner's UTC clock catches up.
    return float("inf") if gap < 0 else gap


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


def post_one(queue, item) -> int:
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
    return 0


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not facebook_publisher.configured():
        log("post_pt: facebook credentials missing")
        return 1

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    already = _posted_today(queue)
    due = _due_by_now()
    want = min(max(due - already, 0), MAX_PER_RUN)
    if want == 0:
        log(f"post_pt: {already} posted today, {due}/{DAILY_POSTS} due by now "
            f"- nothing due this run")
        return 0

    gap = _seconds_since_last(queue)
    if gap < MIN_GAP_SECONDS:
        log(f"post_pt: last post was {gap/60:.0f}min ago - skipping so posts don't bunch")
        return 0

    log(f"post_pt: {already} posted today, {due}/{DAILY_POSTS} due by now "
        f"- posting up to {want} this run")

    posted = 0
    for n in range(want):
        if n:
            log(f"post_pt: waiting {SPACING_SECONDS//60}min before the next post")
            time.sleep(SPACING_SECONDS)
        item = pick_next(queue)
        if item is None:
            log("post_pt: queue empty - nothing further to post")
            break
        rc = post_one(queue, item)
        if rc != 0:
            log(f"post_pt: stopping this run after a failure ({posted} posted)")
            return rc
        posted += 1

    remaining = sum(1 for m in queue if not m.get("posted_at"))
    log(f"post_pt: posted {posted} this run | {remaining} item(s) left in queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
