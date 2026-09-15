import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import VaultSandbox


class TestMonthlyDrop(unittest.TestCase):
    def setUp(self):
        self.sandbox = VaultSandbox().__enter__()
        from lib import monthly_drop
        self.md = monthly_drop

    def tearDown(self):
        self.sandbox.__exit__(None, None, None)

    def test_ensure_creates_skeleton(self):
        path = self.md.ensure_drop(date(2030, 6, 15))
        self.assertTrue(path.exists())
        content = path.read_text()
        self.assertIn("# 2030-06 드롭된 업무", content)

    def test_append_drop_line_with_children(self):
        from lib.models import TaskBlock
        path = self.md.ensure_drop(date(2030, 6, 10))
        block = TaskBlock(
            top_text="맵 성능",
            carryover_days=5,
            origin_date=date(2030, 6, 3),
            children=["    - 원인 분석중", "    - [x] 조사 완료"],
        )
        self.md.append_dropped(path, date(2030, 6, 10), block)
        content = path.read_text()
        self.assertIn("- [-] 맵 성능 (06-03 시작, 06-10 드롭, 5영업일 이월)", content)
        self.assertIn("    - 원인 분석중", content)
        self.assertIn("    - [x] 조사 완료", content)

    def test_append_immediate_drop(self):
        from lib.models import TaskBlock
        path = self.md.ensure_drop(date(2030, 6, 3))
        block = TaskBlock(top_text="폐기", is_dropped_immediate=True)
        self.md.append_dropped(path, date(2030, 6, 3), block)
        self.assertIn("- [-] 폐기 (06-03 즉시 드롭)", path.read_text())


if __name__ == "__main__":
    unittest.main()
