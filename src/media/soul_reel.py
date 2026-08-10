"""Render a narrated, multi-scene quote reel for "Speaking from soul": each short
block of the poem gets its own AI-generated (or gradient fallback) background with a
slow Ken Burns zoom, crossfading into the next scene as the narration moves to the
next block. Only the current block's lines are on screen at a time — not the whole
poem at once. Mirrors narrated_video.py's per-segment narration/caption-sync approach,
adapted for AI-art scene changes and the page's poetic (not bold-caps) typography.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .ai_image import generate_background
from .image_maker import SOFT_GRADIENTS, _font, _gradient_bg, _wrap
from .narrated_video import _duration, _tts
from .reel_maker import _music_files, ffmpeg_available
from .stock_video import get_background as get_stock_clip

W, H = 1080, 1920
LEAD_IN = 0.6
GAP = 0.4          # pause between blocks
TAIL = 2.0          # final beat after the last block
XFADE = 0.6         # scene-to-scene crossfade duration
SPEED = 0.87        # slower, more deliberate/confident delivery than kokoro's default pace


def _block_caption(text: str, path: Path, watermark: str) -> None:
    """One block's lines, centered, poetic italic serif — the style used across the page."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font("georgiai.ttf", 74)
    margin = 110
    blocks = [b.strip() for b in text.split("\n") if b.strip()]
    lines: list[str] = []
    for i, block in enumerate(blocks):
        lines.extend(_wrap(draw, block, font, W - 2 * margin))
        if i < len(blocks) - 1:
            lines.append("")
    line_h = 98
    y = (H - len(lines) * line_h) // 2
    for line in lines:
        if line:
            w = draw.textlength(line, font=font)
            draw.text(((W - w) // 2 + 4, y + 4), line, font=font, fill=(0, 0, 0, 120))
            draw.text(((W - w) // 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h
    if watermark:
        wm_font = _font("arial.ttf", 34)
        w = draw.textlength(watermark, font=wm_font)
        draw.text(((W - w) // 2, H - 150), watermark, font=wm_font, fill=(255, 255, 255, 170))
    img.save(path)


def make_soul_reel(
    blocks: list[str],
    bg_prompts: list[str],
    variant: int,
    out_path: Path,
    voice: str,
    watermark: str = "speaking from soul",
) -> Path | None:
    if not ffmpeg_available():
        print("  [soul_reel] ffmpeg not found - skipping")
        return None
    if not blocks:
        print("  [soul_reel] no text blocks given")
        return None

    n = len(blocks)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # 1. Narrate each block separately — captions and scene changes follow the voice.
        timed: list[tuple[Path, float, float]] = []  # audio, start, end
        clock = LEAD_IN
        for i, block in enumerate(blocks):
            spoken = block.replace("\n", " ")
            audio = _tts(spoken, tmp_dir / f"seg{i:02d}", voice, speed=SPEED)
            if audio is None:
                print("  [soul_reel] TTS failed - no engine available")
                return None
            dur = _duration(audio)
            timed.append((audio, clock, clock + dur))
            clock += dur + GAP
        total = clock - GAP + TAIL
        fade_out_start = max(0.0, total - 1.5)

        # 2. Per-scene on-screen duration (crossfade eats into this at each boundary,
        # so the tail absorbs that loss to keep the overall length matching `total`).
        scene_d: list[float] = []
        for i, (_, start, end) in enumerate(timed):
            d = end - start
            if i == 0:
                d += LEAD_IN
            if i == n - 1:
                d += TAIL + (n - 1) * XFADE
            else:
                d += GAP
            scene_d.append(d)

        # 3. Background per block, in order of preference: AI art (if OPENAI_API_KEY has
        # credit) -> free real stock footage (Pexels/Pixabay, via the prompt as a search
        # query) -> a plain gradient as the last resort. Genuine scene changes, not one
        # continuous clip. Prompts cycle if there are fewer than blocks.
        bg_inputs: list[str] = []
        bg_pre = ""
        bg_sources: list[str] = []
        for i, d in enumerate(scene_d):
            prompt = bg_prompts[i % len(bg_prompts)] if bg_prompts else None
            img = generate_background(prompt, tmp_dir / f"scene{i:02d}.png") if prompt else None
            clip = None if img else (get_stock_clip(variant + i, prompt) if prompt else None)
            bg_sources.append("ai" if img else "stock" if clip else "gradient")
            if img:
                bg_pre += (
                    f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"scale={int(W*1.12)}:{int(H*1.12)},"
                    f"zoompan=z='min(1.08,1+0.0003*on)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
                    f":d={int(d*30)}:s={W}x{H}:fps=30,"
                    f"eq=brightness=-0.08:saturation=0.92,setsar=1[bg{i}];"
                )
                bg_inputs += ["-loop", "1", "-t", f"{d:.2f}", "-i", str(img)]
            elif clip:
                bg_pre += (
                    f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"fps=30,eq=brightness=-0.14:saturation=0.88,setsar=1[bg{i}];"
                )
                bg_inputs += ["-stream_loop", "-1", "-t", f"{d:.2f}", "-i", str(clip)]
            else:
                top, bot = SOFT_GRADIENTS[(variant + i) % len(SOFT_GRADIENTS)]
                grad = tmp_dir / f"grad{i:02d}.png"
                _gradient_bg(W, H, top, bot).save(grad)
                bg_pre += (
                    f"[{i}:v]scale={int(W*1.15)}:{int(H*1.15)},"
                    f"zoompan=z='min(1.1,1+0.0004*on)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
                    f":d={int(d*30)}:s={W}x{H}:fps=30,setsar=1[bg{i}];"
                )
                bg_inputs += ["-loop", "1", "-t", f"{d:.2f}", "-i", str(grad)]

        # 4. Stitch scenes with real crossfades (ffmpeg xfade), not hard cuts.
        if n == 1:
            bg_chain = bg_pre + "[bg0]"
        else:
            chain = bg_pre
            running = "bg0"
            cum = scene_d[0]
            for i in range(1, n):
                offset = cum - i * XFADE
                out_label = f"bgx{i}"
                chain += f"[{running}][bg{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.2f}[{out_label}];"
                running = out_label
                cum += scene_d[i]
            bg_chain = chain + f"[{running}]"
        bg_chain += f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_start:.2f}:d=1.5[bg];"

        # 5. Captions: only the current block's lines are ever on screen.
        cap_inputs: list[str] = []
        cap_chain = ""
        prev = "bg"
        cap_idx0 = n  # background inputs occupy indices [0, n)
        for i, (_, start, end) in enumerate(timed):
            idx = cap_idx0 + i
            png = tmp_dir / f"cap{i:02d}.png"
            _block_caption(blocks[i], png, watermark if i == 0 else "")
            cap_inputs += ["-loop", "1", "-t", f"{total:.2f}", "-i", str(png)]
            cap_chain += (
                f"[{idx}:v]format=rgba,fade=t=in:st={max(0.0, start-0.25):.2f}:d=0.55:alpha=1,"
                f"fade=t=out:st={max(start, end-0.2):.2f}:d=0.45:alpha=1[c{i}];"
                f"[{prev}][c{i}]overlay=0:0:enable='between(t,{max(0.0, start-0.3):.2f},{end+0.25:.2f})'[v{i}];"
            )
            prev = f"v{i}"

        # 6. Narration timeline + a ducked music bed underneath it.
        voice_idx0 = cap_idx0 + n
        audio_inputs: list[str] = []
        for audio, _, _ in timed:
            audio_inputs += ["-i", str(audio)]
        legs = ""
        for i, (_, start, _) in enumerate(timed):
            legs += f"[{voice_idx0+i}:a]adelay={int(start*1000)}|{int(start*1000)}[d{i}];"
        mix_ins = "".join(f"[d{i}]" for i in range(n))
        legs += f"{mix_ins}amix=inputs={n}:normalize=0,volume=1.6[speech];"

        music = _music_files()
        if music:
            track = music[variant % len(music)]
            music_idx = voice_idx0 + n
            audio_inputs += ["-stream_loop", "-1", "-t", f"{total:.2f}", "-i", str(track)]
            legs += (
                f"[{music_idx}:a]volume=0.13,afade=t=in:st=0:d=1.2,"
                f"afade=t=out:st={fade_out_start:.2f}:d=1.5[bed];"
                f"[speech][bed]amix=inputs=2:duration=first:normalize=0[a]"
            )
        else:
            legs += "[speech]anull[a]"

        cmd = [
            "ffmpeg", "-y", *bg_inputs, *cap_inputs, *audio_inputs,
            "-filter_complex", f"{bg_chain}{cap_chain}{legs}",
            "-map", f"[{prev}]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-t", f"{total:.2f}",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [soul_reel] ffmpeg failed: {result.stderr[-800:]}")
            return None
        src_summary = ",".join(bg_sources)
        print(f"  [soul_reel] {total:.1f}s, {n} scenes ({src_summary}), voice={voice}")
    return out_path
