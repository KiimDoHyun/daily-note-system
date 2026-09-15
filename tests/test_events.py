import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.events import classify_events
from lib.models import DailyNoteParsed, TaskBlock


def _active(text, **kw):
    return TaskBlock(top_text=text, **kw)


def _carry(text, days, origin, **kw):
    return TaskBlock(top_text=text, carryover_days=days, origin_date=origin, **kw)


class TestActiveClassification(unittest.TestCase):
    def test_new_active_becomes_1day_carryover(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[_active("할일 A")],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.carrying_over), 1)
        block = events.carrying_over[0]
        self.assertEqual(block.carryover_days, 1)
        self.assertEqual(block.origin_date, date(2030, 6, 3))

    def test_active_completed_goes_to_completed(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[_active("완료 활성", is_completed=True)],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.completed), 1)
        self.assertEqual(events.carrying_over, [])

    def test_active_immediate_drop(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[_active("폐기", is_dropped_immediate=True)],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.dropped), 1)

    def test_active_archive(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[_active("보관 대상 #보관", has_archive_marker=True)],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.archived), 1)
        self.assertEqual(events.carrying_over, [])


class TestCarryoverClassification(unittest.TestCase):
    def test_1day_becomes_2day(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            carryover_blocks=[_carry("이월 A", 1, date(2030, 6, 2))],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.carrying_over), 1)
        b = events.carrying_over[0]
        self.assertEqual(b.carryover_days, 2)
        self.assertEqual(b.origin_date, date(2030, 6, 2))

    def test_4day_completed(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            carryover_blocks=[
                _carry("완료된 이월", 4, date(2030, 5, 28), is_completed=True)
            ],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.completed), 1)
        self.assertEqual(events.completed[0].carryover_days, 4)
        self.assertEqual(events.completed[0].origin_date, date(2030, 5, 28))

    def test_4day_becomes_5day_drops(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            carryover_blocks=[_carry("이월", 4, date(2030, 5, 28))],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.dropped), 1)
        self.assertEqual(events.carrying_over, [])

    def test_4day_with_long_marker_stays(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            carryover_blocks=[
                _carry("장기", 4, date(2030, 5, 28), has_long_marker=True)
            ],
        )
        events = classify_events(parsed)
        self.assertEqual(events.dropped, [])
        self.assertEqual(len(events.carrying_over), 1)
        self.assertEqual(events.carrying_over[0].carryover_days, 5)

    def test_carryover_with_archive_marker(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            carryover_blocks=[
                _carry("보관 #보관", 2, date(2030, 6, 1), has_archive_marker=True)
            ],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.archived), 1)
        self.assertEqual(events.carrying_over, [])


class TestPriorityOrder(unittest.TestCase):
    def test_immediate_drop_beats_completed(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[
                _active("edge", is_dropped_immediate=True, is_completed=True)
            ],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.dropped), 1)
        self.assertEqual(events.completed, [])

    def test_completed_beats_archive(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[
                _active("edge #보관", is_completed=True, has_archive_marker=True)
            ],
        )
        events = classify_events(parsed)
        self.assertEqual(len(events.completed), 1)
        self.assertEqual(events.archived, [])


class TestBlockPreservation(unittest.TestCase):
    def test_children_kept_on_carryover(self):
        parsed = DailyNoteParsed(
            note_date=date(2030, 6, 3),
            active_blocks=[
                _active("with subs", children=["    - 메모", "    - [x] 서브"])
            ],
        )
        events = classify_events(parsed)
        b = events.carrying_over[0]
        self.assertEqual(b.children, ["    - 메모", "    - [x] 서브"])


if __name__ == "__main__":
    unittest.main()
