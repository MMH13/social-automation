"""Post the next queued Psychology Tube photocard (black 16:9) to FB + IG.

Usage: python -m src.post_pt_card [--force]
2026-11-20: 14-day test of original text cards beside the 3 daily reels. Own queue
(scheduled_pt/cards.json) and own workflow so card runs never touch the reel queue or its
lock. Cards flagged "skip" are held back (drafts awaiting approval). Same renderer as
Speaking from soul (src/media/photocard.py) so the look Mamun approved is identical.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from . import slot_plan
from .media.photocard import make_photocard
from .publishers import facebook_publisher, instagram_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_pt" / "cards.json"
PLAN_FILE = ROOT / "scheduled_pt" / "cards_slots.json"
WATERMARK = "@psychology.tube"


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
    if not facebook_publisher.configured():
        log("post_pt_card: facebook credentials missing")
        return 1
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))

    if "--force" in sys.argv:
        log("post_pt_card: --force, posting one card now")
    else:
        kind, why = slot_plan.decide(queue, slot_plan.load(PLAN_FILE))
        if kind is None:
            log(f"post_pt_card: {why} - nothing to post this run")
            return 0
        log(f"post_pt_card: {why} - posting one")

    item = next((m for m in queue if m["type"] == "card" and not m.get("posted_at")
                 and not m.get("skip")), None)
    if item is None:
        log("post_pt_card: no postable card left in the queue")
        return 0

    iid, text = item["id"], item.get("text", "")
    if len(text.strip()) < 20:
        log(f"post_pt_card item{iid}: text looks corrupted ({text!r}) - refusing to post")
        return 1
    image = ROOT / "output" / "pt" / f"card{iid:03d}.jpg"
    make_photocard(text, image, watermark=WATERMARK)
    try:
        fb_url = facebook_publisher.publish(item["fb_caption"], image)
    except Exception as e:
        log(f"post_pt_card item{iid}: FB FAILED: {e}")
        return 1
    item["posted_at"] = datetime.now().isoformat(timespec="seconds")
    item["fb_url"] = fb_url
    save(queue)
    log(f"post_pt_card item{iid}: FB {fb_url}")
    try:
        ig = instagram_publisher.publish(item["ig_caption"], image, fb_post_id=fb_url.rsplit("/", 1)[-1])
        item["ig_url"] = ig
        log(f"post_pt_card item{iid}: IG {ig}")
    except Exception as e:
        item["ig_url"] = f"FAILED: {e}"
        log(f"post_pt_card item{iid}: IG FAILED: {e}")
    save(queue)
    with open(ROOT / "state" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": datetime.now().strftime("%Y%m%d_%H%M"), "platform": "fb+ig",
                            "topic": f"pt card #{iid}", "url": item["fb_url"]}, ensure_ascii=False) + "\n")
    left = sum(1 for m in queue if m["type"] == "card" and not m.get("posted_at") and not m.get("skip"))
    log(f"post_pt_card: posted 1 card | {left} postable left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
