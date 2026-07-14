"""Render a 1080x1920 vertical short: one slide per script line, concatenated with ffmpeg."""
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .image_maker import _font, _wrap

W, H = 1080, 1920
SECONDS_PER_SLIDE = 2.8


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _slide(text: str, idx: int, total: int, style: dict, brand: str, path: Path) -> None:
    img = Image.new("RGB", (W, H), style["bg_color"])
    draw = ImageDraw.Draw(img)
    accent = style["accent_color"]

    # progress bar across the top
    draw.rectangle([0, 0, W, 12], fill="#334155")
    draw.rectangle([0, 0, int(W * (idx + 1) / total), 12], fill=accent)

    font = _font(style.get("font", "arialbd.ttf"), 92 if idx == 0 else 76)
    margin = 100
    lines = _wrap(draw, text, font, W - 2 * margin)
    line_h = 110 if idx == 0 else 92
    y = (H - len(lines) * line_h) // 2
    for line in lines:
        draw.text((margin, y), line, font=font, fill=style["text_color"])
        y += line_h

    draw.text((margin, H - 140), f"@{brand}", font=_font(style.get("font", "arialbd.ttf"), 40), fill=accent)
    img.save(path, "PNG")


def make_video(script: list[str], style: dict, brand: str, out_path: Path) -> Path | None:
    if not ffmpeg_available():
        print("  [video] ffmpeg not found on PATH - skipping video render")
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        concat_lines = []
        for i, line in enumerate(script):
            slide = tmp_dir / f"slide{i:02d}.png"
            _slide(line, i, len(script), style, brand, slide)
            concat_lines.append(f"file '{slide.as_posix()}'")
            concat_lines.append(f"duration {SECONDS_PER_SLIDE}")
        # concat demuxer needs the last file repeated without a duration
        concat_lines.append(f"file '{(tmp_dir / f'slide{len(script)-1:02d}.png').as_posix()}'")
        concat_file = tmp_dir / "concat.txt"
        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", f"scale={W}:{H},format=yuv420p", "-r", "30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [video] ffmpeg failed: {result.stderr[-400:]}")
            return None
    return out_path
