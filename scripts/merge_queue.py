# -*- coding: utf-8 -*-
"""Merge our just-written queue state into whatever is now on origin.

A cloud run marks an item posted by committing the queue JSON back to git. If that
push races another commit, a plain `git pull --rebase` conflicts inside the JSON and
the run dies *after* the post already went out — so the mark is lost and the next run
publishes the same item again. That happened to PT item 77 on 2026-07-28.

This merges by meaning rather than by text: an item is posted if EITHER side says it
is posted, and the earliest timestamp wins. That is safe in both directions — it can
never un-post something, so it can never cause a double-post.

Usage: python scripts/merge_queue.py <ours.json> <theirs.json>   (writes theirs.json)
       python scripts/merge_queue.py <ours.jsonl> <theirs.jsonl> --lines
"""
import json
import sys
from pathlib import Path

POSTED_FIELDS = ("posted_at", "fb_url", "ig_url", "urls", "url", "note")


def merge_lines(ours: Path, theirs: Path) -> None:
    """history.jsonl is append-only: keep the union, preserving first-seen order."""
    seen, out = set(), []
    for src in (theirs, ours):
        if not src.exists():
            continue
        for line in src.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                out.append(line)
    theirs.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    print(f"merge_queue: {theirs.name} -> {len(out)} line(s)")


def merge_queue(ours: Path, theirs: Path) -> None:
    mine = json.loads(ours.read_text(encoding="utf-8"))
    base = json.loads(theirs.read_text(encoding="utf-8")) if theirs.exists() else []

    by_id = {i["id"]: i for i in base}
    order = [i["id"] for i in base]
    applied = 0

    for item in mine:
        iid = item["id"]
        if iid not in by_id:                      # an item only we know about
            by_id[iid] = item
            order.append(iid)
            applied += 1
            continue
        theirs_item = by_id[iid]
        ours_stamp, theirs_stamp = item.get("posted_at"), theirs_item.get("posted_at")
        if ours_stamp and not theirs_stamp:
            for f in POSTED_FIELDS:
                if f in item:
                    theirs_item[f] = item[f]
            applied += 1
        elif ours_stamp and theirs_stamp and ours_stamp < theirs_stamp:
            theirs_item["posted_at"] = ours_stamp  # earliest publish wins

    merged = [by_id[i] for i in order]
    theirs.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    unposted = sum(1 for i in merged if not i.get("posted_at"))
    print(f"merge_queue: {theirs.name} -> {len(merged)} item(s), "
          f"{applied} mark(s) re-applied, {unposted} unposted")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    ours, theirs = Path(args[0]), Path(args[1])
    if not ours.exists():
        print(f"merge_queue: {ours} missing - nothing to re-apply")
        return 0
    if "--lines" in sys.argv:
        merge_lines(ours, theirs)
    else:
        merge_queue(ours, theirs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
