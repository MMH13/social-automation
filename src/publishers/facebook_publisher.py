"""Post an image + caption to a Facebook Page via the Graph API.

Supports multiple pages in one repo: pass page_id/token explicitly (e.g. for a
second track like "Speaking from soul"), or omit them to fall back to the
default FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN env vars (Psychology Tube).
"""
import os
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v21.0"
REQUIRED = ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"]


def configured(page_id_var: str = "FB_PAGE_ID", token_var: str = "FB_PAGE_ACCESS_TOKEN") -> bool:
    return bool(os.environ.get(page_id_var)) and bool(os.environ.get(token_var))


def _raise_for_status(resp: requests.Response) -> None:
    """Like resp.raise_for_status(), but keeps the response body in the exception
    message. The plain version drops it, so every failed run just logged "400 Bad
    Request" with no way to tell a dead token (code 190) apart from a rate limit, a
    bad caption, or a genuinely broken item - without a manual repro. That cost real
    diagnosis time on the "Speaking from soul" 44h outage (2026-09-14/16): the real
    cause (session invalidated - password changed) only surfaced once someone ran
    the request by hand and printed resp.text."""
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} error for {resp.url}: {resp.text[:500]}", response=resp)


def publish(caption: str, image_path: Path, page_id: str | None = None, token: str | None = None) -> str:
    page_id = page_id or os.environ["FB_PAGE_ID"]
    token = token or os.environ["FB_PAGE_ACCESS_TOKEN"]
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH}/{page_id}/photos",
            data={"caption": caption, "access_token": token},
            files={"source": f},
            timeout=120,
        )
    _raise_for_status(resp)
    post_id = resp.json().get("post_id") or resp.json()["id"]
    return f"https://www.facebook.com/{post_id}"


def publish_text(message: str, page_id: str | None = None, token: str | None = None) -> str:
    """Text-only post, no image - the page's feed endpoint rather than /photos."""
    page_id = page_id or os.environ["FB_PAGE_ID"]
    token = token or os.environ["FB_PAGE_ACCESS_TOKEN"]
    resp = requests.post(
        f"{GRAPH}/{page_id}/feed",
        data={"message": message, "access_token": token},
        timeout=60,
    )
    _raise_for_status(resp)
    post_id = resp.json()["id"]
    return f"https://www.facebook.com/{post_id}"


def comment_on_post(post_id: str, message: str, page_id: str | None = None,
                     token: str | None = None, reply_to: str | None = None) -> str:
    """Comment on a post (or reply to a comment, if reply_to is a comment id).

    Used for the "hook in the post, value in the comments" format: publish a bold
    text-card post, then follow up with the actual resource list / numbered steps
    as a comment thread. Boosts comment count and forces scroll-through engagement.
    """
    token = token or os.environ["FB_PAGE_ACCESS_TOKEN"]
    target = reply_to or post_id
    resp = requests.post(
        f"{GRAPH}/{target}/comments",
        data={"message": message, "access_token": token},
        timeout=60,
    )
    _raise_for_status(resp)
    return resp.json()["id"]


def comment_thread(post_id: str, messages: list[str], page_id: str | None = None,
                    token: str | None = None) -> list[str]:
    """Post a numbered sequence of comments as nested replies (1/8, 2/8, ... style),
    so they read as one continuous thread instead of scattered top-level comments."""
    ids: list[str] = []
    reply_to = None
    for msg in messages:
        cid = comment_on_post(post_id, msg, page_id=page_id, token=token, reply_to=reply_to)
        ids.append(cid)
        reply_to = cid
    return ids


def publish_reel(caption: str, video_path: Path, page_id: str | None = None, token: str | None = None) -> str:
    """Publish a vertical video as a Facebook Reel (3-phase resumable upload)."""
    page_id = page_id or os.environ["FB_PAGE_ID"]
    token = token or os.environ["FB_PAGE_ACCESS_TOKEN"]

    start = requests.post(f"{GRAPH}/{page_id}/video_reels",
                          data={"upload_phase": "start", "access_token": token}, timeout=60)
    _raise_for_status(start)
    video_id = start.json()["video_id"]

    size = video_path.stat().st_size
    with open(video_path, "rb") as f:
        up = requests.post(
            f"https://rupload.facebook.com/video-upload/v21.0/{video_id}",
            headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
            data=f, timeout=600,
        )
    _raise_for_status(up)

    fin = requests.post(f"{GRAPH}/{page_id}/video_reels", data={
        "upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
        "description": caption, "access_token": token}, timeout=120)
    _raise_for_status(fin)
    return f"https://www.facebook.com/reel/{video_id}"


def publish_video(caption: str, video_path: Path, page_id: str | None = None, token: str | None = None) -> str:
    """Fallback: plain page video post."""
    page_id = page_id or os.environ["FB_PAGE_ID"]
    token = token or os.environ["FB_PAGE_ACCESS_TOKEN"]
    with open(video_path, "rb") as f:
        resp = requests.post(f"{GRAPH}/{page_id}/videos",
                             data={"description": caption, "access_token": token},
                             files={"source": f}, timeout=600)
    _raise_for_status(resp)
    return f"https://www.facebook.com/{resp.json()['id']}"
