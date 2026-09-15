import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.daily_writer import render_daily_note
from lib.models import TaskBlock


class TestLongMarkerNoWarning(unittest.TestCase):
    def test_3day_long_no_orange(self):
        block = TaskBlock(
            top_text="장기 작업 #장기",
            carryover_days=3,
            origin_date=date(2030, 5, 30),
            has_long_marker=True,
        )
        out = render_daily_note(date(2030, 6, 4), [block])
        self.assertIn("- [ ] 장기 작업 #장기 (3일째 이월, 05-30~)", out)
        self.assertNotIn("🟠", out)
        self.assertNotIn("드롭 예정", out)

    def test_5day_long_no_red(self):
        block = TaskBlock(
            top_text="장기 작업 #장기",
            carryover_days=5,
            origin_date=date(2030, 5, 28),
            has_long_marker=True,
        )
        out = render_daily_note(date(2030, 6, 4), [block])
        self.assertIn("- [ ] 장기 작업 #장기 (5일째 이월, 05-28~)", out)
        self.assertNotIn("🔴", out)
        self.assertNotIn("드롭 예정", out)


if __name__ == "__main__":
    unittest.main()
