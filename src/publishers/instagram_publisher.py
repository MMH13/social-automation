"""Post an image + caption to Instagram (Business account) via the Graph API.

Instagram's publishing API only accepts media by public URL, so the image is
first uploaded to Cloudinary (free tier), then handed to Instagram.
"""
import os
import time
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v21.0"
REQUIRED = ["IG_USER_ID", "FB_PAGE_ACCESS_TOKEN"]
CLOUDINARY = ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"]


def configured() -> bool:
    return all(os.environ.get(k) for k in REQUIRED)


def _cloudinary_configured() -> bool:
    return all(os.environ.get(k) for k in CLOUDINARY)


def _fb_cdn_url(fb_post_id: str, token: str) -> str:
    """Public CDN URL of an image already posted to the Facebook page."""
    resp = requests.get(
        f"{GRAPH}/{fb_post_id}",
        params={"fields": "attachments{media{image{src}}}", "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["attachments"]["data"][0]["media"]["image"]["src"]


def _host_on_cloudinary(image_path: Path) -> str:
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
    )
    result = cloudinary.uploader.upload(str(image_path), folder="social-auto")
    return result["secure_url"]


def publish(caption: str, image_path: Path, fb_post_id: str | None = None) -> str:
    """Publish to Instagram. Needs the image at a public URL: reuses the Facebook
    post's CDN copy when fb_post_id is given, otherwise uploads to Cloudinary."""
    ig_id = os.environ["IG_USER_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    if fb_post_id:
        image_url = _fb_cdn_url(fb_post_id, token)
    elif _cloudinary_configured():
        image_url = _host_on_cloudinary(image_path)
    else:
        raise RuntimeError("Instagram needs either a Facebook post to reuse (enable facebook) "
                           "or Cloudinary credentials in .env")

    container = requests.post(
        f"{GRAPH}/{ig_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=120,
    )
    container.raise_for_status()
    creation_id = container.json()["id"]

    # container can take a few seconds to become ready
    for _ in range(10):
        status = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(3)

    pub = requests.post(
        f"{GRAPH}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=120,
    )
    pub.raise_for_status()
    return f"instagram media id {pub.json()['id']}"


def publish_reel(caption: str, video_path: Path) -> str:
    """Publish a Reel to Instagram. Requires Cloudinary (video must be at a public URL)."""
    import cloudinary
    import cloudinary.uploader

    if not _cloudinary_configured():
        raise RuntimeError("IG reels need Cloudinary credentials in .env (video hosting)")

    ig_id = os.environ["IG_USER_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
    )
    up = cloudinary.uploader.upload(str(video_path), resource_type="video", folder="social-auto")
    video_url = up["secure_url"]

    container = requests.post(f"{GRAPH}/{ig_id}/media", data={
        "media_type": "REELS", "video_url": video_url, "caption": caption,
        "access_token": token}, timeout=120)
    container.raise_for_status()
    creation_id = container.json()["id"]

    for _ in range(30):  # video processing can take a while
        status = requests.get(f"{GRAPH}/{creation_id}",
                              params={"fields": "status_code", "access_token": token},
                              timeout=30).json()
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"IG reel container error: {status}")
        time.sleep(5)

    pub = requests.post(f"{GRAPH}/{ig_id}/media_publish",
                        data={"creation_id": creation_id, "access_token": token}, timeout=120)
    pub.raise_for_status()
    return f"instagram reel id {pub.json()['id']}"
