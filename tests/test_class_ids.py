import re
import unittest


from ground_truth.generate_class_ids import (
    BEGIN_MARKER,
    END_MARKER,
    MAIN_LUA,
    STANDARD_CARD_MAX,
    load_class_map,
)

TABLE_ENTRY = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*(\d+),?\s*$")


def parse_embedded_class_ids() -> dict[str, int]:
    text = MAIN_LUA.read_text(encoding="utf-8")
    body = text[text.index(BEGIN_MARKER) : text.index(END_MARKER)]
    entries: dict[str, int] = {}
    for line in body.splitlines():
        match = TABLE_ENTRY.match(line)
        if match:
            entries[match.group(1)] = int(match.group(2))
    return entries


class EmbeddedClassIdTests(unittest.TestCase):
    def test_embedded_table_matches_vendored_class_map(self) -> None:
        expected = {
            name: class_id
            for class_id, name in load_class_map()
            if class_id > STANDARD_CARD_MAX
        }
        self.assertEqual(parse_embedded_class_ids(), expected)

    def test_class_ids_are_unique(self) -> None:
        ids = list(parse_embedded_class_ids().values())
        self.assertEqual(len(ids), len(set(ids)))

    def test_standard_cards_are_not_in_the_table(self) -> None:
        # class_id 0..51 are computed from suit/rank, never looked up by key.
        for class_id, _name in load_class_map():
            if class_id <= STANDARD_CARD_MAX:
                self.assertNotIn(class_id, parse_embedded_class_ids().values())


if __name__ == "__main__":
    unittest.main()
