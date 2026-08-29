# -*- coding: utf-8 -*-
"""Fire a workflow via the GitHub API — the call an external cron service makes.

GitHub's own `schedule:` events are best-effort and were only delivering 25-35% of
this repo's runs (5-7 of 20/day, measured 2026-08-29), which is why posts bunched
up instead of landing on time. An external scheduler calling workflow_dispatch is
not subject to that throttling, so slots fire when they are supposed to.

Usage (local test, reads GH_TRIGGER_TOKEN from .env or the environment):
    python scripts/trigger_workflow.py post-ss.yml
    python scripts/trigger_workflow.py post-ss.yml --check   # verify token only

The external service does the same thing as a plain HTTPS request:
    POST https://api.github.com/repos/MMH13/social-automation/actions/workflows/<file>/dispatches
    Authorization: Bearer <token>
    Accept: application/vnd.github+json
    Body: {"ref": "master"}
"""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
REPO = "MMH13/social-automation"
BRANCH = "master"
API = "https://api.github.com"


def token() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    tok = os.environ.get("GH_TRIGGER_TOKEN", "").strip()
    if not tok:
        sys.exit("GH_TRIGGER_TOKEN not set (add it to .env or the environment).")
    return tok


def check(tok: str) -> int:
    """Confirm the token can actually see the repo's workflows before you wire it
    into a scheduler — a token missing Actions write fails silently at 3am otherwise."""
    r = requests.get(f"{API}/repos/{REPO}/actions/workflows",
                     headers={"Authorization": f"Bearer {tok}",
                              "Accept": "application/vnd.github+json"}, timeout=30)
    if r.status_code != 200:
        print(f"FAILED {r.status_code}: {r.text[:300]}")
        print("\nToken needs repo access with Actions: Read and write.")
        return 1
    names = [w["path"].split("/")[-1] for w in r.json().get("workflows", [])]
    print(f"OK - token can read {REPO}. Workflows: {', '.join(names)}")
    return 0


def dispatch(tok: str, workflow: str) -> int:
    r = requests.post(
        f"{API}/repos/{REPO}/actions/workflows/{workflow}/dispatches",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
        data=json.dumps({"ref": BRANCH}), timeout=30,
    )
    if r.status_code == 204:
        print(f"OK - dispatched {workflow} on {BRANCH}")
        return 0
    print(f"FAILED {r.status_code}: {r.text[:300]}")
    return 1


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tok = token()
    if "--check" in sys.argv:
        return check(tok)
    if not args:
        print(__doc__)
        return 2
    return dispatch(tok, args[0])


if __name__ == "__main__":
    raise SystemExit(main())
