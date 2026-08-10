"""Post the next queued Mamun Hossain item to Facebook.

Usage: python -m src.post_mh
FB-only for now (no Instagram — page has no linked IG yet). Uses the hook-card +
comment-thread format: publish a bold text-card post, then follow up with the
actual resource list / numbered steps as nested comments, matching how
NasirUShamim's page structures its highest-performing posts.

Requires MH_PAGE_ID / MH_PAGE_ACCESS_TOKEN (separate from Psychology Tube's
FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN — this is a different Page).
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .media.html_card import make_hook_card
from .publishers import facebook_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_mh" / "content.json"
PAGE_ID_VAR, TOKEN_VAR = "MH_PAGE_ID", "MH_PAGE_ACCESS_TOKEN"


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
    if not facebook_publisher.configured(PAGE_ID_VAR, TOKEN_VAR):
        log("post_mh: Mamun Hossain page credentials missing")
        return 1

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    item = next((m for m in queue if not m.get("posted_at")), None)
    if item is None:
        log("post_mh: queue empty - nothing to post")
        return 0

    iid = item["id"]
    body = item.get("hook")
    if not body or len(body.strip()) < 12:
        log(f"post_mh item{iid}: hook text looks corrupted ({body!r}) - refusing to post")
        return 1

    page_id = os.environ[PAGE_ID_VAR]
    token = os.environ[TOKEN_VAR]

    image = ROOT / "output" / "mh" / f"item{iid:02d}.png"
    if not image.exists():
        make_hook_card(
            item["hook"], image,
            bg=item.get("bg", "#c00000"),
            highlight=item.get("highlight"),
        )

    try:
        fb_url = facebook_publisher.publish(item.get("caption", ""), image, page_id=page_id, token=token)
    except Exception as e:
        log(f"post_mh item{iid}: FB FAILED: {e}")
        return 1

    item["posted_at"] = datetime.now().isoformat(timespec="seconds")
    item["fb_url"] = fb_url
    save(queue)
    log(f"post_mh item{iid}: FB {fb_url}")

    comments = item.get("comments") or []
    if comments:
        post_id = fb_url.rsplit("/", 1)[-1]
        try:
            facebook_publisher.comment_thread(post_id, comments, page_id=page_id, token=token)
            log(f"post_mh item{iid}: posted {len(comments)} comment(s) with the value list")
        except Exception as e:
            log(f"post_mh item{iid}: comment thread FAILED (post still live): {e}")

    with open(ROOT / "state" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": datetime.now().strftime("%Y%m%d_%H%M"), "platform": "fb-mh",
                            "topic": f"mh queue #{iid}", "url": fb_url},
                           ensure_ascii=False) + "\n")

    remaining = sum(1 for m in queue if not m.get("posted_at"))
    log(f"post_mh: {remaining} item(s) left in queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
