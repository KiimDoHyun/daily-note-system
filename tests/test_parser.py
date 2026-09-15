import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.parser import parse_daily_note_text


NEW_TEMPLATE = """---
date: 2030-06-04
tags: [daily]
---

# 2030-06-04 데일리

## 📌 할일
- [ ] 활성 할일 A
- [x] 완료된 활성 B
- [-] 즉시 드롭 C
- [ ] 보관 대상 #보관
- [ ] 장기 항목 #장기

## ✅ 이월된 할일
- [ ] SNMP 개선 (1일째 이월, 06-03~)
    - 원인은 host 필터 누락
    - [x] 서브 완료된 것
    - [ ] 아직 안 한 서브
🟠 - [ ] Health map 성능 (3일째 이월, 06-01~) (드롭 예정입니다)
🔴 - [x] 완료된 이월 (4일째 이월, 05-30~) (드롭 예정입니다)

## 💬 메모

자유 메모 한 줄
두 줄

---
📎 마커: ...
"""


OLD_TEMPLATE = """---
date: 2030-06-04
tags: [daily]
---

# 2030-06-04 데일리

## 📌 오늘의 목표
- [ ] 옛 규격 할일 A

## ✅ 미완료 이월
- [ ] 옛 규격 이월 (2일째 이월, 06-02~)

## 💬 메모
"""


class TestParseNewTemplate(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_daily_note_text(NEW_TEMPLATE, date(2030, 6, 4))

    def test_active_block_count(self):
        self.assertEqual(len(self.parsed.active_blocks), 5)

    def test_active_completed(self):
        b = self.parsed.active_blocks[1]
        self.assertEqual(b.top_text, "완료된 활성 B")
        self.assertTrue(b.is_completed)

    def test_active_immediate_drop(self):
        b = self.parsed.active_blocks[2]
        self.assertTrue(b.is_dropped_immediate)

    def test_active_archive_marker(self):
        b = self.parsed.active_blocks[3]
        self.assertTrue(b.has_archive_marker)

    def test_active_long_marker(self):
        b = self.parsed.active_blocks[4]
        self.assertTrue(b.has_long_marker)

    def test_carryover_block_count(self):
        self.assertEqual(len(self.parsed.carryover_blocks), 3)

    def test_carryover_1day(self):
        b = self.parsed.carryover_blocks[0]
        self.assertEqual(b.top_text, "SNMP 개선")
        self.assertEqual(b.carryover_days, 1)
        self.assertEqual(b.origin_date, date(2030, 6, 3))
        self.assertFalse(b.is_completed)
        self.assertEqual(len(b.children), 3)

    def test_carryover_children_include_subs(self):
        b = self.parsed.carryover_blocks[0]
        self.assertIn("    - 원인은 host 필터 누락", b.children)
        self.assertIn("    - [x] 서브 완료된 것", b.children)
        self.assertIn("    - [ ] 아직 안 한 서브", b.children)

    def test_carryover_3day_warning(self):
        b = self.parsed.carryover_blocks[1]
        self.assertEqual(b.top_text, "Health map 성능")
        self.assertEqual(b.carryover_days, 3)

    def test_carryover_4day_completed(self):
        b = self.parsed.carryover_blocks[2]
        self.assertTrue(b.is_completed)
        self.assertEqual(b.carryover_days, 4)
        self.assertEqual(b.origin_date, date(2030, 5, 30))

    def test_memo_lines_captured(self):
        text_joined = "\n".join(self.parsed.memo_lines)
        self.assertIn("자유 메모 한 줄", text_joined)
        self.assertIn("두 줄", text_joined)
        self.assertNotIn("📎 마커", text_joined)


class TestParseOldTemplate(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_daily_note_text(OLD_TEMPLATE, date(2030, 6, 4))

    def test_old_sections_detected(self):
        self.assertEqual(len(self.parsed.active_blocks), 1)
        self.assertEqual(self.parsed.active_blocks[0].top_text, "옛 규격 할일 A")
        self.assertEqual(len(self.parsed.carryover_blocks), 1)
        self.assertEqual(self.parsed.carryover_blocks[0].carryover_days, 2)


class TestOriginDateYearRollover(unittest.TestCase):
    def test_january_note_with_december_tag(self):
        text = (
            "## ✅ 이월된 할일\n"
            "- [ ] 넘어온 항목 (3일째 이월, 12-30~)\n"
        )
        parsed = parse_daily_note_text(text, date(2030, 1, 6))
        self.assertEqual(parsed.carryover_blocks[0].origin_date, date(2029, 12, 30))


if __name__ == "__main__":
    unittest.main()
