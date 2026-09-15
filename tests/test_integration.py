import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._helpers import VaultSandbox


def _write_note(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_note(date_str: str, todo_lines=None, carry_lines=None) -> str:
    todo_lines = todo_lines or []
    carry_lines = carry_lines or []
    parts = [
        "---",
        f"date: {date_str}",
        "tags: [daily]",
        "---",
        "",
        f"# {date_str} 데일리",
        "",
        "## 📌 할일",
        *todo_lines,
        "",
        "## ✅ 이월된 할일",
        *carry_lines,
        "",
        "## 💬 메모",
        "",
    ]
    return "\n".join(parts) + "\n"


class BaseScenario(unittest.TestCase):
    def setUp(self):
        self.sandbox = VaultSandbox().__enter__()
        from lib import config
        from lib.orchestrator import run_create, run_force, run_recompute
        self.config = config
        self.run_create = run_create
        self.run_force = run_force
        self.run_recompute = run_recompute

    def tearDown(self):
        self.sandbox.__exit__(None, None, None)

    def _daily_path(self, d: date) -> Path:
        return self.config.daily_note_path(d)

    def _summary_path(self, d: date) -> Path:
        return self.config.monthly_summary_path(d)

    def _drop_path(self, d: date) -> Path:
        return self.config.monthly_drop_path(d)

    def _archive_path(self) -> Path:
        return self.config.archive_path()


class Scenario1_FirstRun(BaseScenario):
    def test(self):
        result = self.run_create(date(2030, 6, 3))
        self.assertEqual(result.status, "created")
        today = self._daily_path(date(2030, 6, 3))
        self.assertTrue(today.exists())
        content = today.read_text()
        self.assertIn("## ✅ 이월된 할일", content)
        self.assertNotIn("(1일째 이월", content)
        summary = self._summary_path(date(2030, 6, 3))
        self.assertTrue(summary.exists())
        self.assertIn("- 완료: 0건", summary.read_text())


class Scenario2_ActiveIncompleteToCarryover(BaseScenario):
    def test(self):
        prev = date(2030, 6, 3)
        _write_note(
            self._daily_path(prev),
            _minimal_note(prev.isoformat(), todo_lines=["- [ ] 할일 A", "- [ ] 할일 B"]),
        )
        self.run_create(date(2030, 6, 4))
        content = self._daily_path(date(2030, 6, 4)).read_text()
        self.assertIn("- [ ] 할일 A (1일째 이월, 06-03~)", content)
        self.assertIn("- [ ] 할일 B (1일째 이월, 06-03~)", content)


class Scenario3_CompletedActiveLogged(BaseScenario):
    def test(self):
        prev = date(2030, 6, 3)
        _write_note(
            self._daily_path(prev),
            _minimal_note(prev.isoformat(), todo_lines=["- [x] 완료 A", "- [ ] 미완료 B"]),
        )
        self.run_create(date(2030, 6, 4))
        today_content = self._daily_path(date(2030, 6, 4)).read_text()
        self.assertNotIn("완료 A", today_content)
        self.assertIn("- [ ] 미완료 B (1일째 이월, 06-03~)", today_content)
        summary_content = self._summary_path(prev).read_text()
        self.assertIn("- 06-03 완료 A (당일)", summary_content)


class Scenario4_ThreeDayOrangeWarning(BaseScenario):
    def test(self):
        prev = date(2030, 6, 5)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                carry_lines=["- [ ] 오래된 할일 (2일째 이월, 06-03~)"],
            ),
        )
        self.run_create(date(2030, 6, 6))
        content = self._daily_path(date(2030, 6, 6)).read_text()
        self.assertIn("🟠 - [ ] 오래된 할일 (3일째 이월, 06-03~) (드롭 예정입니다)", content)


class Scenario5_FiveDayDrops(BaseScenario):
    def test(self):
        prev = date(2030, 6, 7)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                carry_lines=["🔴 - [ ] 밀린 할일 (4일째 이월, 06-03~) (드롭 예정입니다)"],
            ),
        )
        self.run_create(date(2030, 6, 10))
        today_content = self._daily_path(date(2030, 6, 10)).read_text()
        self.assertNotIn("밀린 할일", today_content)
        drop = self._drop_path(prev)
        self.assertTrue(drop.exists())
        drop_content = drop.read_text()
        self.assertIn("- [-] 밀린 할일", drop_content)
        self.assertIn("06-03 시작", drop_content)
        summary_content = self._summary_path(prev).read_text()
        self.assertIn("- 06-07 밀린 할일 (06-03 시작, 5영업일 이월 후 드롭)", summary_content)


class Scenario6_LongMarkerExempt(BaseScenario):
    def test(self):
        prev = date(2030, 6, 7)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                carry_lines=["🔴 - [ ] 장기 프로젝트 #장기 (4일째 이월, 06-03~) (드롭 예정입니다)"],
            ),
        )
        self.run_create(date(2030, 6, 10))
        today_content = self._daily_path(date(2030, 6, 10)).read_text()
        self.assertIn("장기 프로젝트 #장기", today_content)
        self.assertIn("(5일째 이월, 06-03~)", today_content)
        drop = self._drop_path(prev)
        self.assertFalse(drop.exists())


class Scenario7_ArchiveMarker(BaseScenario):
    def test(self):
        prev = date(2030, 6, 5)
        _write_note(
            self._daily_path(prev),
            _minimal_note(prev.isoformat(), todo_lines=["- [ ] 보관하자 #보관"]),
        )
        self.run_create(date(2030, 6, 6))
        today_content = self._daily_path(date(2030, 6, 6)).read_text()
        self.assertNotIn("보관하자", today_content)
        archive = self._archive_path()
        self.assertTrue(archive.exists())
        archive_content = archive.read_text()
        self.assertIn("## 2030-06", archive_content)
        self.assertIn("- [ ] 보관하자 #보관 (보관: 06-05)", archive_content)
        summary_content = self._summary_path(prev).read_text()
        self.assertIn("- 06-05 보관하자 #보관", summary_content)


class Scenario8_ImmediateDrop(BaseScenario):
    def test(self):
        prev = date(2030, 6, 5)
        _write_note(
            self._daily_path(prev),
            _minimal_note(prev.isoformat(), todo_lines=["- [-] 폐기 아이디어"]),
        )
        self.run_create(date(2030, 6, 6))
        drop = self._drop_path(prev)
        self.assertTrue(drop.exists())
        self.assertIn("- [-] 폐기 아이디어 (06-05 즉시 드롭)", drop.read_text())


class Scenario9_BlockChildrenCarryover(BaseScenario):
    def test(self):
        prev = date(2030, 6, 5)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                todo_lines=[
                    "- [ ] 큰 할일",
                    "    - 하위 메모",
                    "    - [x] 서브 완료",
                    "    - [ ] 서브 미완료",
                ],
            ),
        )
        self.run_create(date(2030, 6, 6))
        content = self._daily_path(date(2030, 6, 6)).read_text()
        self.assertIn("- [ ] 큰 할일 (1일째 이월, 06-05~)", content)
        self.assertIn("    - 하위 메모", content)
        self.assertIn("    - [x] 서브 완료", content)
        self.assertIn("    - [ ] 서브 미완료", content)


class Scenario10_MidCarryoverAddedSubsCarryOver(BaseScenario):
    def test(self):
        first = date(2030, 6, 3)
        _write_note(
            self._daily_path(first),
            _minimal_note(first.isoformat(), todo_lines=["- [ ] 원본"]),
        )
        self.run_create(date(2030, 6, 4))
        yesterday_path = self._daily_path(date(2030, 6, 4))
        content = yesterday_path.read_text()
        content = content.replace(
            "- [ ] 원본 (1일째 이월, 06-03~)",
            "- [ ] 원본 (1일째 이월, 06-03~)\n    - 추가한 메모\n    - [ ] 추가한 서브",
        )
        yesterday_path.write_text(content, encoding="utf-8")
        self.run_create(date(2030, 6, 5))
        today = self._daily_path(date(2030, 6, 5)).read_text()
        self.assertIn("- [ ] 원본 (2일째 이월, 06-03~)", today)
        self.assertIn("    - 추가한 메모", today)
        self.assertIn("    - [ ] 추가한 서브", today)


class Scenario11_ArchiveWithChildren(BaseScenario):
    def test(self):
        prev = date(2030, 6, 5)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                todo_lines=[
                    "- [ ] 보관 대상 #보관",
                    "    - 관련 메모",
                    "    - [x] 서브 완료",
                ],
            ),
        )
        self.run_create(date(2030, 6, 6))
        archive_content = self._archive_path().read_text()
        self.assertIn("- [ ] 보관 대상 #보관 (보관: 06-05)", archive_content)
        self.assertIn("    - 관련 메모", archive_content)
        self.assertIn("    - [x] 서브 완료", archive_content)


class Scenario12_MondayInheritsFriday(BaseScenario):
    def test(self):
        friday = date(2030, 6, 7)
        _write_note(
            self._daily_path(friday),
            _minimal_note(friday.isoformat(), todo_lines=["- [ ] 금요일 미완"]),
        )
        self.run_create(date(2030, 6, 10))
        content = self._daily_path(date(2030, 6, 10)).read_text()
        self.assertIn("- [ ] 금요일 미완 (1일째 이월, 06-07~)", content)


class Scenario13_WeekendSkips(BaseScenario):
    def test(self):
        result = self.run_create(date(2030, 6, 8))
        self.assertEqual(result.status, "skipped_weekend")
        self.assertFalse(self._daily_path(date(2030, 6, 8)).exists())


class Scenario14_MonthBoundary(BaseScenario):
    def test(self):
        friday = date(2030, 6, 28)
        _write_note(
            self._daily_path(friday),
            _minimal_note(friday.isoformat(), todo_lines=["- [ ] 6월 미완"]),
        )
        self.run_create(date(2030, 7, 1))
        content = self._daily_path(date(2030, 7, 1)).read_text()
        self.assertIn("- [ ] 6월 미완 (1일째 이월, 06-28~)", content)
        self.assertTrue(self._summary_path(date(2030, 7, 1)).exists())
        self.assertTrue(self._summary_path(date(2030, 6, 1)).exists())


class Scenario15_OldSectionNamesBackwardCompat(BaseScenario):
    def test(self):
        prev = date(2030, 6, 3)
        old_text = (
            "---\ndate: 2030-06-03\ntags: [daily]\n---\n\n"
            "# 2030-06-03 데일리\n\n"
            "## 📌 오늘의 목표\n- [ ] 옛 규격 A\n\n"
            "## ✅ 미완료 이월\n- [ ] 옛 이월 (2일째 이월, 06-01~)\n\n"
            "## 💬 메모\n"
        )
        _write_note(self._daily_path(prev), old_text)
        self.run_create(date(2030, 6, 4))
        content = self._daily_path(date(2030, 6, 4)).read_text()
        self.assertIn("- [ ] 옛 규격 A (1일째 이월, 06-03~)", content)
        self.assertIn("- [ ] 옛 이월 (3일째 이월, 06-01~)", content)


class Scenario16_DryRunNoFiles(BaseScenario):
    def test(self):
        prev = date(2030, 6, 3)
        _write_note(
            self._daily_path(prev),
            _minimal_note(prev.isoformat(), todo_lines=["- [x] 어제 완료"]),
        )
        result = self.run_create(date(2030, 6, 4), dry_run=True)
        self.assertEqual(result.status, "dry_run")
        self.assertFalse(self._daily_path(date(2030, 6, 4)).exists())
        self.assertFalse(self._summary_path(prev).exists())


class Scenario17_Idempotent(BaseScenario):
    def test(self):
        prev = date(2030, 6, 3)
        _write_note(
            self._daily_path(prev),
            _minimal_note(prev.isoformat(), todo_lines=["- [x] 완료 X"]),
        )
        self.run_create(date(2030, 6, 4))
        summary_first = self._summary_path(prev).read_text()
        result_second = self.run_create(date(2030, 6, 4))
        self.assertEqual(result_second.status, "skipped_exists")
        summary_second = self._summary_path(prev).read_text()
        self.assertEqual(summary_first, summary_second)


class Scenario18_ComplexMix(BaseScenario):
    def test(self):
        prev = date(2030, 6, 7)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                todo_lines=[
                    "- [x] 완료 P",
                    "- [x] 완료 Q",
                    "- [ ] 보관해 #보관",
                    "- [-] 폐기해",
                    "- [ ] 새 미완",
                ],
                carry_lines=[
                    "- [ ] 이월 A (1일째 이월, 06-06~)",
                    "- [ ] 이월 B (2일째 이월, 06-05~)",
                    "🔴 - [ ] 임박 드롭 (4일째 이월, 06-03~) (드롭 예정입니다)",
                ],
            ),
        )
        self.run_create(date(2030, 6, 10))
        today_content = self._daily_path(date(2030, 6, 10)).read_text()
        self.assertNotIn("완료 P", today_content)
        self.assertNotIn("보관해", today_content)
        self.assertNotIn("폐기해", today_content)
        self.assertNotIn("임박 드롭", today_content)
        self.assertIn("- [ ] 새 미완 (1일째 이월, 06-07~)", today_content)
        self.assertIn("- [ ] 이월 A (2일째 이월, 06-06~)", today_content)
        self.assertIn("🟠 - [ ] 이월 B (3일째 이월, 06-05~) (드롭 예정입니다)", today_content)

        summary_content = self._summary_path(prev).read_text()
        self.assertIn("- 06-07 완료 P (당일)", summary_content)
        self.assertIn("- 06-07 완료 Q (당일)", summary_content)
        self.assertIn("- 06-07 폐기해 (즉시 드롭)", summary_content)
        self.assertIn("- 06-07 임박 드롭 (06-03 시작, 5영업일 이월 후 드롭)", summary_content)
        self.assertIn("- 06-07 보관해 #보관", summary_content)
        self.assertIn("- 완료: 2건", summary_content)
        self.assertIn("- 드롭: 2건", summary_content)
        self.assertIn("- 보관 이동: 1건", summary_content)


class Scenario19_CarryoverCompletionDuration(BaseScenario):
    def test(self):
        prev = date(2030, 6, 5)
        _write_note(
            self._daily_path(prev),
            _minimal_note(
                prev.isoformat(),
                carry_lines=["- [x] 완료된 이월 (3일째 이월, 06-02~)"],
            ),
        )
        self.run_create(date(2030, 6, 6))
        summary_content = self._summary_path(prev).read_text()
        self.assertIn("- 06-05 완료된 이월 (3영업일 소요, 06-02 시작)", summary_content)


if __name__ == "__main__":
    unittest.main()
