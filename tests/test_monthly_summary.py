import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import VaultSandbox


class TestMonthlySummary(unittest.TestCase):
    def setUp(self):
        self.sandbox = VaultSandbox().__enter__()
        from lib import monthly_summary
        self.ms = monthly_summary

    def tearDown(self):
        self.sandbox.__exit__(None, None, None)

    def test_ensure_creates_skeleton(self):
        path = self.ms.ensure_summary(date(2030, 6, 15))
        self.assertTrue(path.exists())
        content = path.read_text()
        self.assertIn("2030-06 월간 종합", content)
        self.assertIn("## 📈 이번 달 요약", content)
        self.assertIn("- 완료: 0건", content)
        self.assertIn("## 1주차", content)

    def test_ensure_idempotent(self):
        p1 = self.ms.ensure_summary(date(2030, 6, 15))
        original = p1.read_text()
        p1.write_text(original + "\nEXTRA")
        p2 = self.ms.ensure_summary(date(2030, 6, 15))
        self.assertEqual(p1, p2)
        self.assertIn("EXTRA", p2.read_text())

    def test_week_range_for_saturday_start(self):
        path = self.ms.ensure_summary(date(2030, 6, 15))
        content = path.read_text()
        self.assertIn("## 1주차 (06-01 ~ 06-02)", content)
        self.assertIn("## 2주차 (06-03 ~ 06-07)", content)

    def test_append_completed_same_day(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 3))
        block = TaskBlock(top_text="할일 A", origin_date=date(2030, 6, 3))
        self.ms.append_event(path, "completed", date(2030, 6, 3), block)
        content = path.read_text()
        self.assertIn("- 06-03 할일 A (당일)", content)

    def test_append_completed_multi_day(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 5))
        block = TaskBlock(
            top_text="긴 작업",
            carryover_days=3,
            origin_date=date(2030, 6, 2),
        )
        self.ms.append_event(path, "completed", date(2030, 6, 5), block)
        content = path.read_text()
        self.assertIn("- 06-05 긴 작업 (3영업일 소요, 06-02 시작)", content)

    def test_append_dropped_multi_day(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 10))
        block = TaskBlock(
            top_text="드롭할 것",
            carryover_days=5,
            origin_date=date(2030, 6, 3),
        )
        self.ms.append_event(path, "dropped", date(2030, 6, 10), block)
        content = path.read_text()
        self.assertIn("- 06-10 드롭할 것 (06-03 시작, 5영업일 이월 후 드롭)", content)

    def test_append_dropped_immediate(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 3))
        block = TaskBlock(top_text="즉시 폐기", is_dropped_immediate=True)
        self.ms.append_event(path, "dropped", date(2030, 6, 3), block)
        self.assertIn("- 06-03 즉시 폐기 (즉시 드롭)", path.read_text())

    def test_append_archived(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 3))
        block = TaskBlock(top_text="보관 대상 #보관", has_archive_marker=True)
        self.ms.append_event(path, "archived", date(2030, 6, 3), block)
        self.assertIn("- 06-03 보관 대상 #보관", path.read_text())

    def test_recompute_header_counts_and_average(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 3))
        for d, days, origin in [
            (date(2030, 6, 3), 0, date(2030, 6, 3)),
            (date(2030, 6, 5), 2, date(2030, 6, 3)),
            (date(2030, 6, 6), 3, date(2030, 6, 3)),
        ]:
            self.ms.append_event(
                path, "completed", d,
                TaskBlock(top_text=f"job-{d.day}", carryover_days=days, origin_date=origin),
            )
        block = TaskBlock(top_text="dropped", carryover_days=5, origin_date=date(2030, 6, 3))
        self.ms.append_event(path, "dropped", date(2030, 6, 10), block)
        self.ms.recompute_header(path)
        content = path.read_text()
        self.assertIn("- 완료: 3건", content)
        self.assertIn("- 드롭: 1건", content)
        self.assertIn("- 보관 이동: 0건", content)
        self.assertIn("- 평균 완료 소요: 1.7 영업일", content)

    def test_events_grouped_by_correct_week(self):
        from lib.models import TaskBlock
        path = self.ms.ensure_summary(date(2030, 6, 3))
        self.ms.append_event(
            path, "completed", date(2030, 6, 3),
            TaskBlock(top_text="주2", origin_date=date(2030, 6, 3)),
        )
        self.ms.append_event(
            path, "completed", date(2030, 6, 10),
            TaskBlock(top_text="주3", origin_date=date(2030, 6, 10)),
        )
        content = path.read_text()
        wk3_pos = content.index("## 3주차")
        self.assertLess(content.index("주2"), wk3_pos)
        self.assertGreater(content.index("주3"), wk3_pos)


if __name__ == "__main__":
    unittest.main()
