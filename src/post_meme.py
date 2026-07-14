"""Post the next queued Psychology Tube meme to Facebook + Instagram.

Usage: python -m src.post_meme
Takes the first unposted item from scheduled_memes/memes.json, renders the
minimal dark template, posts to the FB page, then to IG reusing the FB CDN
image. Marks the item posted immediately after the FB publish so a crash or
IG failure can never cause a duplicate FB post.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .media.image_maker import make_minimal_dark
from .publishers import facebook_publisher, instagram_publisher

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_memes" / "memes.json"


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def main() -> int:
    load_dotenv(ROOT / ".env")
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))

    item = next((m for m in queue if not m.get("posted_at")), None)
    if item is None:
        log("post_meme: queue empty - nothing to post")
        return 0

    if not facebook_publisher.configured():
        log("post_meme: facebook credentials missing")
        return 1

    image_path = ROOT / "output" / "memes" / f"meme{item['id']:02d}.jpg"
    if not image_path.exists():
        make_minimal_dark(item["text"], image_path)

    try:
        fb_url = facebook_publisher.publish(item["fb_caption"], image_path)
    except Exception as e:
        log(f"post_meme meme{item['id']}: FB FAILED: {e}")
        return 1

    # mark as posted right away so this meme can never double-post
    item["posted_at"] = datetime.now().isoformat(timespec="seconds")
    item["fb_url"] = fb_url
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"post_meme meme{item['id']}: FB {fb_url}")

    try:
        fb_post_id = fb_url.rsplit("/", 1)[-1]
        ig_result = instagram_publisher.publish(item["ig_caption"], image_path, fb_post_id=fb_post_id)
        item["ig_url"] = ig_result
        log(f"post_meme meme{item['id']}: IG {ig_result}")
    except Exception as e:
        item["ig_url"] = f"FAILED: {e}"
        log(f"post_meme meme{item['id']}: IG FAILED: {e}")
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")

    with open(ROOT / "state" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": datetime.now().strftime("%Y%m%d_%H%M"),
                            "platform": "fb+ig", "topic": f"psych meme queue #{item['id']}",
                            "url": fb_url}, ensure_ascii=False) + "\n")

    remaining = sum(1 for m in queue if not m.get("posted_at"))
    log(f"post_meme: {remaining} meme(s) left in queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
