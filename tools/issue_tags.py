"""Allocate and validate four-letter issue tags."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "planning" / "issue-tags.json"
LOCK = REGISTRY.with_suffix(".lock")
POOL = ("BIRD", "GAIT", "YOYO", "LAMP", "MINT", "NOVA", "WAVE", "ZEST")


def load() -> dict[str, int]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry must be a JSON object")
    result: dict[str, int] = {}
    for tag, issue in data.items():
        if not isinstance(tag, str) or len(tag) != 4 or not tag.isascii() or not tag.isalpha() or tag != tag.upper():
            raise ValueError(f"invalid tag: {tag!r}")
        if not isinstance(issue, int) or issue < 1:
            raise ValueError(f"invalid issue number for {tag}: {issue!r}")
        result[tag] = issue
    if len(result) != len(set(result.values())):
        raise ValueError("an issue number appears more than once")
    return result


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    if command == "register":
        if len(argv) != 3 or not argv[2].isdigit() or int(argv[2]) < 1:
            raise SystemExit(f"usage: {argv[0]} register <issue-number>")
        issue = int(argv[2])
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise SystemExit("another allocation is in progress; retry")
        try:
            registry = load()
            if issue in registry.values():
                raise SystemExit("issue already has a tag")
            for tag in POOL:
                if tag not in registry:
                    registry[tag] = issue
                    payload = json.dumps(registry, indent=2) + "\n"
                    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=REGISTRY.parent, delete=False) as tmp:
                        tmp.write(payload)
                        replacement = Path(tmp.name)
                    os.replace(replacement, REGISTRY)
                    print(tag)
                    return 0
            raise SystemExit("tag pool exhausted; extend POOL deliberately")
        finally:
            os.close(fd)
            LOCK.unlink(missing_ok=True)
    registry = load()
    if command == "allocate":
        for tag in POOL:
            if tag not in registry:
                raise SystemExit("use register <issue-number> to atomically allocate a tag")
        raise SystemExit("tag pool exhausted; extend POOL deliberately")
    if command == "check":
        print(f"valid: {len(registry)} issue tag(s)")
        return 0
    raise SystemExit(f"usage: {argv[0]} [register <issue-number>|check]")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
