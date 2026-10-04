import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ground_truth.file_ipc_bridge import FileIpcBridge

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

    def test_producer_declares_queued_request_and_terminal_watermark_protocol(self) -> None:
        text = (MOD_DIR / "main.lua").read_text(encoding="utf-8")
        self.assertIn('"ipc_schema_version":"file-queue/1.0.0"', text)
        self.assertIn('"last_request_id":', text)
        self.assertIn('"producer_write_failures":', text)
        self.assertIn("request_", text)

    @unittest.skipUnless(os.name == "nt" and shutil.which("lovec"), "Windows LÖVE runtime required")
    def test_producer_lifecycle_in_love(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            io_dir = Path(directory) / "Balatro" / "agent_io"
            io_dir.mkdir(parents=True)
            result = subprocess.run(
                ["lovec", "tests/lua_file_ipc_fixture"],
                cwd=MOD_DIR.parent.parent, env={**os.environ, "APPDATA": directory},
                text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Continue 109->110->111", result.stdout)
            requests = [json.loads(path.read_text()) for path in io_dir.glob("request_*.json")]
            resumed = next(item["meta"]["run_id"] for item in requests if item["request_id"] == 111)
            consumer_io = Path(directory) / "consumer_io"
            consumer_io.mkdir()
            for path in io_dir.glob("*.json"):
                payload = json.loads(path.read_text())
                if payload.get("meta", {}).get("run_id", payload.get("run_id")) == resumed:
                    shutil.copyfile(path, consumer_io / path.name)
            (consumer_io / "recording_start_marker.json").write_text(json.dumps({
                "schema_version": "producer/1.0.0", "recording_id": "resume-fixture",
                "fps": 60, "capture_timestamp_ns": 123,
            }))
            output = Path(directory) / "runs"
            consumer = FileIpcBridge(consumer_io, output)
            for _ in range(115):
                if not consumer.step_once():
                    break
            self.assertEqual([path.name for path in output.iterdir()], [resumed])
            session = json.loads((output / resumed / "session.json").read_text())
            self.assertEqual(session["n_steps"], 111)
            self.assertEqual(session["outcome"], "win")
            self.assertEqual(session["recording"]["recording_id"], "resume-fixture")
            steps = [json.loads(line) for line in (output / resumed / "steps.ndjson").read_text().splitlines()]
            self.assertEqual([step["request_id"] for step in steps], list(range(1, 112)))


if __name__ == "__main__":
    unittest.main()
