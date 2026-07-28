"""Render a narrated listicle video: AI voiceover over darkened copyright-free stock
footage, with bold outlined captions that change in sync with each spoken segment.

Format matches the long-form psychology/motivation pages: 3:4 (1080x1440), 1-2 minutes,
"5 signs that..." style scripts read aloud.

Voice: edge-tts (Microsoft Edge neural voices) — free, no API key, works on CI runners.
Background: stock_video.get_background() — local clips, else Pexels/Pixabay, else gradient.
Music: assets/music/ track ducked under the narration.
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .image_maker import GRADIENTS, _font, _gradient_bg, _wrap
from .reel_maker import ffmpeg_available, _music_files
from .stock_video import get_background

W, H = 1080, 1440           # 3:4, same as the reference format
GAP = 0.45                  # silence between spoken segments (seconds)
LEAD_IN = 0.6               # beat before the first line
TAIL = 1.8                  # music-only outro
VOICE = "en-US-GuyNeural"   # calm male narrator; en-US-AriaNeural for female
RATE = "-8%"                # slightly slower reads better over b-roll


def _tts(text: str, path: Path, voice: str) -> bool:
    try:
        import edge_tts
    except ImportError:
        print("  [tts] edge-tts not installed - skipping narration")
        return False
    try:
        asyncio.run(edge_tts.Communicate(text, voice, rate=RATE).save(str(path)))
        return path.exists() and path.stat().st_size > 0
    except Exception as e:
        print(f"  [tts] failed: {e}")
        return False


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def _caption_png(text: str, path: Path, watermark: str, big: bool) -> None:
    """White uppercase text with a heavy black stroke — readable over any footage."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    size = 96 if big else 82
    font = _font("arialbd.ttf", size)
    margin = 90

    lines: list[str] = []
    for i, block in enumerate([b.strip() for b in text.upper().split("\n") if b.strip()]):
        lines.extend(_wrap(draw, block, font, W - 2 * margin))
        if i:
            lines.insert(len(lines) - 1, "")

    line_h = int(size * 1.18)
    y = (H - len(lines) * line_h) // 2
    for line in lines:
        if line:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255, 255),
                      stroke_width=9, stroke_fill=(0, 0, 0, 235))
        y += line_h

    if watermark:
        wm_font = _font("arialbd.ttf", 38)
        w = draw.textlength(watermark, font=wm_font)
        draw.text(((W - w) // 2, H - 150), watermark, font=wm_font,
                  fill=(255, 255, 255, 210), stroke_width=4, stroke_fill=(0, 0, 0, 200))
    img.save(path)


def make_narrated(
    title: str,
    points: list[str],
    out_path: Path,
    variant: int = 0,
    bg_query: str | None = None,
    watermark: str = "@psychology.tube",
    voice: str = VOICE,
    outro: str = "Follow for more.",
) -> Path | None:
    if not ffmpeg_available():
        print("  [narrated] ffmpeg not found - skipping")
        return None

    segments = [title] + list(points) + ([outro] if outro else [])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg_clip = get_background(variant, bg_query)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # 1. Narrate each segment separately so captions can follow the voice.
        timed: list[tuple[Path, Path, float, float]] = []  # audio, png, start, end
        clock = LEAD_IN
        for i, seg in enumerate(segments):
            audio = tmp_dir / f"seg{i:02d}.mp3"
            if not _tts(seg, audio, voice):
                return None
            dur = _duration(audio)
            png = tmp_dir / f"seg{i:02d}.png"
            _caption_png(seg, png, watermark, big=(i == 0))
            timed.append((audio, png, clock, clock + dur))
            clock += dur + GAP
        total = clock + TAIL

        # 2. Background: darkened stock clip, else a slow gradient.
        if bg_clip:
            bg_in = ["-stream_loop", "-1", "-t", f"{total:.2f}", "-i", str(bg_clip)]
            bg_chain = (
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"fps=30,eq=brightness=-0.22:saturation=0.8,setsar=1,"
                f"fade=t=in:st=0:d=0.8,fade=t=out:st={total - 1.4:.2f}:d=1.4[bg];"
            )
        else:
            top, bot = GRADIENTS[variant % len(GRADIENTS)]
            grad = tmp_dir / "bg.png"
            _gradient_bg(W, H, top, bot).save(grad)
            bg_in = ["-loop", "1", "-t", f"{total:.2f}", "-i", str(grad)]
            bg_chain = f"[0:v]fps=30,setsar=1[bg];"

        # 3. Captions overlaid only while their line is being spoken.
        cap_in: list[str] = []
        cap_chain = ""
        prev = "bg"
        for i, (_, png, start, end) in enumerate(timed):
            idx = 1 + i
            cap_in += ["-loop", "1", "-t", f"{total:.2f}", "-i", str(png)]
            cap_chain += (
                f"[{idx}:v]format=rgba,fade=t=in:st={start:.2f}:d=0.35:alpha=1,"
                f"fade=t=out:st={max(start, end - 0.3):.2f}:d=0.3:alpha=1[c{i}];"
                f"[{prev}][c{i}]overlay=0:0:enable='between(t,{start - 0.35:.2f},{end + 0.05:.2f})'[v{i}];"
            )
            prev = f"v{i}"

        # 4. Narration timeline + music bed underneath it.
        voice_idx0 = 1 + len(timed)
        audio_in: list[str] = []
        for audio, _, _, _ in timed:
            audio_in += ["-i", str(audio)]

        legs = ""
        for i, (_, _, start, _) in enumerate(timed):
            legs += f"[{voice_idx0 + i}:a]adelay={int(start * 1000)}|{int(start * 1000)}[d{i}];"
        mix_ins = "".join(f"[d{i}]" for i in range(len(timed)))
        legs += f"{mix_ins}amix=inputs={len(timed)}:normalize=0,volume=1.6[speech];"

        music = _music_files()
        if music:
            track = music[variant % len(music)]
            music_idx = voice_idx0 + len(timed)
            audio_in += ["-stream_loop", "-1", "-t", f"{total:.2f}", "-i", str(track)]
            legs += (
                f"[{music_idx}:a]volume=0.14,afade=t=in:st=0:d=1.5,"
                f"afade=t=out:st={total - 2.2:.2f}:d=2.0[bed];"
                f"[speech][bed]amix=inputs=2:duration=first:normalize=0[a]"
            )
            src = f"narration + music '{track.name}'"
        else:
            legs += "[speech]anull[a]"
            src = "narration only"

        cmd = [
            "ffmpeg", "-y", *bg_in, *cap_in, *audio_in,
            "-filter_complex", f"{bg_chain}{cap_chain}{legs}",
            "-map", f"[{prev}]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [narrated] ffmpeg failed: {result.stderr[-600:]}")
            return None
        print(f"  [narrated] {len(segments)} segments, {total:.1f}s, {src}")
    return out_path
