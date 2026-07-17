"""Render a short Reel: text fading in over a slowly zooming gradient background."""
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .image_maker import GRADIENTS, _font, _gradient_bg, _wrap

W, H = 1080, 1920
DURATION = 8  # seconds


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def make_reel(text: str, variant: int, out_path: Path) -> Path | None:
    if not ffmpeg_available():
        print("  [reel] ffmpeg not found - skipping")
        return None

    top, bot = GRADIENTS[variant % len(GRADIENTS)]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        bg = _gradient_bg(W, H, top, bot)
        bg_path = tmp_dir / "bg.png"
        bg.save(bg_path)

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = _font("arialbd.ttf", 78)
        margin = 110
        blocks = [b.strip() for b in text.split("\n") if b.strip()]
        lines: list[str] = []
        for i, block in enumerate(blocks):
            lines.extend(_wrap(draw, block, font, W - 2 * margin))
            if i < len(blocks) - 1:
                lines.append("")
        line_h = 100
        y = (H - len(lines) * line_h) // 2
        for line in lines:
            if line:
                w = draw.textlength(line, font=font)
                draw.text(((W - w) // 2 + 4, y + 4), line, font=font, fill=(0, 0, 0, 110))
                draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255, 255))
            y += line_h
        wm_font = _font("arialbd.ttf", 40)
        wm = "@psychology.tube"
        w = draw.textlength(wm, font=wm_font)
        draw.text(((W - w) // 2, H - 180), wm, font=wm_font, fill=(255, 255, 255, 200))
        text_path = tmp_dir / "text.png"
        overlay.save(text_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(bg_path),  # single frame; zoompan expands it to the full duration
            "-loop", "1", "-t", str(DURATION), "-i", str(text_path),
            "-filter_complex",
            (f"[0:v]scale={int(W*1.15)}:{int(H*1.15)},"
             f"zoompan=z='min(1.12,1+0.0005*on)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
             f":d={DURATION*30}:s={W}x{H}:fps=30[bg];"
             "[1:v]format=rgba,fade=t=in:st=0.6:d=0.9:alpha=1[txt];"
             "[bg][txt]overlay=0:0:shortest=1"),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", "30",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [reel] ffmpeg failed: {result.stderr[-300:]}")
            return None
    return out_path
