import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MigrationDocumentationTests(unittest.TestCase):
    def test_all_classifications_and_required_assets_are_documented(self):
        text = (ROOT / "docs" / "migration" / "ZOS_INVENTORY.md").read_text(encoding="utf-8")
        for category in "ABCDEFG":
            self.assertIn(f"Category {category}", text)
        for target in ("core/kernel", "core/foundation", "core/models", "task routing", "permission model", "model update protocol", "personal constitution", "decision models", "writing models", "blind spot models", "memory", "schemas", "runtime architecture"):
            self.assertIn(target.lower(), text.lower())


if __name__ == "__main__":
    unittest.main()

