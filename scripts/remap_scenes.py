# -*- coding: utf-8 -*-
"""Make the reel2 batch playable with whatever scene art exists so far.

Each reel2 item lists the scene ids it was written for. Until every one of those
scenes has its image in assets/ss_art, the item cannot render. This remaps each
missing scene to the closest AVAILABLE scene by emotion-tag overlap (never repeating
a scene inside one reel, and spreading usage), and keeps the originally intended ids in
"scenes_target" so a later run can restore them once the art exists.

Usage: python scripts/remap_scenes.py <batch.json> [--write]
Without --write it only reports.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ART = Path(__file__).resolve().parent.parent / "assets" / "ss_art"


def main() -> int:
    batch_path = Path(sys.argv[1])
    write = "--write" in sys.argv
    meta = json.loads((ART / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    tags = {s["id"]: set(s["tags"]) for s in meta}
    have = {s["id"] for s in meta if (ART / s["file"]).exists()}
    batch = json.loads(batch_path.read_text(encoding="utf-8"))

    usage: Counter = Counter()
    changed = playable = 0
    for item in batch:
        target = item.get("scenes_target") or item["scenes"]
        used: list[int] = []
        for sid in target:
            if sid in have and sid not in used:
                pick = sid
            else:
                options = [c for c in have if c not in used]
                if not options:
                    pick = sid
                else:
                    pick = max(options, key=lambda c: (len(tags[c] & tags[sid]) - 0.15 * usage[c], -usage[c]))
            used.append(pick)
            usage[pick] += 1
        if used != item["scenes"]:
            changed += 1
        item["scenes_target"] = target
        item["scenes"] = used
        if all(s in have for s in used):
            playable += 1

    print(f"scenes available: {len(have)} -> playable reels: {playable}/{len(batch)}; "
          f"remapped {changed}; usage range {min(usage.values())}-{max(usage.values())}")
    if write:
        batch_path.write_text(json.dumps(batch, indent=1, ensure_ascii=False), encoding="utf-8")
        print("written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
