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
