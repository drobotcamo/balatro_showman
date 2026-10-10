r"""Test every tracked literal F:\OBS_RECORDINGS path against the live archive."""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


QUOTED = re.compile(r"(?P<q>[`\"'])(?P<value>F:[\\/]OBS_RECORDINGS[^`\"'\r\n]*?)(?P=q)", re.IGNORECASE)
UNQUOTED = re.compile(r"(?<![A-Za-z0-9_])F:[\\/]OBS_RECORDINGS(?:[\\/][^\s`\"',;)]+)*", re.IGNORECASE)
TRAILING = ".,;:!?)\"]`'"


def tracked_files(repository: Path) -> list[Path]:
    output = subprocess.check_output(["git", "-C", str(repository), "ls-files", "-z"])
    return [repository / Path(value.decode("utf-8", errors="surrogateescape"))
            for value in output.split(b"\0") if value]


def find_references(text: str) -> list[tuple[int, str]]:
    """Find quoted (spaces allowed) and unquoted literal F-drive path tokens."""
    refs: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        # JSON and Python literals commonly store Windows separators doubled.
        line = line.replace("\\\\", "\\")
        spans = []
        for match in QUOTED.finditer(line):
            refs.append((line_number, match.group("value").rstrip(TRAILING)))
            spans.append(match.span())
        if spans:
            chars = list(line)
            for start, end in spans:
                chars[start:end] = " " * (end - start)
            line = "".join(chars)
        for match in UNQUOTED.finditer(line):
            refs.append((line_number, match.group(0).rstrip(TRAILING)))
    return refs


def inspect_path(raw: str) -> dict:
    value = raw.replace("/", "\\").rstrip(".")
    if any(token in value for token in ("<", ">", "$env:", "%")):
        return {"path": raw, "result": "placeholder"}
    if "*" in value or "?" in value:
        matches = glob.glob(value)
        return {"path": raw, "result": "wildcard_resolved" if matches else "wildcard_unmatched",
                "matches": len(matches)}
    path = Path(value)
    try:
        exists = path.exists()
        if exists:
            resolved = path.resolve(strict=True)
            return {"path": raw, "result": "exists_directory" if path.is_dir() else "exists_file",
                    "resolved": str(resolved)}
        return {"path": raw, "result": "missing"}
    except (OSError, RuntimeError) as error:
        return {"path": raw, "result": "error", "error": str(error)}


def audit(repository: Path, recordings_root: Path) -> dict:
    references = []
    text_files = 0
    nontext_files = 0
    files = tracked_files(repository)
    for path in files:
        try:
            raw = path.read_bytes()
        except OSError:
            nontext_files += 1
            continue
        try:
            text = raw.decode("utf-8")
            text_files += 1
        except UnicodeError:
            # F-drive paths are ASCII. Scan binary files too so embedded path
            # literals cannot evade the audit merely because decoding fails.
            nontext_files += 1
            text = raw.decode("utf-8", errors="ignore")
        relative = path.relative_to(repository).as_posix()
        for line, value in find_references(text):
            item = {"file": relative, "line": line}
            item.update({"path": value, "result": "test_fixture"} if relative.startswith("tests/")
                        else inspect_path(value))
            references.append(item)
    totals = Counter(item["result"] for item in references)
    errors = [item for item in references if item["result"] in {"missing", "error"}]
    return {"repository": str(repository), "recordings_root": str(recordings_root),
            "tracked_files": len(files), "text_files_scanned": text_files,
            "nontext_files_scanned": nontext_files,
            "references": len(references), "unique_literals": len({item["path"] for item in references}),
            "results": dict(sorted(totals.items())), "failures": errors, "details": references}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--recordings-root", type=Path, required=True)
    args = parser.parse_args(argv)
    repository = args.repository.resolve()
    result = audit(repository, args.recordings_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
