# External trigger (fixes posting times)

## Why

GitHub's `schedule:` cron is best-effort. Measured on 2026-08-29, this repo asked for
20 scheduled runs/day and GitHub delivered **5–7** — a 25–35% delivery rate, with
individual runs arriving 30 minutes to 4 hours late. That is why posts bunched up
instead of landing on schedule.

`workflow_dispatch` calls through the API are **not** throttled that way. An external
scheduler calling the API fires slots on time.

The in-repo catch-up logic (`DAILY_TARGET` / `MAX_PER_RUN` in `src/post_ss.py`) already
fixes the *volume* problem. This fixes the *timing* problem. Keep both: if the external
trigger ever lapses, catch-up still gets the day's posts out.

## Step 1 — create the token (must be done in your browser)

github.com → Settings → Developer settings → **Fine-grained personal access tokens** →
Generate new token.

- **Repository access:** Only select repositories → `MMH13/social-automation`
- **Permissions:** Repository permissions → **Actions: Read and write**
  (that single permission is all it needs — do not grant more)
- **Expiration:** set a reminder; the trigger dies silently when it expires

Copy the token (starts `github_pat_`). It is shown once.

## Step 2 — verify the token works

Add it to `.env` (git-ignored):

```
GH_TRIGGER_TOKEN=github_pat_...
```

Then:

```bash
python scripts/trigger_workflow.py post-ss.yml --check
```

Expect `OK - token can read MMH13/social-automation`. If it 404s or 403s, the token is
missing the Actions permission or the repo was not selected.

Fire a real run to confirm end to end:

```bash
python scripts/trigger_workflow.py post-ss.yml
```

## Step 3 — set up the scheduler (needs your own account)

Any cron service that can send an HTTPS POST with headers works. cron-job.org is free
and reliable. Create one job per posting slot, all with the same request:

- **URL:** `https://api.github.com/repos/MMH13/social-automation/actions/workflows/post-ss.yml/dispatches`
- **Method:** `POST`
- **Headers:**
  - `Authorization: Bearer github_pat_...`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- **Body:** `{"ref":"master"}`
- **Expected response:** `204 No Content` (success returns an empty body)

### Schedule (UTC — cron-job.org defaults to your local timezone, set it to UTC)

Speaking from soul, 7 slots: `00:00, 03:00, 07:00, 10:00, 13:00, 17:00, 20:00`

Match `.github/workflows/post-ss.yml`. Leave the workflow's own `schedule:` block in
place as a fallback for when the external service has an outage — the run is a no-op
once the day's target is met, so a doubled trigger costs nothing.

Other pages, if you want them on the external trigger too — same setup, different
workflow file in the URL:

| Page | Workflow file | Slots (UTC) |
|---|---|---|
| Speaking from soul | `post-ss.yml` | 00, 03, 07, 10, 13, 17, 20 |
| Psychology Tube | `post-memes.yml` | 00, 02, 05, 07, 10, 12, 15, 17, 20, 22 |
| Mamun Hossain | `post-mh.yml` | 03, 09, 15 |

## Notes

- **X is `disabled_manually`** — it will not run from cron *or* an external trigger
  until it is re-enabled in the Actions tab, and its API credits are topped up
  (it was failing `402 Payment Required` before it was disabled).
- The token is a credential: keep it in `.env` and the cron service only. It is not a
  repo secret and must never be committed.
- If posts stop, check the token's expiry first — that is the most likely cause.
