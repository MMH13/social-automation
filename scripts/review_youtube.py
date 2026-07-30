# -*- coding: utf-8 -*-
"""Review rendered YouTube items before they publish.

Usage:
  python scripts/review_youtube.py                  # list pending items
  python scripts/review_youtube.py --approve <id>    # approve item <id>
  python scripts/review_youtube.py --reject <id>      # reject item <id>

Nothing in youtube_queue/ ever publishes on its own - src.post_yt only touches
items whose metadata.json status is "approved". Open item{id}/video.mp4 and
thumbnail.jpg yourself to judge the actual content before approving.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "youtube_queue"


def _items():
    if not QUEUE_DIR.exists():
        return []
    return sorted(QUEUE_DIR.glob("item*/metadata.json"))


def _set_status(item_id: int, status: str) -> int:
    for meta_path in _items():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["id"] == item_id:
            if meta["status"] == "posted":
                print(f"item {item_id}: already posted to YouTube - not touching it")
                return 1
            meta["status"] = status
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"item {item_id}: -> {status}")
            return 0
    print(f"item {item_id}: not found in {QUEUE_DIR}")
    return 1


def _list() -> int:
    pending = []
    for meta_path in _items():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["status"] == "pending_review":
            pending.append((meta, meta_path.parent))
    if not pending:
        print("no items pending review")
        return 0
    for meta, folder in pending:
        print(f"[{meta['id']}] ({meta['format']}) {meta['title']}")
        print(f"      video:     {folder / 'video.mp4'}")
        print(f"      thumbnail: {folder / 'thumbnail.jpg'}")
        print(f"      tags:      {', '.join(meta.get('tags', []))}")
        print()
    print(f"{len(pending)} item(s) pending. Approve with:\n"
          f"  python scripts/review_youtube.py --approve <id>")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return _list()
    if args[0] in ("--approve", "--reject") and len(args) == 2:
        status = "approved" if args[0] == "--approve" else "rejected"
        return _set_status(int(args[1]), status)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
