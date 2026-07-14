"""Social automation orchestrator.

Usage:
  python -m src.main            # real run: generate content + publish everywhere configured
  python -m src.main --dry-run  # generate media locally, publish nothing (no keys needed)
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .content_generator import generate, sample_package
from .media.image_maker import make_image
from .media.video_maker import make_video
from .publishers import facebook_publisher, instagram_publisher, linkedin_publisher, x_publisher
from .publishers import shorts_publisher

ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT / "state" / "history.jsonl"
LOG_FILE = ROOT / "state" / "runs.log"

IMAGE_PUBLISHERS = {
    "x": x_publisher,
    "facebook": facebook_publisher,
    "instagram": instagram_publisher,
    "linkedin": linkedin_publisher,
}


def load_history(window: int) -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l)["topic"] for l in lines[-window:]]


def log(msg: str) -> None:
    print(msg)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="generate media but publish nothing")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))

    if "FILL ME IN" in cfg["niche"] and not args.dry_run:
        log("ERROR: set your niche in config/config.yaml before a real run")
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = ROOT / "output" / stamp
    log(f"=== run {stamp} {'(DRY RUN)' if args.dry_run else ''} ===")

    # 1. content
    if args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        package = sample_package()
        log("content: using offline sample (no ANTHROPIC_API_KEY)")
    else:
        package = generate(cfg, load_history(cfg.get("history_window", 30)))
        log(f"content: generated topic '{package['topic']}'")

    (out_dir / "package.json").parent.mkdir(parents=True, exist_ok=True)
    (out_dir / "package.json").write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. media
    image_path = make_image(
        package["image_headline"], package["image_subtext"],
        cfg["style"], cfg["brand_name"], out_dir / "post.jpg",
    )
    log(f"image: {image_path}")
    video_path = make_video(package["video_script"], cfg["style"], cfg["brand_name"], out_dir / "short.mp4")
    log(f"video: {video_path or 'skipped'}")

    # 3. publish
    results, failures = {}, []
    enabled = cfg.get("platforms", {})
    fb_post_id = None  # instagram reuses the facebook post's CDN image

    for name, mod in IMAGE_PUBLISHERS.items():
        if not enabled.get(name):
            continue
        if args.dry_run:
            results[name] = "dry-run: skipped"
            continue
        if not mod.configured():
            results[name] = "skipped: credentials missing in .env"
            continue
        try:
            if name == "instagram":
                results[name] = mod.publish(package["captions"][name], image_path, fb_post_id=fb_post_id)
            else:
                results[name] = mod.publish(package["captions"][name], image_path)
            if name == "facebook":
                fb_post_id = results[name].rsplit("/", 1)[-1]
        except Exception as e:
            results[name] = f"FAILED: {e}"
            failures.append(name)
            traceback.print_exc()

    shorts_targets = [p for p in ("tiktok", "youtube") if enabled.get(p)]
    if video_path and shorts_targets:
        if args.dry_run:
            results["shorts"] = "dry-run: skipped"
        elif cfg.get("video_delivery") == "upload_post" and shorts_publisher.upload_post_configured():
            try:
                results["shorts"] = shorts_publisher.via_upload_post(video_path, package, shorts_targets)
            except Exception as e:
                results["shorts"] = f"FAILED: {e}"
                failures.append("shorts")
                traceback.print_exc()
        else:
            results["shorts"] = f"queued: {shorts_publisher.to_queue(video_path, package, ROOT / 'queue', stamp)}"

    for name, outcome in results.items():
        log(f"  {name}: {outcome}")

    # 4. remember the topic so future runs don't repeat it
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"stamp": stamp, "topic": package["topic"]}, ensure_ascii=False) + "\n")

    log(f"=== done ({len(failures)} failure(s)) ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
