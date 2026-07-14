# Social Media Automation

Generates AI content (post text + branded image + short vertical video) and publishes it
automatically to **X, Facebook Page, Instagram, and LinkedIn**, three times a day.
**TikTok and YouTube** shorts land in a ready-to-upload `queue/` folder (or publish
automatically via upload-post.com if you enable it).

## How one run works

1. Claude generates a fresh topic in your niche (checks `state/history.jsonl` to avoid repeats)
   plus platform-tailored captions and a 5-line video script.
2. Pillow renders a branded 1080x1080 image; ffmpeg renders a 1080x1920 short video.
3. Each configured platform gets its post. Platforms with missing credentials are skipped
   with a warning — go live one platform at a time.
4. Everything is saved under `output/<timestamp>/` and logged to `state/runs.log`.

## Setup

```powershell
pip install -r requirements.txt
copy .env.example .env     # then fill in keys (see below)
# edit config/config.yaml  -> set your niche, brand name, voice
python -m src.main --dry-run   # test: generates image+video locally, posts nothing
python -m src.main             # real run
.\schedule_tasks.ps1           # register 3 daily runs (09:00, 13:30, 19:00)
```

**Your PC must be on and awake at the scheduled times.** If you want this to run 24/7
without your PC, the same code can be moved to a small cloud VM or GitHub Actions later.

## Getting the credentials (one-time, ~1-2 hours total)

| Platform | Where | What to do |
|---|---|---|
| Claude API | console.anthropic.com | Create key → `ANTHROPIC_API_KEY` |
| X | developer.x.com | Free tier → create app → OAuth 1.0a, Read+Write → 4 keys |
| Facebook + Instagram | developers.facebook.com | App → Graph API → long-lived Page token with `pages_manage_posts`, `instagram_content_publish`; IG must be a Business account linked to the Page |
| Cloudinary | cloudinary.com | Free account (Instagram requires media at a public URL) |
| LinkedIn | developer.linkedin.com | App → "Share on LinkedIn" + OpenID products → access token with `w_member_social` |
| upload-post (optional) | upload-post.com | Connect TikTok+YouTube there, set API key, switch `video_delivery: upload_post` |

Ask Claude Code to walk you through any of these step by step.

## Notes & limits

- X free API tier: ~17 posts/day — 3/day is safely inside it.
- Instagram API: 25 posts/day cap. LinkedIn tokens expire every ~60 days (regenerate).
- The Meta long-lived page token lasts ~60 days too; refresh when posts start failing.
- TikTok/YouTube direct APIs need app audits, which is why they're queued/proxied here.
- `state/runs.log` shows every run; failures are per-platform and never block the others.
