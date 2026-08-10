"""Render a text card via a headless browser instead of PIL.

Why: PIL's ImageDraw can't shape complex scripts (Bengali conjuncts, matras)
without libraqm, and the standard PyPI Pillow wheel doesn't bundle it. A real
browser engine shapes any script correctly with zero extra native deps beyond
Chromium itself, and gives proper CSS text layout instead of hand-rolled wrapping.

Used for the Mamun Hossain page (Bangla) — Psychology Tube's English content
keeps using image_maker.py/PIL, which works fine for Latin script.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1080, 1080

# Matches Nasir Uddin Shamim's signature hook-card look: solid color background,
# bold white (optionally yellow-highlighted) text, centered, generous line-height.
CARD_CSS = """
@font-face {
  font-family: 'BengaliSans';
  src: local('Nirmala UI'), local('Noto Sans Bengali'), local('Vrinda');
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: %(w)dpx; height: %(h)dpx;
  background: %(bg)s;
  display: flex; align-items: center; justify-content: center;
  font-family: 'BengaliSans', 'Noto Sans Bengali', 'Nirmala UI', 'Segoe UI', sans-serif;
}
.card {
  width: 90%%; text-align: center;
  color: #ffffff;
  font-size: %(size)dpx; font-weight: 800; line-height: 1.35;
  text-shadow: 0 2px 6px rgba(0,0,0,0.35);
}
.hl { background: #ffd400; color: #1a1a1a; padding: 0 10px; border-radius: 6px; }
.arrow { font-size: 90px; margin-top: 40px; }
"""


def _html(text_html: str, bg: str, font_size: int, arrow: bool) -> str:
    arrow_html = '<div class="arrow">&#x1F447;</div>' if arrow else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{CARD_CSS % {"w": W, "h": H, "bg": bg, "size": font_size}}</style>
</head><body><div><div class="card">{text_html}</div>{arrow_html}</div></body></html>"""


def make_hook_card(text: str, out_path: Path, bg: str = "#c00000",
                    highlight: str | None = None, font_size: int = 56,
                    arrow: bool = True) -> Path:
    """text may contain a literal '\\n' for manual line breaks. Wrap the phrase
    that should get the yellow highlight (matching his style) in {{ }} - the
    braces themselves are stripped, only the wrapped phrase is highlighted."""
    html_text = text.replace("\n", "<br>")
    if highlight:
        inner = highlight.strip("{}")
        html_text = html_text.replace(highlight, f'<span class="hl">{inner}</span>')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(_html(html_text, bg, font_size, arrow))
        page.screenshot(path=str(out_path))
        browser.close()
    return out_path
