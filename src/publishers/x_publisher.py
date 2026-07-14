"""Post an image + caption to X (Twitter) via tweepy."""
import os
from pathlib import Path

REQUIRED = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]


def configured() -> bool:
    return all(os.environ.get(k) for k in REQUIRED)


def publish(caption: str, image_path: Path) -> str:
    import tweepy

    auth_kwargs = dict(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    # v1.1 API for media upload, v2 for creating the post
    api_v1 = tweepy.API(tweepy.OAuth1UserHandler(**auth_kwargs))
    media = api_v1.media_upload(filename=str(image_path))
    client = tweepy.Client(**auth_kwargs)
    resp = client.create_tweet(text=caption, media_ids=[media.media_id])
    return f"https://x.com/i/status/{resp.data['id']}"
