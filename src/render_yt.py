"""Render the next un-rendered YouTube item (Shorts or long-form) from
scheduled_yt/content.json into youtube_queue/item{id}/ for manual review.

Usage: python -m src.render_yt

Mirrors post_pt.py's "one item per run" convention, but does NOT publish -
rendered items land with status "pending_review" and need
`python -m scripts.review_youtube --approve <id>` before src.post_yt will touch them.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .media.image_maker import make_thumbnail
from .media.longform_video import make_longform
from .media.narrated_video import make_narrated

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "scheduled_yt" / "content.json"
QUEUE_DIR = ROOT / "youtube_queue"


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
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
    watermark = cfg.get("youtube", {}).get("channel_watermark", "@psychology.tube")

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    item = next((i for i in queue if not i.get("rendered")), None)
    if item is None:
        log("render_yt: queue empty - nothing to render")
        return 0

    iid, fmt = item["id"], item["format"]
    title = item.get("title", "")
    yt_title = item.get("youtube_title", "")
    yt_desc = item.get("youtube_description", "")

    # A queue-builder bug once truncated content to a single character before it
    # published (see post_pt.py) - refuse to render/queue obvious garbage.
    if not title or len(title.strip()) < 8 or not yt_title or len(yt_title.strip()) < 8:
        log(f"render_yt item{iid}: title/youtube_title look corrupted - refusing to render")
        return 1
    if fmt == "shorts" and not item.get("points"):
        log(f"render_yt item{iid}: shorts item has no points - refusing to render")
        return 1
    if fmt == "longform" and not item.get("scenes"):
        log(f"render_yt item{iid}: longform item has no scenes - refusing to render")
        return 1

    out_dir = QUEUE_DIR / f"item{iid:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "video.mp4"

    if fmt == "shorts":
        built = make_narrated(
            title, item["points"], video_path,
            variant=item.get("variant", 0), bg_query=item.get("bg_query"),
            watermark=watermark, outro=item.get("outro", "Follow for more."),
        )
    elif fmt == "longform":
        built = make_longform(
            title, item["scenes"], video_path,
            variant=item.get("variant", 0), watermark=watermark,
            outro=item.get("outro", "Follow for more."),
        )
    else:
        log(f"render_yt item{iid}: unknown format '{fmt}'")
        return 1

    if built is None or not video_path.exists() or video_path.stat().st_size == 0:
        log(f"render_yt item{iid} ({fmt}): video render failed")
        return 1

    thumb_path = out_dir / "thumbnail.jpg"
    make_thumbnail(item.get("thumbnail_text", title), thumb_path, variant=item.get("variant", 0),
                   watermark=watermark)

    metadata = {
        "id": iid,
        "format": fmt,
        "title": yt_title,
        "description": yt_desc,
        "tags": item.get("tags", []),
        "status": "pending_review",
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    item["rendered"] = True
    save(queue)
    log(f"render_yt item{iid} ({fmt}): rendered -> {out_dir} (pending_review)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
