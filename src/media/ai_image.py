"""Generate a still background image via the OpenAI Images API (gpt-image-1).

Used by the "Speaking from soul" reels for Whisprs-style dreamy/painterly
backgrounds instead of stock footage. Fails soft: if OPENAI_API_KEY is
missing or the request errors, callers fall back to a gradient.
"""
import base64
import os
from pathlib import Path

import requests

API_URL = "https://api.openai.com/v1/images/generations"
STYLE_SUFFIX = (
    ", soft painterly digital art, dreamy muted color palette, cinematic soft "
    "lighting, emotional and poetic atmosphere, no text, no words, no letters, "
    "vertical portrait composition"
)

# Set within a run once the account is confirmed out of credit, so later scenes in the
# same reel skip straight to the stock-footage fallback instead of waiting out another
# guaranteed-to-fail call. Each cron run is a fresh process, so this only ever spans one
# video's scenes, never persists across runs — if credits return, the next run tries again.
_quota_exhausted = False


def configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY")) and not _quota_exhausted


def generate_background(prompt: str, out_path: Path, size: str = "1024x1536") -> Path | None:
    global _quota_exhausted
    if not configured():
        return None
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": "gpt-image-1", "prompt": prompt + STYLE_SUFFIX, "size": size, "n": 1},
            timeout=120,
        )
        if resp.status_code == 429 and "insufficient_quota" in resp.text:
            _quota_exhausted = True
            print("  [ai_image] out of credit - skipping AI art for the rest of this reel")
            return None
        resp.raise_for_status()
        b64 = resp.json()["data"][0]["b64_json"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(base64.b64decode(b64))
        return out_path
    except Exception as e:
        print(f"  [ai_image] generation failed: {e}")
        return None
