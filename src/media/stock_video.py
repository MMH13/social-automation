"""Fetch a copyright-free vertical background clip for reels.

Sources, in priority order:
  1. Local clips committed in assets/video/ (*.mp4/*.mov/*.webm) — rotated by variant.
  2. Pexels Video API (PEXELS_API_KEY) — Pexels License: free commercial use, no attribution.
  3. Pixabay Video API (PIXABAY_API_KEY) — Pixabay Content License, same terms.

Returns None if nothing is available, in which case the reel falls back to a
generated gradient background.
"""
import os
import tempfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
CLIP_DIR = ROOT / "assets" / "video"
CLIP_EXTS = (".mp4", ".mov", ".webm")
CACHE_DIR = Path(tempfile.gettempdir()) / "reel_bg_cache"

# Calm, abstract, face-free footage that won't fight the text overlay.
QUERIES = [
    "calm ocean waves slow motion",
    "clouds time lapse sky",
    "rain on window",
    "forest sunlight trees",
    "night city bokeh lights",
    "abstract ink water",
    "snow falling forest",
    "sunset over mountains",
    "candle flame dark",
    "waves aerial beach",
]

TIMEOUT = 45


def local_clips() -> list[Path]:
    if not CLIP_DIR.exists():
        return []
    return sorted(p for p in CLIP_DIR.iterdir() if p.suffix.lower() in CLIP_EXTS)


def _download(url: str, dest: Path) -> Path | None:
    try:
        with requests.get(url, stream=True, timeout=TIMEOUT) as r:
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(1 << 16):
                    fh.write(chunk)
        return dest
    except Exception as e:  # network / API hiccup must never kill a post
        print(f"  [bg] download failed: {e}")
        return None


def _from_pexels(query: str, key: str) -> Path | None:
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 15},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
    except Exception as e:
        print(f"  [bg] pexels search failed: {e}")
        return None

    for vid in videos:
        # Prefer a portrait file around 1080p — big enough to crop, small enough to fetch.
        files = [f for f in vid.get("video_files", []) if (f.get("height") or 0) >= (f.get("width") or 0)]
        files.sort(key=lambda f: abs((f.get("height") or 0) - 1920))
        if not files:
            continue
        link = files[0].get("link")
        if link:
            return _download(link, CACHE_DIR / f"pexels_{vid['id']}.mp4")
    return None


def _from_pixabay(query: str, key: str) -> Path | None:
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": query, "per_page": 15, "safesearch": "true"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
    except Exception as e:
        print(f"  [bg] pixabay search failed: {e}")
        return None

    for hit in hits:
        streams = hit.get("videos", {})
        for size in ("large", "medium", "small"):
            link = streams.get(size, {}).get("url")
            if link:
                return _download(link, CACHE_DIR / f"pixabay_{hit['id']}.mp4")
    return None


def get_background(variant: int, query: str | None = None) -> Path | None:
    """Return a path to a background clip, or None to fall back to a gradient."""
    clips = local_clips()
    if clips:
        clip = clips[variant % len(clips)]
        print(f"  [bg] local clip '{clip.name}'")
        return clip

    q = query or QUERIES[variant % len(QUERIES)]

    pexels = os.getenv("PEXELS_API_KEY", "").strip()
    if pexels:
        path = _from_pexels(q, pexels)
        if path:
            print(f"  [bg] pexels '{q}' -> {path.name}")
            return path

    pixabay = os.getenv("PIXABAY_API_KEY", "").strip()
    if pixabay:
        path = _from_pixabay(q, pixabay)
        if path:
            print(f"  [bg] pixabay '{q}' -> {path.name}")
            return path

    print("  [bg] no stock source available - using gradient")
    return None
