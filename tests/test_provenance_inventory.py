import hashlib
import json
from pathlib import Path

from planning.provenance_inventory import build_manifest


def test_inventory_is_deterministic_and_hashes_bytes(tmp_path):
    root = tmp_path / "repo"
    candidate = root / "legacy" / "tools"
    candidate.mkdir(parents=True)
    file = candidate / "sample.bin"
    file.write_bytes(b"stable bytes")

    first = build_manifest(root)
    second = build_manifest(root)
    assert first == second
    entry = next(item for item in first["artifacts"] if item["path"] == "legacy/tools/sample.bin")
    assert entry["checksum"] == {"algorithm": "sha256", "value": hashlib.sha256(b"stable bytes").hexdigest()}
    assert entry["status"] == "not-ready"


def test_missing_candidate_is_explicitly_unavailable(tmp_path):
    manifest = build_manifest(tmp_path)
    entry = next(item for item in manifest["artifacts"] if item["path"] == "legacy/label_store.py")
    assert entry["status"] == "unavailable"
    assert entry["checksum"] is None


def test_checked_in_schema_and_report_are_json():
    schema = json.loads(Path("planning/provenance_manifest.schema.json").read_text())
    assert schema["$defs"]["artifact"]["properties"]["status"]["enum"] == ["verified", "unknown", "unavailable", "incompatible", "not-ready"]
