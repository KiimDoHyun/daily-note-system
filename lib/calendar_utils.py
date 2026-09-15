from datetime import date, timedelta


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def previous_business_day(d: date) -> date:
    prev = d - timedelta(days=1)
    while is_weekend(prev):
        prev -= timedelta(days=1)
    return prev


def next_business_day(d: date) -> date:
    nxt = d + timedelta(days=1)
    while is_weekend(nxt):
        nxt += timedelta(days=1)
    return nxt


def business_days_between(start: date, end: date) -> int:
    if end <= start:
        return 0
    count = 0
    cur = start
    while cur < end:
        cur += timedelta(days=1)
        if not is_weekend(cur):
            count += 1
    return count


def week_of_month(d: date) -> int:
    first_of_month = d.replace(day=1)
    first_weekday = first_of_month.weekday()
    if first_weekday == 0:
        return (d.day - 1) // 7 + 1
    first_monday_day = 8 - first_weekday
    if d.day < first_monday_day:
        return 1
    return (d.day - first_monday_day) // 7 + 2


def week_range_of_month(d: date) -> tuple[date, date]:
    wk = week_of_month(d)
    ranges = all_weeks_of_month(d)
    for num, start, end in ranges:
        if num == wk:
            return start, end
    return d, d


def all_weeks_of_month(any_day: date) -> list[tuple[int, date, date]]:
    first = any_day.replace(day=1)
    last = _last_day_of_month(any_day)
    first_weekday = first.weekday()

    ranges: list[tuple[int, date, date]] = []
    if first_weekday == 0:
        ranges.append((1, first, min(first + timedelta(days=4), last)))
        cur = first + timedelta(days=7)
        week_num = 2
    else:
        first_monday_day = 8 - first_weekday
        if first_monday_day > last.day:
            ranges.append((1, first, last))
            return ranges
        first_monday = first.replace(day=first_monday_day)
        ranges.append((1, first, first_monday - timedelta(days=1)))
        cur = first_monday
        week_num = 2

    while cur <= last:
        end = min(cur + timedelta(days=4), last)
        ranges.append((week_num, cur, end))
        cur = cur + timedelta(days=7)
        week_num += 1

    return ranges


def _last_day_of_month(d: date) -> date:
    if d.month == 12:
        next_month = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
    return next_month - timedelta(days=1)
