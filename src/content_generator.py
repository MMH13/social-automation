"""Generate a full content package (topic, captions, image text, video script) via Claude."""
import json
import os

import anthropic

PROMPT = """You are a social media content creator for the brand "{brand_name}".
Niche: {niche}
Voice: {brand_voice}
Language: {language}
Standard call to action: {cta}

Recently used topics (do NOT repeat or closely rephrase these):
{recent_topics}

Create ONE fresh piece of content for today. Respond with ONLY valid JSON, no markdown fences:
{{
  "topic": "short internal label for this post",
  "image_headline": "max 8 words, punchy, fits on an image",
  "image_subtext": "max 15 words supporting line",
  "captions": {{
    "x": "max 260 chars incl. 2-3 hashtags",
    "facebook": "2-4 sentences, conversational, 3-5 hashtags at end",
    "instagram": "2-4 sentences, line breaks ok, 8-12 hashtags at end",
    "linkedin": "3-6 sentences, professional but personal, 3-5 hashtags",
    "tiktok": "1-2 sentences hook + 4-6 hashtags",
    "youtube_title": "max 90 chars, curiosity-driven",
    "youtube_description": "2-3 sentences + hashtags"
  }},
  "video_script": ["hook line (max 10 words)", "point 1", "point 2", "point 3", "CTA line"]
}}"""


def generate(cfg: dict, recent_topics: list[str]) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = PROMPT.format(
        brand_name=cfg["brand_name"],
        niche=cfg["niche"],
        brand_voice=cfg["brand_voice"],
        language=cfg["language"],
        cta=cfg["call_to_action"],
        recent_topics="\n".join(f"- {t}" for t in recent_topics) or "(none yet)",
    )
    resp = client.messages.create(
        model=cfg.get("model", "claude-sonnet-5"),
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    # Strip accidental code fences before parsing
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    return json.loads(text)


def sample_package() -> dict:
    """Offline sample used by --dry-run so the pipeline can be tested with no API key."""
    return {
        "topic": "dry-run sample: 50/30/20 budgeting rule",
        "image_headline": "The 50/30/20 Rule, Simplified",
        "image_subtext": "Needs, wants, savings — one paycheck, three buckets.",
        "captions": {
            "x": "Budgeting doesn't need a spreadsheet. 50% needs, 30% wants, 20% savings. Start this month. #PersonalFinance #MoneyTips",
            "facebook": "Ever feel like your salary disappears? Try the 50/30/20 rule. It takes five minutes to set up. #budgeting #money #savings",
            "instagram": "Your paycheck, three buckets.\n50% needs. 30% wants. 20% future you.\n#budget #moneytips #finance #savings #personalfinance #money #financialfreedom #investing",
            "linkedin": "The simplest budgeting framework I know: 50/30/20. Most people skip the 20 — automate it and you won't. #personalfinance #careers #money",
            "tiktok": "The only budget rule you need. #budget #moneytok #finance #savings #fyp",
            "youtube_title": "The 5-Minute Budget That Actually Sticks (50/30/20)",
            "youtube_description": "How to split every paycheck in five minutes. #budgeting #money",
        },
        "video_script": [
            "Your salary has a leak.",
            "50% goes to needs — rent, food, bills.",
            "30% to wants — guilt-free.",
            "20% to savings, automated on payday.",
            "Follow for more daily tips.",
        ],
    }
