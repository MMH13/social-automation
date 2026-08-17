"""Render a text card via a headless browser instead of PIL.

Why: PIL's ImageDraw can't shape complex scripts (Bengali conjuncts, matras)
without libraqm, and the standard PyPI Pillow wheel doesn't bundle it. A real
browser engine shapes any script correctly with zero extra native deps beyond
Chromium itself, and gives proper CSS text layout instead of hand-rolled wrapping.

Font note: fonts load from Google Fonts over the network rather than relying on
a locally-installed Bengali font. A `local('Nirmala UI')` fallback works when
testing on this Windows PC (which ships it) but the Ubuntu GitHub Actions
runner has no Bengali font installed at all - relying on `local()` there would
silently fall back to tofu/no-glyphs. Google Fonts works identically on both.

Theme + *word* highlight syntax matches the proven format from the older
meta-automation project (14 real reference posts analyzed 2026-08-03): crimson
reserved for fear/curiosity + personal-development hooks, black is the default
for everything else - color themes beyond those two were tried and dropped
after real engagement data showed he doesn't use them.

Used for the Mamun Hossain page (Bangla) — Psychology Tube's English content
keeps using image_maker.py/PIL, which works fine for Latin script.
"""
import re
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1080, 1080

THEMES = {  # (background, text, accent-for-*highlighted* words)
    "crimson": ("#e8112d", "#ffffff", "#ffd60a"),
    "black": ("#0a0a0a", "#ffffff", "#ffd60a"),
}

_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link href="https://fonts.googleapis.com/css2?'
          'family=Anek+Bangla:wght@700;800&family=Hind+Siliguri:wght@600;700'
          '&display=swap" rel="stylesheet">')

CARD_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: %(w)dpx; height: %(h)dpx;
  background: %(bg)s;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Anek Bangla', 'Hind Siliguri', sans-serif;
}
.card {
  width: 88%%; text-align: center;
  color: %(fg)s;
  font-size: %(size)dpx; font-weight: 800; line-height: 1.4;
  text-shadow: 0 2px 6px rgba(0,0,0,0.35);
}
.hl { color: %(accent)s; }
.arrow { font-size: 90px; margin-top: 40px; }
"""


def _lines_html(text: str) -> str:
    """*word* segments (whole line or inline, one or many per card) become
    accent-colored spans - matches the proven page's inline-highlight style,
    not a boxed/pill highlight."""
    out = []
    for ln in text.strip().split("\n"):
        html = re.sub(r"\*(.+?)\*", lambda m: f'<span class="hl">{m.group(1)}</span>',
                      escape(ln.strip()))
        out.append(html)
    return "<br>".join(out)


def _html(text_html: str, bg: str, fg: str, accent: str, font_size: int, arrow: bool) -> str:
    arrow_html = '<div class="arrow">&#x1F447;</div>' if arrow else ""
    css = CARD_CSS % {"w": W, "h": H, "bg": bg, "fg": fg, "accent": accent, "size": font_size}
    return f"""<!doctype html><html><head><meta charset="utf-8">{_FONTS}
<style>{css}</style>
</head><body><div><div class="card">{text_html}</div>{arrow_html}</div></body></html>"""


def make_hook_card(text: str, out_path: Path, theme: str = "black",
                    font_size: int = 56, arrow: bool = True) -> Path:
    """text may contain literal '\\n' for line breaks. Wrap any word or phrase
    in *stars* to accent-color it - supports multiple per card, matching the
    proven live format (not a single all-or-nothing highlight)."""
    bg, fg, accent = THEMES[theme]
    html_text = _lines_html(text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(_html(html_text, bg, fg, accent, font_size, arrow))
        page.wait_for_timeout(300)  # let the web font finish loading before the shot
        page.screenshot(path=str(out_path))
        browser.close()
    return out_path
