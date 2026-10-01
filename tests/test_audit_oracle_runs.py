import json
import tempfile
import unittest
from pathlib import Path

from planning.audit_oracle_runs import (
    MASK_BASIS_FIELDS,
    RAW_LEAF_FIELDS,
    OFFERING_ZONES,
    STATE_KEYS,
    audit,
    conformance_findings,
)


def _state() -> dict:
    return {key: 0 for key in STATE_KEYS}


def _mask_basis() -> dict:
    return {
        "reroll_cost": 5,
        "free_rerolls": 0,
        "selected_hand_count": 2,
        "selected_consumable_count": 0,
        "selected_sellable_count": 0,
    }


def _raw_persistent() -> dict:
    return {
        "deck": {"center_key": "b_red", "class_id": 65},
        "stake": {"level": 2, "center_key": "stake_red"},
        "starting_params_no_faces": False,
        "modifiers": {"no_interest": False},
        "tracked_deck_cards": [_playing_card(0)],
        "hand_levels": {"High Card": {"level": 1, "played": 0, "played_this_round": 0}},
        "vouchers_redeemed": ["v_reroll_surplus"],
        "bosses_used": {"bl_arm": 0},
        "blind_states": {"Small": "Select", "Big": "Upcoming", "Boss": "Upcoming"},
        "blind_choices": {"Small": "bl_small", "Big": "bl_big", "Boss": "bl_arm"},
        "blind_tags": {"Small": "tag_double"},
        "boss_rerolled": False,
        "skips": 1,
        "hands_played": 3,
        "unused_discards": 2,
        "ecto_minus": 1,
        "last_tarot_planet": None,
    }


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


def _offering(zone, position=0, object_type="joker"):
    return {
        "class_id": 151,
        "object_type": object_type,
        "zone": zone,
        "position_in_zone": position,
        "modifier": None,
        "edition": None,
        "seal": None,
        "stickers": [],
        "card": None,
        "center_key": "j_joker",
    }


def _record(objects, pending, schema_version="producer/1.0.0", extra=None) -> dict:
    record = {
        "schema_version": schema_version,
        "step_id": "audit-test:1",
        "capture_timestamp_ns": 1_000_000_000,
        "request_id": 1,
        "page_name": "In_Blind",
        "state": _state(),
        "objects": objects,
        "pending_cards": pending,
        "persistent_state": {},
        "action_taken": "PlayHand",
        "meta": {
            "run_id": "audit-test",
            "capture_timestamp_ns": 1_000_000_000,
            "video_timestamp_ns": 1_000_000_000,
        },
    }
    if schema_version in {"live/3.0.0"}:
        record["raw_persistent"] = _raw_persistent()
        record["legal_actions"] = ["PlayHand", "DiscardHand"]
        record["mask_basis"] = _mask_basis()
    if extra:
        record.update(extra)
    return record


def _write_run(
    directory: Path, objects, pending, schema_version="live/2.0.0", extra=None, omit=()
) -> Path:
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
    step = _record(objects, pending, schema_version=schema_version, extra=extra)
    for key in omit:
        step.pop(key, None)
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
        self.assertEqual(
            conformance_findings(summary),
            [
                "audit-test: no raw persistent fields (schema {'live/2.0.0': 1} "
                "predates ['live/3.0.0'])",
                "audit-test: legal_actions missing/empty on 1/1 steps",
                "audit-test: mask_basis missing on 1/1 steps",
                "audit-test: action_taken not in legal_actions on 1/1 steps "
                "(client would reject these snapshots)",
            ],
        )

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

    def test_offering_zone_coverage_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[
                    _offering("TopShelfShopOfferings", 0),
                    _offering("TopShelfShopOfferings", 1, "planet"),
                    _offering("VoucherShopOfferings", 0, "voucher"),
                    _offering("PackShopOfferings", 0, "pack"),
                    _offering("PackOfferings", 0),
                ],
                pending=[],
            )
            summary = audit(run_dir)
        self.assertEqual(summary["offering_objects_total"], 5)
        self.assertEqual(
            summary["offering_zone_counts"],
            {
                "TopShelfShopOfferings": 2,
                "VoucherShopOfferings": 1,
                "PackShopOfferings": 1,
                "PackOfferings": 1,
            },
        )
        self.assertEqual(
            summary["offering_zones_present"], list(OFFERING_ZONES)
        )
        self.assertEqual(summary["offering_zones_missing"], [])
        self.assertEqual(summary["offering_position_missing"], 0)
        self.assertFalse(
            any("position_in_zone" in finding for finding in conformance_findings(summary))
        )

    def test_missing_offering_zone_is_reported_in_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[_offering("PackOfferings", 0)],
                pending=[],
            )
            summary = audit(run_dir)
        self.assertEqual(summary["offering_objects_total"], 1)
        self.assertIn("PackOfferings", summary["offering_zones_present"])
        self.assertIn("VoucherShopOfferings", summary["offering_zones_missing"])

    def test_offering_without_position_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[_offering("PackOfferings", None)],
                pending=[],
            )
            summary = audit(run_dir)
        self.assertEqual(summary["offering_position_missing"], 1)
        findings = conformance_findings(summary)
        self.assertTrue(any("position_in_zone" in finding for finding in findings))

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
        self.assertEqual(
            findings,
            [
                "audit-test: object.modifier is null/empty on all 1 objects",
                "audit-test: object.edition is null/empty on all 1 objects",
                "audit-test: object.seal is null/empty on all 1 objects",
                "audit-test: object.stickers is null/empty on all 1 objects",
                "audit-test: no raw persistent fields (schema {'live/2.0.0': 1} "
                "predates ['live/3.0.0'])",
                "audit-test: legal_actions missing/empty on 1/1 steps",
                "audit-test: mask_basis missing on 1/1 steps",
                "audit-test: action_taken not in legal_actions on 1/1 steps "
                "(client would reject these snapshots)",
            ],
        )


class RawFieldAndLegalityTests(unittest.TestCase):
    def test_live3_run_reports_full_coverage_and_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[
                    _joker(151, "j_joker", edition="e_foil", stickers=["eternal"]),
                    _playing_card(0, modifier="m_bonus", seal="red_seal"),
                ],
                pending=[],
                schema_version="live/3.0.0",
            )
            summary = audit(run_dir)
        self.assertTrue(summary["raw_field_schema"])
        self.assertEqual(summary["raw_deck_center_key_present"], 1)
        self.assertEqual(summary["raw_deck_class_id_present"], 1)
        self.assertEqual(summary["raw_stake_level_present"], 1)
        self.assertEqual(summary["raw_stake_center_key_present"], 1)
        self.assertEqual(summary["raw_skips_present"], 1)
        self.assertEqual(summary["raw_tracked_deck_cards_total"], 1)
        self.assertEqual(summary["mask_basis_present"], 1)
        for field in MASK_BASIS_FIELDS:
            self.assertEqual(summary[f"mask_basis_{field}_present"], 1)
        self.assertEqual(summary["legal_actions_nonempty"], 1)
        self.assertEqual(summary["action_in_legal_actions"], 1)
        self.assertEqual(summary["legal_action_labels"], ["DiscardHand", "PlayHand"])
        self.assertEqual(conformance_findings(summary), [])

    def test_live3_run_missing_raw_fields_fails_integrity(self) -> None:
        import planning.audit_oracle_runs as module

        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[],
                pending=[],
                schema_version="live/3.0.0",
                omit=("raw_persistent", "legal_actions", "mask_basis"),
            )
            before = len(module.INTEGRITY_FAILURES)
            summary = audit(run_dir)
            new_failures = module.INTEGRITY_FAILURES[before:]
        self.assertEqual(summary["raw_field_schema"], True)
        self.assertTrue(any("raw_persistent" in failure for failure in new_failures))
        self.assertTrue(any("legal_actions" in failure for failure in new_failures))
        self.assertTrue(any("mask_basis" in failure for failure in new_failures))

    def test_legacy_run_reports_raw_field_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(Path(directory), objects=[_joker(151, "j_joker")], pending=[])
            summary = audit(run_dir)
        self.assertFalse(summary["raw_field_schema"])
        findings = conformance_findings(summary)
        self.assertTrue(any("no raw persistent fields" in finding for finding in findings))

    def test_action_not_in_legal_actions_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[],
                pending=[],
                schema_version="live/3.0.0",
                extra={"legal_actions": ["PlayHand"], "action_taken": "RerollShop"},
            )
            summary = audit(run_dir)
        findings = conformance_findings(summary)
        self.assertTrue(any("action_taken not in legal_actions" in finding for finding in findings))
        self.assertEqual(summary["action_in_legal_actions"], 0)

    def test_null_raw_counter_is_reported(self) -> None:
        raw = _raw_persistent()
        raw["skips"] = None
        raw["stake"] = {"level": None, "center_key": "stake_red"}
        with tempfile.TemporaryDirectory() as directory:
            run_dir = _write_run(
                Path(directory),
                objects=[],
                pending=[],
                schema_version="live/3.0.0",
                extra={"raw_persistent": raw},
            )
            summary = audit(run_dir)
        self.assertEqual(summary["raw_skips_present"], 0)
        self.assertEqual(summary["raw_stake_level_present"], 0)
        findings = conformance_findings(summary)
        self.assertTrue(any("raw_persistent.skips" in finding for finding in findings))
        self.assertTrue(any("raw_persistent.stake.level" in finding for finding in findings))
        self.assertFalse(any("raw_persistent.hands_played" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
