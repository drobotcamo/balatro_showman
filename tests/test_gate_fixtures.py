"""Executable fixture classification model, NOT an agent or gate implementation.

The model makes the tabletop refusal examples checkable. No live protocol,
threshold, human approval or deterministic agent behavior is established here.
"""
import json
from pathlib import Path
import unittest

FIXTURES = Path(__file__).parents[1] / ".opencode/skill/gate-facilitator/fixtures/cases.json"


def classify(data, case):
    protocol = data["protocols"].get(case["protocol"])
    target = dict(data["request"], revision=case.get("revision", data["request"]["revision"]))
    if (not protocol or not protocol["approved"] or not protocol["required"]
            or any(protocol[key] != target[key] for key in ("slice", "revision"))
            or set(case["rows"]) != set(protocol["required"]) or case.get("request")):
        return "blocked"
    if case.get("evidence_issue"):
        return "unknown"
    rows = set(case["rows"].values())
    for status in ("blocked", "unknown", "sendback"):
        if status in rows:
            return status
    if rows != {"pass"}:
        return "unknown"
    return "pass" if case["human_acceptance"] else "decision_pending"


class GateFixtureModelTests(unittest.TestCase):
    def test_named_protocol_classification_examples(self):
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "2.0.0")
        names = [case["name"] for case in data["cases"]]
        self.assertEqual(len(names), len(set(names)))
        for case in data["cases"]:
            with self.subTest(case=case["name"]):
                self.assertIsInstance(case["rows"], dict)
                self.assertTrue(set(case["rows"].values()) <= {"pass", "sendback", "blocked", "unknown"})
                self.assertEqual(classify(data, case), case["expected"])
