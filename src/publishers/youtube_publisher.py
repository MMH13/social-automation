"""Upload a video to YouTube via the Data API v3, using a long-lived refresh token
(no interactive browser flow at runtime — see scripts/youtube_oauth_setup.py for the
one-time local setup that mints YOUTUBE_REFRESH_TOKEN).
"""
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REQUIRED = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]


def configured() -> bool:
    return all(os.environ.get(k) for k in REQUIRED)


def _client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def publish_video(video_path: Path, thumbnail_path: Path | None, title: str, description: str,
                   tags: list[str], privacy_status: str = "private") -> str:
    youtube = _client()
    body = {
        "snippet": {"title": title, "description": description, "tags": tags,
                    "categoryId": "22"},  # People & Blogs — closest fit for psychology content
        "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response["id"]

    if thumbnail_path is not None and Path(thumbnail_path).exists():
        youtube.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))
        ).execute()

    return f"https://www.youtube.com/watch?v={video_id}"
