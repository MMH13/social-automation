"""Black 16:9 photocard for "Speaking from soul".

2026-11-19: Mamun picked this look from previews - plain black, one short line in small
white serif centred on the card, a faint page name at the bottom. Replaces the old
square gradient quote card (image_maker.make_quote_card), whose 94 posts reached ~1 person
each. The font ships in assets/fonts so the GitHub runner renders exactly what was
previewed (the old cards silently fell back to DejaVu on the runner).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
REPO = Path(__file__).resolve().parents[2]
FONT = REPO / "assets" / "fonts" / "Gelasio-Variable.ttf"
TEXT_SIZE = 50
MIN_SIZE = 40
MAX_LINES = 4
MAX_W = W * 0.55          # keeps the line in the middle with wide black margins
TEXT_FILL = (245, 245, 245)
MARK_FILL = (120, 120, 120)
MARK_TOP = H - 80         # text never enters the band below MARK_TOP - 40


def _font(size: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_name("Regular")
    except (OSError, ValueError, AttributeError):
        pass
    return f


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, limit: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= limit or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def layout(text: str) -> tuple[int, list[str]]:
    """Font size and balanced lines. Shrinks the font before ever exceeding MAX_LINES."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for size in range(TEXT_SIZE, MIN_SIZE - 1, -2):
        font = _font(size)
        lines = _wrap(probe, text, font, MAX_W)
        if len(lines) > 1:
            # Balance the rows so one word is never left alone on the last line.
            total = probe.textlength(text, font=font)
            balanced = _wrap(probe, text, font, min(MAX_W, total / len(lines) * 1.12))
            if len(balanced) == len(lines):
                lines = balanced
        if len(lines) <= MAX_LINES:
            return size, lines
    return MIN_SIZE, lines


def make_photocard(text: str, out_path: Path, watermark: str = "speaking from soul") -> Path:
    # Gelasio draws the straight ' as a slanted prime ("I′m"); use typographic quotes.
    text = " ".join(text.split()).replace("'", "’")
    size, lines = layout(text)
    font = _font(size)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    lh = int(size * 1.45)
    y = (H - lh * len(lines)) // 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=font)) / 2, y), ln, font=font, fill=TEXT_FILL)
        y += lh
    if watermark:
        wf = _font(26)
        d.text(((W - d.textlength(watermark, font=wf)) / 2, MARK_TOP), watermark,
               font=wf, fill=MARK_FILL)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=95)
    return out_path
