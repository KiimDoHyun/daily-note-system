import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.daily_writer import render_daily_note
from lib.models import TaskBlock


class TestRenderDailyNote(unittest.TestCase):
    def test_empty_carryover(self):
        out = render_daily_note(date(2030, 6, 3), [])
        self.assertIn("## 📌 할일", out)
        self.assertIn("## ✅ 이월된 할일", out)
        self.assertIn("## 💬 메모", out)
        self.assertIn("[[2030-06 종합]]", out)
        self.assertIn("[[2030-06 드롭]]", out)
        self.assertIn("[[보관함]]", out)

    def test_1day_carryover_line(self):
        block = TaskBlock(
            top_text="SNMP 개선",
            carryover_days=1,
            origin_date=date(2030, 6, 2),
        )
        out = render_daily_note(date(2030, 6, 3), [block])
        self.assertIn("- [ ] SNMP 개선 (1일째 이월, 06-02~)", out)
        self.assertNotIn("🟠", out)
        self.assertNotIn("🔴", out)
        self.assertNotIn("드롭 예정", out)

    def test_3day_orange_warning(self):
        block = TaskBlock(
            top_text="맵 성능",
            carryover_days=3,
            origin_date=date(2030, 5, 30),
        )
        out = render_daily_note(date(2030, 6, 4), [block])
        self.assertIn("🟠 - [ ] 맵 성능 (3일째 이월, 05-30~) (드롭 예정입니다)", out)

    def test_4day_red_warning(self):
        block = TaskBlock(
            top_text="맵 성능",
            carryover_days=4,
            origin_date=date(2030, 5, 29),
        )
        out = render_daily_note(date(2030, 6, 4), [block])
        self.assertIn("🔴 - [ ] 맵 성능 (4일째 이월, 05-29~) (드롭 예정입니다)", out)

    def test_sort_oldest_first(self):
        blocks = [
            TaskBlock(top_text="1일", carryover_days=1, origin_date=date(2030, 6, 2)),
            TaskBlock(top_text="3일", carryover_days=3, origin_date=date(2030, 5, 30)),
            TaskBlock(top_text="2일", carryover_days=2, origin_date=date(2030, 6, 1)),
        ]
        out = render_daily_note(date(2030, 6, 3), blocks)
        idx3 = out.index("3일")
        idx2 = out.index("2일")
        idx1 = out.index("1일")
        self.assertLess(idx3, idx2)
        self.assertLess(idx2, idx1)

    def test_children_included(self):
        block = TaskBlock(
            top_text="블록",
            carryover_days=2,
            origin_date=date(2030, 6, 1),
            children=["    - 메모", "    - [x] 서브"],
        )
        out = render_daily_note(date(2030, 6, 3), [block])
        self.assertIn("    - 메모", out)
        self.assertIn("    - [x] 서브", out)


if __name__ == "__main__":
    unittest.main()
