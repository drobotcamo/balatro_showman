from run_bundle import RunBundleInspector
from run_bundle import InspectionError

from test_run_bundle import bundle


def test_inspection_is_enveloped_and_preserves_raw_bytes(tmp_path):
    b = bundle(tmp_path)
    b.append("r1", 0, "state", {"chips": 1})
    b.append_raw("r1", 1, "partial", b"\xff")
    inspector = RunBundleInspector(f"sqlite:///{tmp_path / 'run.db'}")

    assert inspector.summary("r1")["status"] == "observed"
    assert inspector.get_record("r1", 0)["data"]["payload"] == {"chips": 1}
    raw = inspector.get_record("r1", 1)["data"]
    assert raw["encoding"] == "base64"
    assert inspector.validate("r1")["data"]["status"] == "invalid"



def test_unsupported_transition_and_machine_readable_missing_run(tmp_path):
    b = bundle(tmp_path)
    inspector = RunBundleInspector(f"sqlite:///{tmp_path / 'run.db'}")
    assert inspector.transitions("r1")["status"] == "unsupported"
    try:
        inspector.summary("missing")
    except Exception as exc:
        assert exc.code == "run_not_found"
    else:
        raise AssertionError("missing run did not fail")


def test_missing_unsupported_operation_is_still_a_query_error(tmp_path):
    bundle(tmp_path)
    inspector = RunBundleInspector(f"sqlite:///{tmp_path / 'run.db'}")
    for call in (lambda: inspector.transitions("missing"), lambda: inspector.diff("missing", 0, 1)):
        try:
            call()
        except Exception as exc:
            assert exc.code == "run_not_found"
        else:
            raise AssertionError("missing run did not fail")


def test_strict_validation_reports_integrity_failure(tmp_path):
    b = bundle(tmp_path)
    b.append_raw("r1", 0, "partial", b"bad")
    inspector = RunBundleInspector(f"sqlite:///{tmp_path / 'run.db'}")

    try:
        inspector.validate("r1", strict=True)
    except InspectionError as exc:
        assert exc.code == "integrity_failure"
    else:
        raise AssertionError("strict validation did not fail")


def test_evidence_applies_the_same_range_filters_as_find(tmp_path):
    b = bundle(tmp_path)
    b.append("r1", 0, "state", {"n": 0})
    b.append("r1", 1, "event", {"n": 1})
    inspector = RunBundleInspector(f"sqlite:///{tmp_path / 'run.db'}")

    result = inspector.evidence("r1", sequence_from=1, sequence_to=1)
    assert [record["sequence"] for record in result["data"]] == [1]


def test_inspector_does_not_create_a_missing_sqlite_database(tmp_path):
    path = tmp_path / "missing.db"
    try:
        RunBundleInspector(f"sqlite:///{path}")
    except InspectionError as exc:
        assert exc.code == "storage_not_found"
    else:
        raise AssertionError("missing database was accepted")
    assert not path.exists()
