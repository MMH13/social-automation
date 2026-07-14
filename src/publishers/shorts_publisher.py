"""Deliver the vertical short video to TikTok + YouTube.

Two modes (config: video_delivery):
  queue       - copy video + captions into queue/ for one-tap manual upload
  upload_post - publish automatically via upload-post.com's API
"""
import json
import os
import shutil
from pathlib import Path

import requests

UPLOAD_POST_API = "https://api.upload-post.com/api/upload"


def to_queue(video_path: Path, package: dict, queue_dir: Path, stamp: str) -> str:
    dest = queue_dir / stamp
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video_path, dest / "short.mp4")
    captions = {
        "tiktok_caption": package["captions"]["tiktok"],
        "youtube_title": package["captions"]["youtube_title"],
        "youtube_description": package["captions"]["youtube_description"],
    }
    (dest / "captions.json").write_text(json.dumps(captions, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(dest)


def upload_post_configured() -> bool:
    return bool(os.environ.get("UPLOAD_POST_API_KEY") and os.environ.get("UPLOAD_POST_USER"))


def via_upload_post(video_path: Path, package: dict, platforms: list[str]) -> str:
    targets = [p for p in ("tiktok", "youtube") if platforms and p in platforms]
    with open(video_path, "rb") as f:
        resp = requests.post(
            UPLOAD_POST_API,
            headers={"Authorization": f"Apikey {os.environ['UPLOAD_POST_API_KEY']}"},
            data={
                "user": os.environ["UPLOAD_POST_USER"],
                "platform[]": targets,
                "title": package["captions"]["youtube_title"],
                "description": package["captions"]["youtube_description"],
                "caption": package["captions"]["tiktok"],
            },
            files={"video": f},
            timeout=600,
        )
    resp.raise_for_status()
    return resp.json().get("message", "submitted")
