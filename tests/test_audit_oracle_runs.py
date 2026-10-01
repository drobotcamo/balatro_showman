import json
import tempfile
import unittest
from pathlib import Path

from planning.audit_oracle_runs import STATE_KEYS, audit, conformance_findings


def _state() -> dict:
    return {key: 0 for key in STATE_KEYS}


def _joker(class_id, center_key, edition=None, stickers=None):
    return {
        "class_id": class_id,
        "object_type": "joker",
        "zone": "CurrentJokers",
        "position_in_zone": 0,
        "modifier": None,
        "edition": edition,
        "seal": None,
        "stickers": stickers if stickers is not None else [],
        "card": None,
        "center_key": center_key,
    }


def _playing_card(class_id, modifier=None, edition=None, seal=None, stickers=None):
    return {
        "class_id": class_id,
        "object_type": "card",
        "zone": "CurrentHand",
        "position_in_zone": 0,
        "modifier": modifier,
        "edition": edition,
        "seal": seal,
        "stickers": stickers if stickers is not None else [],
        "card": {
            "rank": "A",
            "rank_index": 0,
            "suit": "Spades",
            "suit_index": 0,
            "is_ace": True,
            "is_face": False,
        },
    }


def _record(objects, pending) -> dict:
    return {
        "schema_version": "live/2.0.0",
        "request_id": 1,
        "page_name": "In_Blind",
        "state": _state(),
        "objects": objects,
        "pending_cards": pending,
        "persistent_state": {},
        "action_taken": "PlayHand",
        "meta": {"run_id": "audit-test"},
    }


def _write_run(directory: Path, objects, pending) -> Path:
    run_dir = directory / "audit-test"
    run_dir.mkdir()
    (run_dir / "session.json").write_text(
        json.dumps(
            {
                "run_id": "audit-test",
                "schema_version": "record/1.0.0",
                "n_steps": 1,
                "outcome": "win",
            }
        ),
        encoding="utf-8",
    )
    step = _record(objects, pending)
    (run_dir / "steps.ndjson").write_text(
        json.dumps(step) + "\n", encoding="utf-8"
    )
    return run_dir


class AuditConformanceTests(unittest.TestCase):
    def test_populated_run_has_no_attribute_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[
                    _joker(151, "j_joker", edition="e_foil", stickers=["eternal"]),
                    _playing_card(0, modifier="m_bonus", seal="red_seal"),
                ],
                pending=[
                    _playing_card(13, modifier="m_glass", edition="e_holo", seal="blue_seal")
                ],
            )
            summary = audit(run_dir)
        self.assertEqual(summary["inventory_objects"], 1)
        self.assertEqual(summary["inventory_class_id_null"], 0)
        self.assertEqual(summary["object_attribute_all_null"], [])
        self.assertEqual(summary["pending_attribute_all_null"], [])
        self.assertEqual(summary["object_stickers_not_list"], 0)
        self.assertEqual(conformance_findings(summary), [])

    def test_unmapped_inventory_key_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[_joker(None, "j_modded_unknown")],
                pending=[],
            )
            summary = audit(run_dir)
        self.assertEqual(summary["inventory_class_id_null"], 1)
        self.assertEqual(summary["inventory_center_key_only"], 1)
        findings = conformance_findings(summary)
        self.assertTrue(any("class_id:null" in finding for finding in findings))

    def test_all_null_attribute_column_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[_joker(151, "j_joker")],
                pending=[],
            )
            summary = audit(run_dir)
        self.assertEqual(
            summary["object_attribute_all_null"], ["modifier", "edition", "seal", "stickers"]
        )
        findings = conformance_findings(summary)
        self.assertEqual(len(findings), 4)


if __name__ == "__main__":
    unittest.main()
