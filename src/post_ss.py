"""Post the next queued "Speaking from soul" item (reel / black photocard) to FB + IG.

Usage: python -m src.post_ss [--force [--kind=card2]]
Mirrors post_pt.py but targets a second Facebook Page + Instagram account via the
SS_-prefixed env vars, so it runs independently of the Psychology Tube track.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .media.image_maker import make_quote_card
from .media.photocard import make_photocard
from .media.soul_reel import make_soul_reel
from .media.soul_reel_v2 import make_illustrated_reel
from .publishers import facebook_publisher, instagram_publisher
from . import slot_plan

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_ss" / "content.json"
# 2026-11-19: typed daily plan (3 reels + 2 black 16:9 photocards), shared with the gate.
PLAN_FILE = ROOT / "scheduled_ss" / "slots.json"
ART_DIR = ROOT / "assets" / "ss_art"
WATERMARK = "speaking from soul"
# 2026-09-27: switched from Echo to Michael after Mamun compared it against several
# deep/pitch-shifted candidates on a matched line ("Pick up all your pieces and
# start over.") and picked "am_michael deep" — the actual pitch-down effect lives in
# soul_reel.py (PITCH_RATIO), not here; this just selects the base kokoro voice.
# 2026-11-17: Mamun asked for 4-5 different voices and told me to pick the best five.
# Chosen on the kokoro model card's quality grades (I cannot audition audio): af_bella A-,
# bf_emma B-, am_michael/am_puck C+, bm_george C - three men, two women, none shared with
# Psychology Tube's rotation. Each queued reel carries its own "voice"; this list is the
# fallback and the set the workflow pre-downloads.
# 2026-11-17: bm_george dropped - Mamun found him less clear than the others; replaced by
# am_echo (his own pick for this page in August).
VOICES = ["am_michael", "af_bella", "am_puck", "bf_emma", "am_echo"]
# Cadence history (7/day with a daily quote card -> 3 reels/day 8h apart on 2026-10-28 after
# a four-day distribution blackout -> 3 reels + 2 photocards on 2026-11-19) is in git log.
# The daily plan, per-kind minimum gaps and the shared anti-bunching gap now live in
# scheduled_ss/slots.json, read here and by the workflow gate through src/slot_plan.py.
# One post per run: the workflow polls every 15 minutes, so a late slot is picked up by a
# later run instead of being burned down as a back-to-back pair.


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


def pick_next(queue, kind: str = "reel2"):
    """Next unposted item of the given plan kind. Never falls back to another kind: an
    empty kind leaves its slot empty (the low-queue alert flags it) instead of dumping
    the other kind's stock."""
    unposted = [m for m in queue if not m.get("posted_at") and not m.get("skip")]
    if kind == "card2":
        return next((m for m in unposted if m["type"] == "card2"), None)
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
            voice = item.get("voice") or VOICES[iid % len(VOICES)]
            item["voice"] = voice
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
            if kind == "card2":
                make_photocard(item["text"], image, watermark=WATERMARK)
            else:
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
    plan = slot_plan.load(PLAN_FILE)

    # `--force` posts one item now regardless of the plan - for filling a gap by hand after
    # an outage (`--force --kind=card2` for a card; reel by default). It still marks
    # posted_at, so the queue stays consistent and the next scheduled run counts it.
    if "--force" in sys.argv:
        kind = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--kind=")), "reel2")
        log(f"post_ss: --force, posting one {kind} now")
    else:
        kind, why = slot_plan.decide(queue, plan)
        if kind is None:
            log(f"post_ss: {why} - nothing to post this run")
            return 0
        log(f"post_ss: {why} - posting one")

    item = pick_next(queue, kind)
    if item is None:
        log(f"post_ss: no postable {kind} left in the queue")
        return 0
    rc = post_one(queue, item, page_id, token, ig_id)
    if rc != 0:
        return rc

    reels_left = sum(1 for m in queue if not m.get("posted_at") and m["type"] in ("reel", "reel2"))
    cards_left = sum(1 for m in queue if not m.get("posted_at") and m["type"] == "card2")
    log(f"post_ss: posted 1 {kind} | left: {reels_left} reels, {cards_left} cards")
    return 0

if __name__ == "__main__":
    sys.exit(main())
