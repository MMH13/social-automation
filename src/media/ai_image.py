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


def configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def generate_background(prompt: str, out_path: Path, size: str = "1024x1536") -> Path | None:
    if not configured():
        return None
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": "gpt-image-1", "prompt": prompt + STYLE_SUFFIX, "size": size, "n": 1},
            timeout=120,
        )
        resp.raise_for_status()
        b64 = resp.json()["data"][0]["b64_json"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(base64.b64decode(b64))
        return out_path
    except Exception as e:
        print(f"  [ai_image] generation failed: {e}")
        return None
