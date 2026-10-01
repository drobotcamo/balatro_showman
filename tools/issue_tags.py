"""Allocate and validate four-letter issue tags."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "planning" / "issue-tags.json"
POOL = ("BIRD", "GAIT", "YOYO", "LAMP", "MINT", "NOVA", "WAVE", "ZEST")


def load() -> dict[str, int]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry must be a JSON object")
    result: dict[str, int] = {}
    for tag, issue in data.items():
        if not isinstance(tag, str) or len(tag) != 4 or not tag.isalpha() or tag != tag.upper():
            raise ValueError(f"invalid tag: {tag!r}")
        if not isinstance(issue, int) or issue < 1:
            raise ValueError(f"invalid issue number for {tag}: {issue!r}")
        result[tag] = issue
    if len(result) != len(set(result.values())):
        raise ValueError("an issue number appears more than once")
    return result


def main(argv: list[str]) -> int:
    registry = load()
    command = argv[1] if len(argv) > 1 else "check"
    if command == "allocate":
        for tag in POOL:
            if tag not in registry:
                print(tag)
                return 0
        raise SystemExit("tag pool exhausted; extend POOL deliberately")
    if command == "check":
        print(f"valid: {len(registry)} issue tag(s)")
        return 0
    raise SystemExit(f"usage: {argv[0]} [allocate|check]")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
