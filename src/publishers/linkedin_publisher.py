"""Post an image + caption to a LinkedIn profile via the REST API (ugcPosts)."""
import os
from pathlib import Path

import requests

API = "https://api.linkedin.com/v2"
REQUIRED = ["LINKEDIN_ACCESS_TOKEN"]


def configured() -> bool:
    return all(os.environ.get(k) for k in REQUIRED)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _person_urn() -> str:
    resp = requests.get(f"{API}/userinfo", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return f"urn:li:person:{resp.json()['sub']}"


def publish(caption: str, image_path: Path) -> str:
    author = _person_urn()

    register = requests.post(
        f"{API}/assets?action=registerUpload",
        headers=_headers(),
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author,
                "serviceRelationships": [
                    {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                ],
            }
        },
        timeout=30,
    )
    register.raise_for_status()
    value = register.json()["value"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset = value["asset"]

    with open(image_path, "rb") as f:
        up = requests.put(upload_url, headers=_headers(), data=f, timeout=120)
    up.raise_for_status()

    post = requests.post(
        f"{API}/ugcPosts",
        headers=_headers(),
        json={
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "media": asset}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
        timeout=60,
    )
    post.raise_for_status()
    return post.headers.get("x-restli-id", "posted")
