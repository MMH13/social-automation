"""Illustrated-scene poetry reel for "Speaking from soul" (v2).

One short phrase per scene, each on its own lo-fi illustration, cutting about every
3 seconds with a slow push/pull, film grain and a vignette, small handwritten text
and a mastered (EQ / light room / ducked music) voice. Built to close the gap with
the top poetry reel pages, whose look is illustrated art + thin handwritten text +
fast phrase-per-scene pacing - not stock footage with a big serif poem.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .narrated_video import _duration, _tts
from .reel_maker import _music_files, ffmpeg_available
from .soul_reel import PITCH_FILTER, SPEED

W, H = 1080, 1920
FPS = 30
LEAD_IN = 0.5
GAP = 0.3
TAIL = 1.6
XFADE = 0.5

FONT_CANDIDATES = (
    "assets/fonts/Caveat-Regular.ttf",
    "C:/Windows/Fonts/Inkfree.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
)
REPO = Path(__file__).resolve().parents[2]

# Warm up the voice, add presence, a touch of room, then glue it with a compressor.
VOICE_MASTER = (
    "highpass=f=70,"
    "equalizer=f=180:t=q:w=1:g=2,"
    "equalizer=f=3200:t=q:w=1.2:g=1.5,"
    "acompressor=threshold=-18dB:ratio=3:attack=15:release=180:makeup=3,"
    "aecho=0.8:0.7:40|75:0.2|0.12"
)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for cand in FONT_CANDIDATES:
        p = Path(cand) if Path(cand).is_absolute() else REPO / cand
        try:
            return ImageFont.truetype(str(p), size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _phrase_png(text: str, path: Path, watermark: str) -> None:
    """Small thin handwritten phrase, centred a little above the middle, soft shadow."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = _font(56)
    max_w = W - 260
    probe = ImageDraw.Draw(img)
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if probe.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    line_h = 78
    y0 = int(H * 0.40) - (len(lines) * line_h) // 2

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, ln in enumerate(lines):
        w = sd.textlength(ln, font=font)
        sd.text(((W - w) / 2, y0 + i * line_h + 3), ln, font=font, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    img = Image.alpha_composite(img, shadow)

    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y0 + i * line_h), ln, font=font, fill=(255, 255, 255, 245))

    if watermark:
        wf = _font(34)
        w = d.textlength(watermark, font=wf)
        d.text(((W - w) / 2, H - 190), watermark, font=wf, fill=(255, 255, 255, 140))
    img.save(path)


def make_illustrated_reel(
    phrases: list[str],
    scene_images: list[Path],
    variant: int,
    out_path: Path,
    voice: str,
    watermark: str = "speaking from soul",
    master_voice: bool = False,
) -> Path | None:
    if not ffmpeg_available():
        print("  [reel_v2] ffmpeg not found")
        return None
    n = len(phrases)
    if n == 0 or len(scene_images) < n:
        print("  [reel_v2] need one scene image per phrase")
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        timed: list[tuple[Path, float, float]] = []
        clock = LEAD_IN
        for i, phrase in enumerate(phrases):
            audio = _tts(phrase, tmp_dir / f"seg{i:02d}", voice, speed=SPEED)
            if audio is None:
                print("  [reel_v2] TTS failed")
                return None
            dur = _duration(audio)
            timed.append((audio, clock, clock + dur))
            clock += dur + GAP
        total = clock - GAP + TAIL
        fade_out_start = max(0.0, total - 1.3)

        scene_d: list[float] = []
        for i, (_, start, end) in enumerate(timed):
            d = end - start + GAP
            if i == 0:
                d += LEAD_IN
            if i == n - 1:
                d += TAIL - GAP + (n - 1) * XFADE
            scene_d.append(d)

        bg_inputs: list[str] = []
        bg_pre = ""
        for i, d in enumerate(scene_d):
            frames = int(d * FPS) + 2
            zoom = (f"min(1.0+0.07*on/{frames},1.07)" if i % 2 == 0
                    else f"max(1.07-0.07*on/{frames},1.0)")
            drift = 30 if i % 2 == 0 else -30
            bg_pre += (
                f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"scale={int(W * 1.2)}:{int(H * 1.2)},"
                f"zoompan=z='{zoom}':x='(iw-iw/zoom)/2+{drift}*on/{frames}':y='(ih-ih/zoom)/2'"
                f":d={frames}:s={W}x{H}:fps={FPS},"
                f"eq=contrast=1.04:saturation=1.06:brightness=-0.02,setsar=1[bg{i}];"
            )
            bg_inputs += ["-loop", "1", "-t", f"{d:.2f}", "-i", str(scene_images[i])]

        if n == 1:
            chain = bg_pre + "[bg0]"
        else:
            chain = bg_pre
            running, cum = "bg0", scene_d[0]
            for i in range(1, n):
                offset = cum - i * XFADE
                chain += (f"[{running}][bg{i}]xfade=transition=fade:duration={XFADE}"
                          f":offset={offset:.2f}[bgx{i}];")
                running = f"bgx{i}"
                cum += scene_d[i]
            chain += f"[{running}]"
        chain += (f"noise=alls=11:allf=t,vignette=PI/4,"
                  f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_start:.2f}:d=1.3[bg];")

        cap_inputs: list[str] = []
        cap_chain = ""
        prev = "bg"
        for i, (_, start, end) in enumerate(timed):
            idx = n + i
            png = tmp_dir / f"cap{i:02d}.png"
            _phrase_png(phrases[i], png, watermark)
            cap_inputs += ["-loop", "1", "-t", f"{total:.2f}", "-i", str(png)]
            show_from = max(0.0, start - 0.15)
            show_to = end + GAP
            cap_chain += (
                f"[{idx}:v]format=rgba,fade=t=in:st={show_from:.2f}:d=0.4:alpha=1,"
                f"fade=t=out:st={max(show_from, show_to - 0.3):.2f}:d=0.3:alpha=1[c{i}];"
                f"[{prev}][c{i}]overlay=0:0:enable='between(t,{show_from:.2f},{show_to + 0.05:.2f})'[v{i}];"
            )
            prev = f"v{i}"

        voice_idx0 = n + n
        audio_inputs: list[str] = []
        for audio, _, _ in timed:
            audio_inputs += ["-i", str(audio)]
        legs = ""
        for i, (_, start, _) in enumerate(timed):
            ms = int(start * 1000)
            legs += f"[{voice_idx0 + i}:a]{PITCH_FILTER},adelay={ms}|{ms}[d{i}];"
        mix_ins = "".join(f"[d{i}]" for i in range(n))
        if master_voice:
            legs += f"{mix_ins}amix=inputs={n}:normalize=0,{VOICE_MASTER},volume=1.5[speech];"
        else:
            legs += f"{mix_ins}amix=inputs={n}:normalize=0,volume=1.6[speech];"

        music = _music_files()
        if music:
            track = music[variant % len(music)]
            music_idx = voice_idx0 + n
            audio_inputs += ["-stream_loop", "-1", "-t", f"{total:.2f}", "-i", str(track)]
            if master_voice:
                legs += (
                    "[speech]asplit=2[sp1][sp2];"
                    f"[{music_idx}:a]volume=0.22,afade=t=in:st=0:d=1.2,"
                    f"afade=t=out:st={fade_out_start:.2f}:d=1.3[bed];"
                    "[bed][sp2]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400[duck];"
                    "[sp1][duck]amix=inputs=2:duration=first:normalize=0,"
                    "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
                )
            else:
                legs += (
                    f"[{music_idx}:a]volume=0.13,afade=t=in:st=0:d=1.2,"
                    f"afade=t=out:st={fade_out_start:.2f}:d=1.3[bed];"
                    "[speech][bed]amix=inputs=2:duration=first:normalize=0[a]"
                )
        else:
            legs += "[speech]anull[a]"

        cmd = [
            "ffmpeg", "-y", *bg_inputs, *cap_inputs, *audio_inputs,
            "-filter_complex", f"{chain}{cap_chain}{legs}",
            "-map", f"[{prev}]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [reel_v2] ffmpeg failed: {result.stderr[-1200:]}")
            return None
        print(f"  [reel_v2] {total:.1f}s, {n} scenes, voice={voice}")
    return out_path
