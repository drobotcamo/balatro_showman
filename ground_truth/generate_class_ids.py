"""Regenerate the Lua class-ID table embedded in the bridge producer.

The vendored class-ID map (D003) is the versioned base ontology:
`legacy/vendor/balatro-policy-transformer/data/class_map.csv`. The Lua producer
runs inside the game and cannot read repository files, so the subset of the map
that maps a game `center_key` to a canonical `class_id` is embedded in
`ground_truth/balatro_mod/main.lua` between explicit BEGIN/END markers.

This tool keeps that embedded copy mechanically tied to the vendored CSV:
regenerate after extending the class map (IDs are extended, never renumbered).

Usage (from the repository root):

    py -3 ground_truth\\generate_class_ids.py            # rewrite main.lua
    py -3 ground_truth\\generate_class_ids.py --check    # verify only (exit 1 if stale)

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLASS_MAP_CSV = (
    REPO_ROOT
    / "legacy"
    / "vendor"
    / "balatro-policy-transformer"
    / "data"
    / "class_map.csv"
)
MAIN_LUA = REPO_ROOT / "ground_truth" / "balatro_mod" / "main.lua"

BEGIN_MARKER = "-- BEGIN GENERATED CLASS ID TABLE"
END_MARKER = "-- END GENERATED CLASS ID TABLE"

# class_id 0..51 are the standard 52 playing cards. Their class_id is computed
# from suit/rank in the producer, not looked up by `center_key`, so they are not
# part of the key->id table.
STANDARD_CARD_MAX = 51


def load_class_map(path: Path = CLASS_MAP_CSV) -> list[tuple[int, str]]:
    """Return (class_id, class_name) pairs from the vendored class map."""
    entries: list[tuple[int, str]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if index == 0 and line.strip().lower() == "class_id,class_name":
            continue
        line = line.strip()
        if not line:
            continue
        class_id_text, _, class_name = line.partition(",")
        entries.append((int(class_id_text), class_name))
    return entries


def render_table(entries: list[tuple[int, str]]) -> list[str]:
    """Render Lua table body lines for the non-card class names."""
    rows = [(cid, name) for cid, name in entries if cid > STANDARD_CARD_MAX]
    rows.sort(key=lambda row: row[0])
    return [f"  {name} = {cid}," for cid, name in rows]


def render_block(entries: list[tuple[int, str]]) -> str:
    body = "\n".join(render_table(entries))
    return (
        f"{BEGIN_MARKER}\n"
        "local CLASS_ID_BY_CENTER_KEY = {\n"
        f"{body}\n"
        "}\n"
        f"{END_MARKER}"
    )


def replace_block(text: str, block: str) -> str:
    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER) + len(END_MARKER)
    return text[:start] + block + text[end:]


def main(argv: list[str]) -> int:
    check_only = "--check" in argv[1:]
    text = MAIN_LUA.read_text(encoding="utf-8")
    block = render_block(load_class_map())
    updated = replace_block(text, block)
    if check_only:
        if updated == text:
            print("class ID table is up to date")
            return 0
        print("class ID table is stale; run ground_truth/generate_class_ids.py")
        return 1
    MAIN_LUA.write_text(updated, encoding="utf-8", newline="")
    print(f"wrote {len(render_table(load_class_map()))} class IDs into {MAIN_LUA.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
