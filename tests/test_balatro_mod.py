import json
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parent.parent / "ground_truth" / "balatro_mod"
REQUIRED_JSON_FIELDS = ("id", "author", "name", "description", "prefix", "main_file")


class BalatroModManifestTests(unittest.TestCase):
    def test_manifest_has_steamodded_required_fields(self) -> None:
        manifest = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
        for field in REQUIRED_JSON_FIELDS:
            self.assertIn(field, manifest, field)
        self.assertIsInstance(manifest["author"], list)
        self.assertNotIn("$", manifest["prefix"])
        self.assertTrue((MOD_DIR / manifest["main_file"]).is_file())

    def test_mod_dir_has_exactly_one_json_metadata_file(self) -> None:
        # Steamodded treats every *.json under a mod as metadata and logs an
        # error for each invalid one, so the mod must ship exactly one.
        json_files = sorted(path.name for path in MOD_DIR.glob("*.json"))
        self.assertEqual(json_files, ["manifest.json"])


if __name__ == "__main__":
    unittest.main()
