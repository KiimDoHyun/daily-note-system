import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.calendar_utils import (
    is_weekend,
    previous_business_day,
    business_days_between,
    week_of_month,
)


class TestIsWeekend(unittest.TestCase):
    def test_monday_false(self):
        self.assertFalse(is_weekend(date(2030, 6, 3)))

    def test_friday_false(self):
        self.assertFalse(is_weekend(date(2030, 6, 7)))

    def test_saturday_true(self):
        self.assertTrue(is_weekend(date(2030, 6, 8)))

    def test_sunday_true(self):
        self.assertTrue(is_weekend(date(2030, 6, 9)))


class TestPreviousBusinessDay(unittest.TestCase):
    def test_tuesday_returns_monday(self):
        self.assertEqual(
            previous_business_day(date(2030, 6, 4)), date(2030, 6, 3)
        )

    def test_monday_returns_previous_friday(self):
        self.assertEqual(
            previous_business_day(date(2030, 6, 10)), date(2030, 6, 7)
        )

    def test_sunday_returns_friday(self):
        self.assertEqual(
            previous_business_day(date(2030, 6, 9)), date(2030, 6, 7)
        )

    def test_month_boundary(self):
        self.assertEqual(
            previous_business_day(date(2030, 7, 1)), date(2030, 6, 28)
        )


class TestBusinessDaysBetween(unittest.TestCase):
    def test_same_day_zero(self):
        self.assertEqual(business_days_between(date(2030, 6, 3), date(2030, 6, 3)), 0)

    def test_consecutive_business_days(self):
        self.assertEqual(business_days_between(date(2030, 6, 3), date(2030, 6, 4)), 1)

    def test_over_weekend(self):
        self.assertEqual(business_days_between(date(2030, 6, 7), date(2030, 6, 10)), 1)

    def test_full_week(self):
        self.assertEqual(business_days_between(date(2030, 6, 3), date(2030, 6, 10)), 5)

    def test_reversed_returns_zero(self):
        self.assertEqual(business_days_between(date(2030, 6, 10), date(2030, 6, 3)), 0)


class TestWeekOfMonth(unittest.TestCase):
    def test_2030_06_first_week(self):
        self.assertEqual(week_of_month(date(2030, 6, 1)), 1)
        self.assertEqual(week_of_month(date(2030, 6, 2)), 1)

    def test_2030_06_second_week(self):
        self.assertEqual(week_of_month(date(2030, 6, 3)), 2)
        self.assertEqual(week_of_month(date(2030, 6, 7)), 2)

    def test_2030_06_last_week(self):
        self.assertEqual(week_of_month(date(2030, 6, 24)), 5)
        self.assertEqual(week_of_month(date(2030, 6, 28)), 5)

    def test_month_starting_monday(self):
        self.assertEqual(week_of_month(date(2030, 4, 1)), 1)
        self.assertEqual(week_of_month(date(2030, 4, 7)), 1)
        self.assertEqual(week_of_month(date(2030, 4, 8)), 2)


if __name__ == "__main__":
    unittest.main()
