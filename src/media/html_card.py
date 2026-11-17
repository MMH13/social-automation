"""Render a high-converting text card via a headless browser.

V2 Design Standard (Updated Nov 2026):
  - Deep radial gradient background (Charcoal Radial or Crimson Radial) for maximum contrast
  - Top category pill badge (e.g. '⚡ AI & PRODUCTIVITY' or '🚨 CRITICAL WARNING')
  - Bold, commanding typography (68px font size, drop shadows, Anek Bangla / Hind Siliguri)
  - Inline accent highlights (*word* becomes high-visibility yellow #ffd60a)
  - Glassmorphism comment indicator pill ('ডিটেইলস কমেন্টে দেওয়া আছে 👇')
  - Author brand footer ('(M) Mamun Hossain' + '+ Follow' badge)
"""
import re
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1080, 1080

THEMES = {
    "black": {
        "bg_gradient": "radial-gradient(circle at 50% 45%, #18181b 0%, #09090b 100%)",
        "fg": "#f8fafc",
        "accent": "#ffd60a",
        "badge_bg": "rgba(255, 214, 10, 0.12)",
        "badge_border": "rgba(255, 214, 10, 0.35)",
        "badge_color": "#ffd60a",
        "cue_bg": "rgba(255, 255, 255, 0.08)",
        "cue_border": "rgba(255, 255, 255, 0.15)",
        "cue_color": "#cbd5e1",
        "footer_border": "rgba(255, 255, 255, 0.14)",
        "avatar_bg": "linear-gradient(135deg, #e11d48, #fbbf24)",
        "avatar_fg": "#000000",
        "brand_name_color": "#f8fafc",
        "follow_bg": "#ffffff",
        "follow_fg": "#09090b",
        "default_category": "⚡ AI & PRODUCTIVITY",
    },
    "crimson": {
        "bg_gradient": "radial-gradient(circle at 50% 45%, #e11d48 0%, #881337 100%)",
        "fg": "#ffffff",
        "accent": "#ffd60a",
        "badge_bg": "rgba(0, 0, 0, 0.25)",
        "badge_border": "rgba(255, 255, 255, 0.35)",
        "badge_color": "#ffffff",
        "cue_bg": "rgba(0, 0, 0, 0.25)",
        "cue_border": "rgba(255, 255, 255, 0.25)",
        "cue_color": "#ffffff",
        "footer_border": "rgba(255, 255, 255, 0.2)",
        "avatar_bg": "#ffffff",
        "avatar_fg": "#881337",
        "brand_name_color": "#ffffff",
        "follow_bg": "#ffffff",
        "follow_fg": "#881337",
        "default_category": "🚨 CRITICAL WARNING",
    },
}

_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Anek+Bangla:wght@700;800;900&family=Hind+Siliguri:wght@600;700'
    '&family=Plus+Jakarta+Sans:wght@700;800&display=swap" rel="stylesheet">'
)


def _lines_html(text: str) -> str:
    """Format lines and convert *words* into highlighted spans."""
    clean_lines = []
    for ln in text.strip().split("\n"):
        ln_clean = ln.strip()
        # Clean trailing pointing arrows since the V2 template has a dedicated comment cue pill
        ln_clean = re.sub(r"\s*👇\s*$", "", ln_clean).strip()
        if not ln_clean:
            continue
        html = re.sub(
            r"\*(.+?)\*",
            lambda m: f'<span class="hl">{escape(m.group(1))}</span>',
            escape(ln_clean),
        )
        clean_lines.append(html)
    return "<br>".join(clean_lines)


def _html(text_html: str, theme_cfg: dict, category: str, font_size: int) -> str:
    cat_text = category or theme_cfg["default_category"]
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
{_FONTS}
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  width: {W}px; height: {H}px;
  background: {theme_cfg["bg_gradient"]};
  color: {theme_cfg["fg"]};
  display: flex; flex-direction: column;
  justify-content: space-between; align-items: center;
  font-family: 'Anek Bangla', 'Hind Siliguri', sans-serif;
  padding: 70px 70px 50px 70px;
  position: relative;
}}
.top-badge {{
  display: inline-flex; align-items: center; gap: 8px;
  background: {theme_cfg["badge_bg"]};
  border: 1px solid {theme_cfg["badge_border"]};
  color: {theme_cfg["badge_color"]};
  padding: 10px 24px; border-radius: 999px;
  font-size: 24px; font-weight: 700; letter-spacing: 0.5px;
  text-transform: uppercase;
}}
.center-box {{
  width: 100%; text-align: center;
  margin: auto 0;
}}
.hook-text {{
  font-size: {font_size}px; font-weight: 800; line-height: 1.35;
  color: {theme_cfg["fg"]};
  text-shadow: 0 4px 18px rgba(0,0,0,0.55);
}}
.hl {{
  color: {theme_cfg["accent"]};
  text-shadow: 0 0 25px rgba(255, 214, 10, 0.35);
}}
.comment-cue {{
  display: inline-flex; align-items: center; gap: 10px;
  margin-top: 36px;
  font-size: 30px; font-weight: 700;
  color: {theme_cfg["cue_color"]};
  background: {theme_cfg["cue_bg"]};
  padding: 12px 30px; border-radius: 50px;
  border: 1px solid {theme_cfg["cue_border"]};
}}
.comment-cue span {{ font-size: 34px; }}
.footer {{
  width: 100%;
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 25px;
  border-top: 1px solid {theme_cfg["footer_border"]};
}}
.brand {{
  display: flex; align-items: center; gap: 14px;
}}
.brand-avatar {{
  width: 50px; height: 50px; border-radius: 50%;
  background: {theme_cfg["avatar_bg"]};
  display: flex; align-items: center; justify-content: center;
  font-weight: 900; font-size: 24px; color: {theme_cfg["avatar_fg"]};
  font-family: 'Plus Jakarta Sans', sans-serif;
}}
.brand-name {{
  font-size: 28px; font-weight: 700; color: {theme_cfg["brand_name_color"]};
  font-family: 'Plus Jakarta Sans', sans-serif;
}}
.follow-pill {{
  background: {theme_cfg["follow_bg"]}; color: {theme_cfg["follow_fg"]};
  font-size: 22px; font-weight: 800;
  padding: 10px 24px; border-radius: 999px;
  font-family: 'Plus Jakarta Sans', sans-serif;
}}
</style>
</head>
<body>
  <div class="top-badge">{escape(cat_text)}</div>
  <div class="center-box">
    <div class="hook-text">{text_html}</div>
    <div class="comment-cue">
      ডিটেইলস কমেন্টে দেওয়া আছে <span>👇</span>
    </div>
  </div>
  <div class="footer">
    <div class="brand">
      <div class="brand-avatar">M</div>
      <div class="brand-name">Mamun Hossain</div>
    </div>
    <div class="follow-pill">+ Follow</div>
  </div>
</body>
</html>"""


def make_hook_card(
    text: str,
    out_path: Path,
    theme: str = "black",
    font_size: int = 68,
    category: str = None,
    arrow: bool = False,
) -> Path:
    """Generate high-converting V2 hook card."""
    theme_cfg = THEMES.get(theme, THEMES["black"])
    html_text = _lines_html(text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(_html(html_text, theme_cfg, category, font_size))
        page.wait_for_timeout(400)
        page.screenshot(path=str(out_path))
        browser.close()
    return out_path
