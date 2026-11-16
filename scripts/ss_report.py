# -*- coding: utf-8 -*-
"""Which Speaking from soul reels perform, and why - plus a queue reorder from the answer.

Reads the per-reel engagement written by scripts/ss_insights.py, joins it with the queue
(theme, hook_style, phrase count, voice, scenes, post hour) and prints a leaderboard and
breakdowns. With --reorder it moves the unposted reels so the themes/hooks that earn the
most come first (never the same theme back to back).

Score = plays/median + watch/median + 3*followers + 2*shares + 0.5*reactions. Plays barely
vary (reach is capped near the follower count) so watch time, shares and followers carry it.

Usage:
  python scripts/ss_insights.py out.json --since=2026-10-18 --types=reel2
  python scripts/ss_report.py out.json [--reorder]
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

QUEUE = Path(__file__).resolve().parent.parent / "scheduled_ss" / "content.json"
# A distribution blackout (0-2 plays per reel regardless of content) is excluded from every comparison.
BLACKOUT = ("2026-10-23T05:00", "2026-10-27T00:00")
MIN_N = 5


def build(rows, queue):
    ok = [r for r in rows if r.get("plays") is not None and r["id"] in queue
          and not (BLACKOUT[0] <= r["posted_at"] < BLACKOUT[1])]
    for r in ok:
        m = queue[r["id"]]
        r["theme"] = m.get("theme")
        r["hook"] = m.get("hook_style") or "untagged"
        r["voice"] = m.get("voice") or "am_michael"
        r["n"] = len(m["phrases"])
        r["w1"] = len(m["phrases"][0].split())
        r["hour"] = int(r["posted_at"][11:13])
        r["watch_s"] = (r["avg_watch_ms"] or 0) / 1000
        r["text"] = " ".join(m["phrases"])
    pl = st.median(r["plays"] for r in ok)
    wt = st.median(r["watch_s"] for r in ok)
    for r in ok:
        r["score"] = round(r["plays"] / max(pl, 1) + r["watch_s"] / max(wt, 0.1)
                           + 3 * (r.get("followers_gained") or 0) + 2 * (r.get("shares") or 0)
                           + 0.5 * (r.get("reactions_total") or 0), 2)
    return ok


def table(ok, title, key):
    by = defaultdict(list)
    for r in ok:
        by[key(r)].append(r)
    print(f"\n== {title} ==")
    for k, rs in sorted(by.items(), key=lambda kv: -st.mean(x["score"] for x in kv[1])):
        if len(rs) < MIN_N:
            continue
        print(f"  {str(k):28s} n={len(rs):3d} score={st.mean(x['score'] for x in rs):5.2f} "
              f"plays={st.median(x['plays'] for x in rs):6.1f} watch={st.mean(x['watch_s'] for x in rs):.1f}s "
              f"ret5={st.mean(x['ret_5s'] or 0 for x in rs):.0%} fol={sum(x.get('followers_gained') or 0 for x in rs)} "
              f"sh={sum(x.get('shares') or 0 for x in rs)}")


def means(ok, key):
    by = defaultdict(list)
    for r in ok:
        by[key(r)].append(r["score"])
    return {k: st.mean(v) for k, v in by.items() if len(v) >= MIN_N}


def reorder(ok, queue_list):
    theme_m = means(ok, lambda r: r["theme"])
    hook_m = means(ok, lambda r: r["hook"] if r["hook"] != "untagged" else None)
    n_m = means(ok, lambda r: r["n"])
    base = st.mean(r["score"] for r in ok)

    def predicted(m):
        t = theme_m.get(m.get("theme"), base)
        h = hook_m.get(m.get("hook_style"), t)
        n = n_m.get(len(m["phrases"]), base)
        return 0.5 * t + 0.3 * h + 0.2 * n

    pool = [m for m in queue_list if m["type"] == "reel2" and not m.get("posted_at") and not m.get("skip")]
    pool.sort(key=predicted, reverse=True)
    ordered, recent = [], []
    while pool:
        pick = next((m for m in pool if m.get("theme") not in recent[-2:]), pool[0])
        pool.remove(pick)
        ordered.append(pick)
        recent.append(pick.get("theme"))
    ids = {m["id"] for m in ordered}
    slots = iter(ordered)
    out = [next(slots) if (m["id"] in ids) else m for m in queue_list]
    return out, ordered


def main() -> int:
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    queue_list = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue = {m["id"]: m for m in queue_list}
    ok = build(rows, queue)
    print(f"reels analysed: {len(ok)} of {len(rows)} (blackout excluded)")
    table(ok, "THEME", lambda r: r["theme"])
    table(ok, "HOOK STYLE", lambda r: r["hook"])
    table(ok, "VOICE", lambda r: r["voice"])
    table(ok, "PHRASES", lambda r: r["n"])
    table(ok, "POST HOUR (UTC, 3h)", lambda r: f"{(r['hour'] // 3) * 3:02d}-{(r['hour'] // 3) * 3 + 2:02d}h")
    print("\n== TOP 10 ==")
    for r in sorted(ok, key=lambda r: -r["score"])[:10]:
        print(f"  {r['score']:5.2f} plays {r['plays']:3d} watch {r['watch_s']:.1f}s fol {r.get('followers_gained')} "
              f"| {r['theme']} | {r['hook']} | {r['text'][:70]}")
    if "--reorder" in sys.argv:
        new, ordered = reorder(ok, queue_list)
        QUEUE.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nreordered {len(ordered)} unposted reels; next 8 themes: {[m['theme'] for m in ordered[:8]]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
