"""Publish one pre-written package to X.

Usage: python -m src.post_one scheduled/post1
Renders the image if not already rendered, posts it, then marks the folder done
(renames package.json -> package.posted.json) so a re-run can't double-post.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .media.image_maker import make_image
from .publishers import x_publisher

ROOT = Path(__file__).resolve().parent.parent


def log(msg: str) -> None:
    print(msg)
    log_file = ROOT / "state" / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def main() -> int:
    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))

    folder = ROOT / sys.argv[1]
    package_file = folder / "package.json"
    if not package_file.exists():
        if (folder / "package.posted.json").exists():
            log(f"post_one {folder.name}: already posted, skipping")
            return 0
        log(f"post_one {folder.name}: no package.json found")
        return 1

    package = json.loads(package_file.read_text(encoding="utf-8"))

    image_path = folder / "post.jpg"
    if not image_path.exists():
        make_image(package["image_headline"], package["image_subtext"],
                   cfg["style"], cfg["brand_name"], image_path)

    if not x_publisher.configured():
        log(f"post_one {folder.name}: X credentials missing")
        return 1

    try:
        url = x_publisher.publish(package["captions"]["x"], image_path)
    except Exception as e:
        log(f"post_one {folder.name}: FAILED: {e}")
        return 1

    log(f"post_one {folder.name}: POSTED {url}")
    package_file.rename(folder / "package.posted.json")

    hist = ROOT / "state" / "history.jsonl"
    with open(hist, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "stamp": datetime.now().strftime("%Y%m%d_%H%M"),
            "topic": package["topic"], "url": url,
        }, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
