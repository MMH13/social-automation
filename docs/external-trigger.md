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

### Schedule — 7 jobs (set the account timezone to UTC first)

cron-job.org defaults to your local timezone. Set it to **UTC** in account settings
before adding these, or every slot lands 6 hours out.

These are 24h / 7 = 3h25m apart, matching `SLOT_MINUTES` in `src/post_ss.py`:

| # | UTC (enter this) | Dhaka |
|---|---|---|
| 1 | `00:00` | 06:00 |
| 2 | `03:26` | 09:26 |
| 3 | `06:51` | 12:51 |
| 4 | `10:17` | 16:17 |
| 5 | `13:43` | 19:43 |
| 6 | `17:09` | 23:09 |
| 7 | `20:34` | 02:34 |

If you change these, change `SLOT_MINUTES` to match — the pacing logic decides how many
posts are due from that list, so a mismatch makes runs think they are behind or ahead.

Leave the workflow's own `schedule:` block in place as a fallback for when the external
service has an outage. A doubled trigger is harmless: the run no-ops once the slots due
so far are already posted.

Other pages use the same setup with a different workflow file in the URL — but their
schedules are still the old hourly ones, so copy the hours from the `cron:` line in each
workflow rather than from here:

| Page | Workflow file |
|---|---|
| Speaking from soul | `post-ss.yml` |
| Psychology Tube | `post-memes.yml` |
| Mamun Hossain | `post-mh.yml` |

## Notes

- **X is `disabled_manually`** — it will not run from cron *or* an external trigger
  until it is re-enabled in the Actions tab, and its API credits are topped up
  (it was failing `402 Payment Required` before it was disabled).
- The token is a credential: keep it in `.env` and the cron service only. It is not a
  repo secret and must never be committed.
- If posts stop, check the token's expiry first — that is the most likely cause.
