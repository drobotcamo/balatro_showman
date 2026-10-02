"""Build a deterministic, read-only inventory of legacy candidate artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOTS = ("legacy/vendor/balatro-cv-pipeline", "legacy/vendor/balatro-policy-transformer", "legacy/label_store.py", "legacy/tools")
VERSION = "1.0.0"


def _artifact(path: Path, base: Path) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.relative_to(base).as_posix(),
        "identity": {"kind": "file", "size_bytes": path.stat().st_size},
        "source": {"repository": None, "url": None, "evidence": None},
        "revision": None,
        "license": {"spdx": None, "redistribution": "unknown", "evidence": None},
        "checksum": {"algorithm": "sha256", "value": digest},
        "compatibility": {"game_version": None, "runtime": None, "assessment": "unknown", "notes": None},
        "eligibility": "research-reference-only",
        "status": "not-ready",
    }


def build_manifest(base: Path) -> dict:
    artifacts = []
    for raw_root in ROOTS:
        root = base / raw_root
        if root.is_file():
            artifacts.append(_artifact(root, base))
        elif root.is_dir():
            for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
                artifacts.append(_artifact(path, base))
        else:
            artifacts.append({
                "path": raw_root, "identity": None,
                "source": {"repository": None, "url": None, "evidence": None},
                "revision": None, "license": {"spdx": None, "redistribution": "unknown", "evidence": None},
                "checksum": None, "compatibility": {"game_version": None, "runtime": None, "assessment": "unknown", "notes": "not present"},
                "eligibility": "research-reference-only", "status": "unavailable",
            })
    artifacts.sort(key=lambda item: item["path"])
    return {"manifest_version": VERSION, "generated_by": "planning/provenance_inventory.py", "artifacts": artifacts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    document = json.dumps(build_manifest(args.root.resolve()), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(document, encoding="utf-8", newline="\n")
    else:
        print(document, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
