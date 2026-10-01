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

    def test_producer_emits_canonical_offering_zones(self) -> None:
        # Issue #16: the live/2.0 zone vocabulary uses the four split offering
        # zones; bare `ShopOfferings` is a deprecated alias and must not be
        # emitted.
        text = (MOD_DIR / "main.lua").read_text(encoding="utf-8")
        for zone in (
            "TopShelfShopOfferings",
            "VoucherShopOfferings",
            "PackShopOfferings",
            "PackOfferings",
        ):
            self.assertIn(f'"{zone}"', text, zone)
        self.assertNotIn('"ShopOfferings"', text)

    def test_producer_reads_the_expected_shop_cardareas(self) -> None:
        text = (MOD_DIR / "main.lua").read_text(encoding="utf-8")
        for area in ("G.shop_jokers", "G.shop_vouchers", "G.shop_booster", "G.pack_cards"):
            self.assertIn(area, text, area)

    def test_producer_declares_direct_action_subtypes(self) -> None:
        text = (MOD_DIR / "main.lua").read_text(encoding="utf-8")
        for subtype in ("selljoker", "sellconsumable", "buytopshelfconsumable"):
            self.assertIn(subtype, text, subtype)
        self.assertIn('"BuyAndUseShopConsumable"', text)


if __name__ == "__main__":
    unittest.main()
