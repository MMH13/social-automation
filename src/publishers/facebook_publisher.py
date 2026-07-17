"""Post an image + caption to a Facebook Page via the Graph API."""
import os
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v21.0"
REQUIRED = ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"]


def configured() -> bool:
    return all(os.environ.get(k) for k in REQUIRED)


def publish(caption: str, image_path: Path) -> str:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH}/{page_id}/photos",
            data={"caption": caption, "access_token": token},
            files={"source": f},
            timeout=120,
        )
    resp.raise_for_status()
    post_id = resp.json().get("post_id") or resp.json()["id"]
    return f"https://www.facebook.com/{post_id}"


def publish_reel(caption: str, video_path: Path) -> str:
    """Publish a vertical video as a Facebook Reel (3-phase resumable upload)."""
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    start = requests.post(f"{GRAPH}/{page_id}/video_reels",
                          data={"upload_phase": "start", "access_token": token}, timeout=60)
    start.raise_for_status()
    video_id = start.json()["video_id"]

    size = video_path.stat().st_size
    with open(video_path, "rb") as f:
        up = requests.post(
            f"https://rupload.facebook.com/video-upload/v21.0/{video_id}",
            headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
            data=f, timeout=600,
        )
    up.raise_for_status()

    fin = requests.post(f"{GRAPH}/{page_id}/video_reels", data={
        "upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
        "description": caption, "access_token": token}, timeout=120)
    fin.raise_for_status()
    return f"https://www.facebook.com/reel/{video_id}"


def publish_video(caption: str, video_path: Path) -> str:
    """Fallback: plain page video post."""
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    with open(video_path, "rb") as f:
        resp = requests.post(f"{GRAPH}/{page_id}/videos",
                             data={"description": caption, "access_token": token},
                             files={"source": f}, timeout=600)
    resp.raise_for_status()
    return f"https://www.facebook.com/{resp.json()['id']}"
