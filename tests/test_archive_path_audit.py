from pathlib import Path

from planning.audit_archive_paths import find_references, inspect_path


def test_reference_parser_handles_spaces_and_unquoted_templates():
    text = '''`F:\\OBS_RECORDINGS\\showman-archive\\catalog.sqlite`
"F:/OBS_RECORDINGS/2026-10-03 17-25-24.mkv"
F:\\OBS_RECORDINGS\\oracle_runs\\<run_id>
F:\\OBS_RECORDINGS\\oracle_runs*\n'''
    found = find_references(text)
    assert found[0][1] == r"F:\OBS_RECORDINGS\showman-archive\catalog.sqlite"
    assert found[1][1] == "F:/OBS_RECORDINGS/2026-10-03 17-25-24.mkv"
    assert found[2][1] == r"F:\OBS_RECORDINGS\oracle_runs\<run_id>"
    assert found[3][1] == r"F:\OBS_RECORDINGS\oracle_runs*"


def test_path_check_distinguishes_placeholder_and_existing_path(tmp_path):
    actual = tmp_path / "source file.mkv"
    actual.write_bytes(b"media")
    assert inspect_path("F:\\OBS_RECORDINGS\\oracle_runs\\<run>")["result"] == "placeholder"
    assert inspect_path(str(actual))["result"] == "exists_file"
    assert inspect_path(str(tmp_path / "missing.mkv"))["result"] == "missing"
