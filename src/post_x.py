"""Post the next queued X item (single post or thread).

Usage: python -m src.post_x
Takes the first unposted item from scheduled_x/posts.json. Text-only posts,
no media. Threads are posted as reply chains. The item is marked posted after
the first tweet succeeds so it can never double-post.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import tweepy
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_x" / "posts.json"
RETRIES = 3        # X throws transient Cloudflare 403s; retrying usually clears them
RETRY_WAIT = 20    # seconds


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def main() -> int:
    load_dotenv(ROOT / ".env")
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))

    item = next((p for p in queue if not p.get("posted_at")), None)
    if item is None:
        log("post_x: queue empty - nothing to post")
        return 0

    return _post(item, queue)


def _detail(e: Exception) -> str:
    """X returns a bare '403 Forbidden' unless you dig the body out of the response."""
    body = getattr(getattr(e, "response", None), "text", "") or ""
    api = getattr(e, "api_messages", None) or getattr(e, "api_errors", None)
    extra = f" | {api}" if api else ""
    return f"{e}{extra}{' | ' + body[:300] if body else ''}"


def _create(client, text: str, reply_to, item_id: int):
    """X intermittently answers writes with a transient Cloudflare 403 from any IP.
    One retry turns most of those into a normal post instead of a failed run."""
    last = None
    for attempt in range(RETRIES):
        try:
            if reply_to:
                return client.create_tweet(text=text, in_reply_to_tweet_id=reply_to)
            return client.create_tweet(text=text)
        except tweepy.errors.Forbidden as e:
            last = e
            if attempt < RETRIES - 1:
                log(f"post_x item{item_id}: 403 on attempt {attempt + 1}, retrying in {RETRY_WAIT}s")
                time.sleep(RETRY_WAIT)
    raise last


def _post(item, queue):
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )

    tweets = [item["text"]] if item["type"] == "single" else item["tweets"]
    urls, reply_to = [], None
    for i, text in enumerate(tweets):
        try:
            resp = _create(client, text, reply_to, item["id"])
        except Exception as e:
            if i == 0:
                log(f"post_x item{item['id']}: FAILED: {_detail(e)}")
                return 1
            log(f"post_x item{item['id']}: thread broke at tweet {i + 1}: {_detail(e)}")
            break
        reply_to = resp.data["id"]
        urls.append(f"https://x.com/i/status/{reply_to}")
        if i == 0:
            # mark posted immediately so a crash mid-thread can't double-post
            item["posted_at"] = datetime.now().isoformat(timespec="seconds")
            item["urls"] = urls
            QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
        if len(tweets) > 1:
            time.sleep(2)

    item["urls"] = urls
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"post_x item{item['id']} ({item['type']}, day {item['day']}): {urls[0]}"
        + (f" (+{len(urls) - 1} thread tweets)" if len(urls) > 1 else ""))

    with open(ROOT / "state" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": datetime.now().strftime("%Y%m%d_%H%M"), "platform": "x",
                            "topic": f"x queue #{item['id']} ({item['type']})",
                            "url": urls[0]}, ensure_ascii=False) + "\n")

    remaining = sum(1 for p in queue if not p.get("posted_at"))
    log(f"post_x: {remaining} item(s) left in queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
