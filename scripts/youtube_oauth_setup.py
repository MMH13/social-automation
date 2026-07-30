# -*- coding: utf-8 -*-
"""One-time LOCAL setup to authorize this app against your own YouTube channel.

Run this yourself, once, on your own machine — never in CI (it opens a browser).
It mints a refresh token that src/publishers/youtube_publisher.py then uses forever
(refresh tokens for apps in "Testing" publishing status on the OAuth consent screen
do NOT expire as long as you sign in as a listed test user during this flow).

Before running:
  1. console.cloud.google.com -> create/select a project -> enable "YouTube Data API v3".
  2. OAuth consent screen -> External -> add yourself as a test user -> keep status "Testing".
  3. Credentials -> Create OAuth client ID -> Application type "Desktop app".
  4. Download the JSON, save it as client_secret.json next to this script (or pass --secrets <path>).

Usage:
  python scripts/youtube_oauth_setup.py [--secrets client_secret.json]

Prints YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN to add to
.env (local) and to the repo's GitHub Actions secrets (for automated publishing).
"""
import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--secrets", default="client_secret.json",
                         help="path to the OAuth client JSON downloaded from Google Cloud Console")
    args = parser.parse_args()

    secrets_path = Path(args.secrets)
    if not secrets_path.exists():
        print(f"error: {secrets_path} not found — download it from Google Cloud Console first (see docstring)")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    creds = flow.run_local_server(port=0)
    client_config = json.loads(secrets_path.read_text(encoding="utf-8"))["installed"]

    print("\nAuthorized. Add these to .env AND to your GitHub repo's Actions secrets:\n")
    print(f"YOUTUBE_CLIENT_ID={client_config['client_id']}")
    print(f"YOUTUBE_CLIENT_SECRET={client_config['client_secret']}")
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print("\nKeep client_secret.json out of git — it's already covered by no .env commits, "
          "but double-check .gitignore before committing anything in this folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
