"""Render a branded 1080x1080 post image with Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1080
FONT_DIRS = [
    Path(r"C:\Windows\Fonts"),                       # Windows
    Path("/usr/share/fonts/truetype/dejavu"),        # Linux (GitHub Actions)
]
LINUX_FONT_MAP = {"arial.ttf": "DejaVuSans.ttf", "arialbd.ttf": "DejaVuSans-Bold.ttf"}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (name, LINUX_FONT_MAP.get(name, name), "arial.ttf", "DejaVuSans.ttf"):
        for d in FONT_DIRS:
            try:
                return ImageFont.truetype(str(d / candidate), size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def make_minimal_dark(text: str, out_path: Path, sub_line: str = "") -> Path:
    """Minimal viral-meme template: near-black background, small centered white text."""
    img = Image.new("RGB", (SIZE, SIZE), "#181818")
    draw = ImageDraw.Draw(img)
    font = _font("arial.ttf", 42)
    max_w = 640  # narrow text block, like the reference posts

    blocks = [b.strip() for b in text.split("\n") if b.strip()]
    lines: list[str] = []
    for b, block in enumerate(blocks):
        lines.extend(_wrap(draw, block, font, max_w))
        if b < len(blocks) - 1:
            lines.append("")  # blank line between paragraphs
    if sub_line:
        lines.extend(["", *_wrap(draw, sub_line, font, max_w)])

    line_h = 58
    y = (SIZE - len(lines) * line_h) // 2
    for line in lines:
        if line:
            w = draw.textlength(line, font=font)
            draw.text(((SIZE - w) // 2, y), line, font=font, fill="#EDEDED")
        y += line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=92)
    return out_path


def make_image(headline: str, subtext: str, style: dict, brand: str, out_path: Path) -> Path:
    img = Image.new("RGB", (SIZE, SIZE), style["bg_color"])
    draw = ImageDraw.Draw(img)

    accent = style["accent_color"]
    text_color = style["text_color"]
    draw.rectangle([0, 0, SIZE, 14], fill=accent)
    draw.rectangle([0, SIZE - 14, SIZE, SIZE], fill=accent)

    head_font = _font(style.get("font", "arialbd.ttf"), 88)
    sub_font = _font("arial.ttf", 44)
    brand_font = _font(style.get("font", "arialbd.ttf"), 36)

    margin = 90
    head_lines = _wrap(draw, headline, head_font, SIZE - 2 * margin)
    sub_lines = _wrap(draw, subtext, sub_font, SIZE - 2 * margin)

    head_h = len(head_lines) * 104
    sub_h = len(sub_lines) * 58
    y = (SIZE - head_h - 40 - sub_h) // 2

    for line in head_lines:
        draw.text((margin, y), line, font=head_font, fill=text_color)
        y += 104
    draw.rectangle([margin, y + 8, margin + 160, y + 16], fill=accent)
    y += 40
    for line in sub_lines:
        draw.text((margin, y), line, font=sub_font, fill=text_color)
        y += 58

    draw.text((margin, SIZE - 80), f"@{brand}", font=brand_font, fill=accent)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=92)
    return out_path
