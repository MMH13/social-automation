"""Render a short Reel: text fading in over a slowly zooming gradient background,
with a calm, royalty-free ambient audio bed.

Audio source, in priority order:
  1. Your own licensed tracks dropped in assets/music/ (*.mp3/*.m4a/*.wav) — rotated by variant.
  2. A synthesized ambient chord pad (generated on the fly; royalty-free by construction —
     it's math, so it can never carry a copyright claim).
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .image_maker import GRADIENTS, _font, _gradient_bg, _wrap

W, H = 1080, 1920
DURATION = 8  # seconds
ROOT = Path(__file__).resolve().parent.parent.parent
MUSIC_DIR = ROOT / "assets" / "music"
MUSIC_EXTS = (".mp3", ".m4a", ".wav", ".ogg")

# Calm triads (Hz), one per gradient — a heavy lowpass + tremolo + echo turns these
# into a soft ambient wash rather than obvious sine tones.
CHORDS = [
    [220.00, 261.63, 329.63],  # Am
    [261.63, 329.63, 392.00],  # C
    [164.81, 196.00, 246.94],  # Em
    [146.83, 174.61, 220.00],  # Dm
    [196.00, 246.94, 293.66],  # G
    [174.61, 220.00, 261.63],  # F
    [220.00, 261.63, 392.00],  # Am7
    [196.00, 246.94, 329.63],  # Em-ish
]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _music_files() -> list[Path]:
    if not MUSIC_DIR.exists():
        return []
    return sorted(p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in MUSIC_EXTS)


def make_reel(text: str, variant: int, out_path: Path) -> Path | None:
    if not ffmpeg_available():
        print("  [reel] ffmpeg not found - skipping")
        return None

    top, bot = GRADIENTS[variant % len(GRADIENTS)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fade_out_start = max(0.0, DURATION - 1.5)

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

        video_chain = (
            f"[0:v]scale={int(W*1.15)}:{int(H*1.15)},"
            f"zoompan=z='min(1.12,1+0.0005*on)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
            f":d={DURATION*30}:s={W}x{H}:fps=30[bg];"
            "[1:v]format=rgba,fade=t=in:st=0.6:d=0.9:alpha=1[txt];"
            "[bg][txt]overlay=0:0:shortest=1[v]"
        )

        inputs = ["-i", str(bg_path), "-loop", "1", "-t", str(DURATION), "-i", str(text_path)]

        music = _music_files()
        if music:
            track = music[variant % len(music)]
            inputs += ["-stream_loop", "-1", "-t", str(DURATION), "-i", str(track)]
            audio_chain = (
                f"[2:a]volume=0.55,afade=t=in:st=0:d=1.2,"
                f"afade=t=out:st={fade_out_start}:d=1.5[a]"
            )
            src = f"music '{track.name}'"
        else:
            freqs = CHORDS[variant % len(CHORDS)]
            for f in freqs:
                inputs += ["-f", "lavfi", "-t", str(DURATION), "-i", f"sine=frequency={f}:sample_rate=44100"]
            mix = "".join(f"[{2 + i}:a]" for i in range(len(freqs)))
            audio_chain = (
                f"{mix}amix=inputs={len(freqs)}:duration=longest,"
                "tremolo=f=0.12:d=0.5,aecho=0.8:0.9:500:0.25,lowpass=f=750,"
                f"volume=0.5,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start}:d=1.5[a]"
            )
            src = "synthesized ambient pad"

        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", f"{video_chain};{audio_chain}",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [reel] ffmpeg failed: {result.stderr[-400:]}")
            return None
        print(f"  [reel] audio: {src}")
    return out_path
