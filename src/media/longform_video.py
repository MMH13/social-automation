"""Render a multi-scene long-form narrated video: 16:9, several minutes, one scene
per narration beat — the horizontal, longer sibling of narrated_video.py's vertical
listicle format.

Two-pass assembly (kept simple on purpose so it scales to 15-25 scenes without one
giant ffmpeg filter graph):
  Pass 1 - render each scene to its own clip (background + synced caption + narration,
           silence-padded to a fixed gap) and concat them with the concat demuxer.
  Pass 2 - lay one continuous music bed under the whole concatenated narration.

Cuts between scenes are hard cuts, not crossfades — simpler, robust at any scene
count, and a normal look for documentary/listicle-style narration.

Voice: same kokoro/edge-tts stack as narrated_video.py.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .image_maker import GRADIENTS, _font, _gradient_bg, _wrap
from .narrated_video import VOICE, _duration, _tts
from .reel_maker import _music_files, ffmpeg_available
from .stock_video import get_background

W, H = 1920, 1080       # 16:9 long-form
GAP = 0.5                # silence between scenes (seconds)
TAIL = 2.2               # music-only outro after the last line


def _caption_png(text: str, path: Path, watermark: str, big: bool) -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    size = 80 if big else 66
    font = _font("arialbd.ttf", size)
    margin = 220

    blocks = [b.strip() for b in text.upper().split("\n") if b.strip()]
    lines: list[str] = []
    for i, block in enumerate(blocks):
        lines.extend(_wrap(draw, block, font, W - 2 * margin))
        if i < len(blocks) - 1:
            lines.append("")

    line_h = int(size * 1.2)
    y = H - 260 - len(lines) * line_h  # lower-third placement, standard for 16:9 narration
    for line in lines:
        if line:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255, 255),
                      stroke_width=8, stroke_fill=(0, 0, 0, 235))
        y += line_h

    if watermark:
        wm_font = _font("arialbd.ttf", 34)
        w = draw.textlength(watermark, font=wm_font)
        draw.text((W - w - 50, 40), watermark, font=wm_font,
                  fill=(255, 255, 255, 200), stroke_width=4, stroke_fill=(0, 0, 0, 200))
    img.save(path)


def _render_scene(idx: int, text: str, audio: Path, bg_query: str | None, variant: int,
                   seg_dur: float, watermark: str, tmp_dir: Path, big: bool) -> Path | None:
    cap_png = tmp_dir / f"seg{idx:02d}_cap.png"
    _caption_png(text, cap_png, watermark, big)

    bg_clip = get_background(variant, bg_query, orientation="landscape")
    if bg_clip:
        bg_in = ["-stream_loop", "-1", "-t", f"{seg_dur:.2f}", "-i", str(bg_clip)]
        bg_chain = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"fps=30,eq=brightness=-0.22:saturation=0.8,setsar=1[bg];"
        )
    else:
        top, bot = GRADIENTS[variant % len(GRADIENTS)]
        grad = tmp_dir / f"seg{idx:02d}_bg.png"
        _gradient_bg(W, H, top, bot).save(grad)
        bg_in = ["-loop", "1", "-t", f"{seg_dur:.2f}", "-i", str(grad)]
        bg_chain = f"[0:v]fps=30,setsar=1[bg];"

    fade_out_start = max(0.0, seg_dur - 0.4)
    filt = (
        f"{bg_chain}"
        f"[1:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,"
        f"fade=t=out:st={fade_out_start:.2f}:d=0.3:alpha=1[cap];"
        f"[bg][cap]overlay=0:0[v];"
        f"[2:a]apad=pad_dur={GAP + 1}[a]"
    )
    out = tmp_dir / f"seg{idx:02d}.mp4"
    cmd = [
        "ffmpeg", "-y", *bg_in, "-loop", "1", "-t", f"{seg_dur:.2f}", "-i", str(cap_png),
        "-i", str(audio),
        "-filter_complex", filt,
        "-map", "[v]", "-map", "[a]",
        "-t", f"{seg_dur:.2f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [longform] scene {idx} ffmpeg failed: {result.stderr[-600:]}")
        return None
    return out


def make_longform(
    title: str,
    scenes: list[dict],
    out_path: Path,
    variant: int = 0,
    watermark: str = "@psychology.tube",
    voice: str = VOICE,
    outro: str = "Follow for more.",
) -> Path | None:
    """scenes: list of {"narration": str, "bg_query": str | None}."""
    if not ffmpeg_available():
        print("  [longform] ffmpeg not found - skipping")
        return None
    if not scenes:
        print("  [longform] no scenes provided")
        return None

    segments = (
        [{"narration": title, "bg_query": None}]
        + scenes
        + ([{"narration": outro, "bg_query": None}] if outro else [])
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        clips: list[Path] = []
        for i, seg in enumerate(segments):
            audio = _tts(seg["narration"], tmp_dir / f"seg{i:02d}", voice)
            if audio is None:
                print(f"  [longform] scene {i} TTS failed")
                return None
            dur = _duration(audio)
            if dur <= 0:
                print(f"  [longform] scene {i} TTS produced empty audio")
                return None
            seg_dur = dur + (TAIL if i == len(segments) - 1 else GAP)
            clip = _render_scene(
                i, seg["narration"], audio, seg.get("bg_query"), variant + i, seg_dur,
                watermark, tmp_dir, big=(i == 0),
            )
            if clip is None:
                return None
            clips.append(clip)

        list_txt = tmp_dir / "list.txt"
        list_txt.write_text(
            "\n".join(f"file '{c.as_posix()}'" for c in clips), encoding="utf-8"
        )
        assembled = tmp_dir / "assembled.mp4"
        concat_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt),
                      "-c", "copy", str(assembled)]
        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [longform] concat failed: {result.stderr[-600:]}")
            return None

        total = _duration(assembled)
        music = _music_files()
        if music:
            track = music[variant % len(music)]
            filt = (
                f"[1:a]volume=0.12,afade=t=in:st=0:d=1.5,"
                f"afade=t=out:st={max(0.0, total - 2.2):.2f}:d=2.0[bed];"
                f"[0:a][bed]amix=inputs=2:duration=first:normalize=0[a]"
            )
            cmd = [
                "ffmpeg", "-y", "-i", str(assembled),
                "-stream_loop", "-1", "-t", f"{total:.2f}", "-i", str(track),
                "-filter_complex", filt,
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                str(out_path),
            ]
        else:
            cmd = ["ffmpeg", "-y", "-i", str(assembled), "-c", "copy", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [longform] music mix failed: {result.stderr[-600:]}")
            return None
        print(f"  [longform] {len(segments)} scenes, {total:.1f}s")
    return out_path
