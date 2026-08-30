"""Post the next queued "Speaking from soul" item (quote card / reel) to FB + IG.

Usage: python -m src.post_ss
Mirrors post_pt.py but targets a second Facebook Page + Instagram account via the
SS_-prefixed env vars, so it runs independently of the Psychology Tube track.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .media.image_maker import make_quote_card
from .media.soul_reel import make_soul_reel
from .publishers import facebook_publisher, instagram_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_ss" / "content.json"
WATERMARK = "speaking from soul"
# Mamun picked SS-Narrator-Echo (kokoro am_echo) after comparing samples — single
# consistent narrator for the page rather than a rotation.
VOICES = ["am_echo"]
# 2026-08-28: 6 reels + 1 quote card per day (7 cron slots). The first run of each
# UTC day takes a quote, the rest take reels. Once the 77 pre-written cards are used
# up this degrades to reels-only on its own — no code change needed at that point.
DAILY_QUOTE = True

# 2026-08-29: GitHub only actually delivered 25-35% of this repo's scheduled runs
# (5-7 of 20/day across all workflows) — scheduled events are best-effort and get
# dropped under load. One-item-per-run therefore capped the page at ~2 posts/day.
#
# Backfilling to a flat daily total fixed the volume but front-loaded the whole day:
# on 2026-08-29 all 7 posts landed between 02:45 and 09:52, three of them inside two
# minutes, then nothing for 7+ hours. So the budget is paced against the clock instead
# of a day total — a run may only catch up to the slots that have actually passed.
# Slots are evenly spaced: 24h / DAILY_TARGET, so every post sits the same distance
# from its neighbours (7/day = one every 3h25m). SLOT_MINUTES must stay in sync with
# the cron in .github/workflows/post-ss.yml.
DAILY_TARGET = 7
SLOT_MINUTES = [round(i * 1440 / DAILY_TARGET) for i in range(DAILY_TARGET)]
GAP_SECONDS = 86400 // DAILY_TARGET          # 12342s = 3h25m, the even spacing
# Volume over perfect spacing (Mamun's call, 2026-08-31): capping at 1 post per run
# guaranteed the 3h25m gap but only yielded ~3 posts/day, because GitHub drops 4 of
# the 7 slots. A run may catch up on the slots it missed instead, sleeping between
# posts so a catch-up still spreads over hours rather than minutes — the 11-minute
# pairs came from a 10-minute sleep, not from catching up as such.
MAX_PER_RUN = 3
SPACING_SECONDS = 3600     # 1h between posts inside one catch-up run
# Only guards against a duplicate trigger double-posting; real spacing is the sleep
# above plus _due_by_now, so this stays small or it would block the catch-up itself.
MIN_GAP_SECONDS = 1200


def _posted_today(queue) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for m in queue if str(m.get("posted_at", "")).startswith(today))


def _due_by_now() -> int:
    """How many posts should have gone out by now — not the whole day's total."""
    now = datetime.now()
    minutes = now.hour * 60 + now.minute
    return sum(1 for m in SLOT_MINUTES if minutes >= m)


def _seconds_since_last(queue) -> float:
    stamps = [m["posted_at"] for m in queue if m.get("posted_at")]
    if not stamps:
        return float("inf")
    try:
        last = datetime.fromisoformat(max(stamps))
    except ValueError:
        return float("inf")
    gap = (datetime.now() - last).total_seconds()
    # A stamp in the future means it was written by a clock in another timezone —
    # a --force run from the Dhaka laptop stamps +6h ahead of the UTC runners, which
    # otherwise reads as "just posted" and blocks every slot until UTC catches up.
    # Treat that as no recent post rather than silently stalling the page.
    return float("inf") if gap < 0 else gap


def _quote_posted_today(queue) -> bool:
    """Has a quote card already gone out today? Date-based rather than tied to a
    specific cron hour, so a run GitHub delays or skips can't double-post one."""
    today = datetime.now().strftime("%Y-%m-%d")
    return any(m["type"] == "quote" and str(m.get("posted_at", "")).startswith(today)
               for m in queue)


def pick_next(queue):
    unposted = [m for m in queue if not m.get("posted_at")]
    if DAILY_QUOTE and not _quote_posted_today(queue):
        quote = next((m for m in unposted if m["type"] == "quote"), None)
        if quote:
            return quote
    # Reels only from here. Deliberately NO fallback to quote cards: reels run out
    # long before the cards do (~26 days vs ~77 at these rates), and falling back
    # would dump 7 static cards a day and burn the whole card stock in 11 days.
    # Returning None instead leaves the slot empty, which the low-queue alert flags.
    return next((m for m in unposted if m["type"] == "reel"), None)


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def save(queue) -> None:
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def post_one(queue, item, page_id, token, ig_id) -> int:
    kind, iid = item["type"], item["id"]
    media_dir = ROOT / "output" / "ss"

    body = " ".join(item["blocks"]) if kind == "reel" else item.get("text")
    if not body or len(body.strip()) < 8:
        log(f"post_ss item{iid} ({kind}): text looks corrupted ({body!r}) - refusing to post")
        return 1

    if kind == "reel":
        video = media_dir / f"item{iid:02d}.mp4"
        if not video.exists():
            voice = VOICES[iid % len(VOICES)]
            built = make_soul_reel(item["blocks"], item.get("bg_prompts", []), item.get("variant", 0),
                                   video, voice, watermark=WATERMARK)
            if built is None:
                log(f"post_ss item{iid}: reel render failed")
                return 1
        try:
            fb_url = facebook_publisher.publish_reel(item["fb_caption"], video, page_id=page_id, token=token)
        except Exception as e:
            log(f"post_ss item{iid}: FB reel failed ({e}); trying plain video")
            try:
                fb_url = facebook_publisher.publish_video(item["fb_caption"], video, page_id=page_id, token=token)
            except Exception as e2:
                log(f"post_ss item{iid}: FB video FAILED: {e2}")
                return 1
        item["posted_at"] = datetime.now().isoformat(timespec="seconds")
        item["fb_url"] = fb_url
        save(queue)
        log(f"post_ss item{iid} ({kind}): FB {fb_url}")
        if ig_id:
            try:
                ig = instagram_publisher.publish_reel(item["ig_caption"], video, ig_id=ig_id, token=token)
                item["ig_url"] = ig
                log(f"post_ss item{iid} ({kind}): IG {ig}")
            except Exception as e:
                item["ig_url"] = f"skipped: {e}"
                log(f"post_ss item{iid} ({kind}): IG skipped: {e}")
        else:
            item["ig_url"] = "skipped: SS_IG_USER_ID not set"
        save(queue)
    else:  # quote card image
        image = media_dir / f"item{iid:02d}.jpg"
        if not image.exists():
            make_quote_card(item["text"], image, item.get("variant", 0), watermark=WATERMARK)
        try:
            fb_url = facebook_publisher.publish(item["fb_caption"], image, page_id=page_id, token=token)
        except Exception as e:
            log(f"post_ss item{iid}: FB FAILED: {e}")
            return 1
        item["posted_at"] = datetime.now().isoformat(timespec="seconds")
        item["fb_url"] = fb_url
        save(queue)
        log(f"post_ss item{iid} ({kind}): FB {fb_url}")
        if ig_id:
            try:
                fb_post_id = fb_url.rsplit("/", 1)[-1]
                ig = instagram_publisher.publish(item["ig_caption"], image, fb_post_id=fb_post_id,
                                                  ig_id=ig_id, token=token)
                item["ig_url"] = ig
                log(f"post_ss item{iid} ({kind}): IG {ig}")
            except Exception as e:
                item["ig_url"] = f"FAILED: {e}"
                log(f"post_ss item{iid} ({kind}): IG FAILED: {e}")
        else:
            item["ig_url"] = "skipped: SS_IG_USER_ID not set"
        save(queue)

    with open(ROOT / "state" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": datetime.now().strftime("%Y%m%d_%H%M"), "platform": "fb+ig (ss)",
                            "topic": f"ss queue #{iid} ({kind})", "url": item["fb_url"]},
                           ensure_ascii=False) + "\n")
    return 0


def main() -> int:
    load_dotenv(ROOT / ".env")
    page_id = os.environ.get("SS_FB_PAGE_ID")
    token = os.environ.get("SS_FB_PAGE_ACCESS_TOKEN")
    ig_id = os.environ.get("SS_IG_USER_ID")

    if not page_id or not token:
        log("post_ss: SS_FB_PAGE_ID / SS_FB_PAGE_ACCESS_TOKEN not set - page not created/granted yet")
        return 1

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    already = _posted_today(queue)
    due = _due_by_now()
    want = min(max(due - already, 0), MAX_PER_RUN)

    # `--force` posts one item regardless of pacing — for filling a gap by hand after
    # an outage. It deliberately still marks posted_at, so the queue stays consistent
    # and the next scheduled run counts it.
    if "--force" in sys.argv:
        log(f"post_ss: --force, posting 1 now ({already} posted today, {due} due by now)")
        want = 1
    elif want == 0:
        log(f"post_ss: {already} posted today, {due}/{DAILY_TARGET} due by now "
            f"- nothing due this run")
        return 0

    gap = _seconds_since_last(queue)
    if "--force" not in sys.argv and gap < MIN_GAP_SECONDS:
        log(f"post_ss: last post was {gap/60:.0f}min ago (<{MIN_GAP_SECONDS//60}min) "
            f"- skipping so posts don't bunch")
        return 0

    log(f"post_ss: {already} posted today, {due}/{DAILY_TARGET} due by now "
        f"- posting up to {want} this run")

    posted = 0
    for n in range(want):
        if n:
            # Spread a catch-up across hours; back-to-back reels compete for reach.
            log(f"post_ss: waiting {SPACING_SECONDS//60}min before the next post")
            time.sleep(SPACING_SECONDS)
        # Re-pick each pass: the previous post mutated the queue, and the quote/reel
        # choice depends on what has gone out today.
        item = pick_next(queue)
        if item is None:
            log("post_ss: queue empty - nothing further to post")
            break
        rc = post_one(queue, item, page_id, token, ig_id)
        if rc != 0:
            # Stop on the first failure so a broken item can't burn the whole
            # day's budget retrying siblings; the next run picks up from here.
            log(f"post_ss: stopping this run after a failure ({posted} posted)")
            return rc
        posted += 1

    remaining = sum(1 for m in queue if not m.get("posted_at"))
    reels_left = sum(1 for m in queue if not m.get("posted_at") and m["type"] == "reel")
    log(f"post_ss: posted {posted} this run | {remaining} left in queue ({reels_left} reels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
