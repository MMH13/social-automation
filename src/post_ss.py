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
from .media.soul_reel_v2 import make_illustrated_reel
from .publishers import facebook_publisher, instagram_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_ss" / "content.json"
ART_DIR = ROOT / "assets" / "ss_art"
WATERMARK = "speaking from soul"
# 2026-09-27: switched from Echo to Michael after Mamun compared it against several
# deep/pitch-shifted candidates on a matched line ("Pick up all your pieces and
# start over.") and picked "am_michael deep" — the actual pitch-down effect lives in
# soul_reel.py (PITCH_RATIO), not here; this just selects the base kokoro voice.
VOICES = ["am_michael"]
# 2026-08-28: 6 reels + 1 quote card per day (7 cron slots). The first run of each
# UTC day takes a quote, the rest take reels. Once the 77 pre-written cards are used
# up this degrades to reels-only on its own — no code change needed at that point.
DAILY_QUOTE = False       # 2026-10-28: reels only (see the cadence note below)

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
# 2026-10-28: cut to 3 reels/day, 8 hours apart, no quote card. Plays per reel were flat at
# ~200 (= the follower count) and from 2026-10-23 05:31 to 2026-10-26 22:58 UTC every reel
# got 0-2 plays - a four-day distribution blackout while the page posted 7/day with pairs
# 11 minutes apart. Fewer, spaced-out posts give each reel a clean first-hour test.
# Slots 01:00 / 09:00 / 17:00 UTC (9pm / 5am / 1pm ET). Keep SLOT_OFFSET_HOURS in step with
# --offset in post-ss.yml's gate (scripts/is_due.py).
DAILY_TARGET = 3
SLOT_OFFSET_HOURS = 1
GAP_SECONDS = 86400 // DAILY_TARGET          # 28800s = 8h
SLOT_MINUTES = sorted(((SLOT_OFFSET_HOURS * 3600 + i * GAP_SECONDS) % 86400) // 60
                      for i in range(DAILY_TARGET))
# 2026-09-01: the workflow polls every 15 minutes instead of firing at the 7 slots,
# so a slot is picked up shortly after it opens and there is no backlog to burn down.
# One post per run is therefore enough, and the hour-long in-run sleep that used to
# spread a catch-up is gone — spacing now comes from the schedule itself, which is
# both better spaced and ~10x cheaper in runner minutes.
#
# 2026-10-01: that assumption broke down. GitHub is delivering far fewer of this
# repo's */15min triggers than it used to (measured 4-6 actual runs/day instead of
# ~96 - the same per-repo schedule-delivery cap documented for PT, now worse here
# too), landing only 4-6 posts/day against the 7 target even though every run
# succeeds. Raised to 2/run + a spacing gap, mirroring the fix already proven for
# PT (post_pt.py), so a delivered trigger can burn down more than one missed slot
# instead of just the one closest to it.
MAX_PER_RUN = 1          # 3/day at 8h spacing: a late run posts one, never a pair
SPACING_SECONDS = 600
# Guards against two runs overlapping near a slot boundary and double-posting.
MIN_GAP_SECONDS = 6 * 3600


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


def _scene_files() -> dict[int, Path]:
    """scene id -> image path, for scenes whose art file is actually in the repo."""
    try:
        meta = json.loads((ART_DIR / "scenes.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {s["id"]: ART_DIR / s["file"] for s in meta["scenes"] if (ART_DIR / s["file"]).exists()}


def _playable(item, scene_files) -> bool:
    """A reel2 item can only render once every scene it uses has its art in the repo."""
    if item["type"] != "reel2":
        return True
    return all(sid in scene_files for sid in item["scenes"])


def pick_next(queue):
    unposted = [m for m in queue if not m.get("posted_at") and not m.get("skip")]
    if DAILY_QUOTE and not _quote_posted_today(queue):
        quote = next((m for m in unposted if m["type"] == "quote"), None)
        if quote:
            return quote
    # Reels only from here. Deliberately NO fallback to quote cards: reels run out
    # long before the cards do (~26 days vs ~77 at these rates), and falling back
    # would dump 7 static cards a day and burn the whole card stock in 11 days.
    # Returning None instead leaves the slot empty, which the low-queue alert flags.
    scene_files = _scene_files()
    return next((m for m in unposted
                 if m["type"] in ("reel", "reel2") and _playable(m, scene_files)), None)


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

    if kind == "reel":
        body = " ".join(item["blocks"])
    elif kind == "reel2":
        body = " ".join(item["phrases"])
    else:
        body = item.get("text")
    if not body or len(body.strip()) < 8:
        log(f"post_ss item{iid} ({kind}): text looks corrupted ({body!r}) - refusing to post")
        return 1

    if kind in ("reel", "reel2"):
        video = media_dir / f"item{iid:02d}.mp4"
        if not video.exists():
            voice = VOICES[iid % len(VOICES)]
            if kind == "reel2":
                files = _scene_files()
                built = make_illustrated_reel(item["phrases"], [files[sid] for sid in item["scenes"]],
                                              item.get("variant", 0), video, voice, watermark=WATERMARK)
            else:
                built = make_soul_reel(item["blocks"], item.get("bg_prompts", []), item.get("variant", 0),
                                       video, voice, watermark=WATERMARK)
            if built is None:
                log(f"post_ss item{iid}: reel render failed")
                if kind == "reel2":
                    # A reel that cannot render must not block the whole queue: after two
                    # failed attempts it is skipped so the next item gets its turn.
                    item["render_failures"] = item.get("render_failures", 0) + 1
                    if item["render_failures"] >= 2:
                        item["skip"] = True
                        log(f"post_ss item{iid}: skipped after {item['render_failures']} failed renders")
                    save(queue)
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
    reels_left = sum(1 for m in queue if not m.get("posted_at") and m["type"] in ("reel", "reel2"))
    log(f"post_ss: posted {posted} this run | {remaining} left in queue ({reels_left} reels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
