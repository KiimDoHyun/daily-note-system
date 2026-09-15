from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .archive import append_archived, ensure_archive
from .calendar_utils import is_weekend, previous_business_day
from .config import daily_note_path
from .daily_writer import write_daily_note
from .events import classify_events
from .models import DailyNoteParsed, Events
from .monthly_drop import append_dropped, ensure_drop
from .monthly_summary import (
    append_event as append_summary_event,
    ensure_summary,
    recompute_header,
)
from .parser import parse_daily_note


@dataclass
class RunResult:
    status: str
    today: date
    today_path: Optional[Path]
    prev_date: Optional[date]
    prev_path: Optional[Path]
    events: Optional[Events]
    detail: str = ""


def run_create(today: date, dry_run: bool = False) -> RunResult:
    if is_weekend(today):
        return RunResult(
            status="skipped_weekend",
            today=today,
            today_path=None,
            prev_date=None,
            prev_path=None,
            events=None,
            detail=f"{today.isoformat()} 은 주말입니다",
        )

    today_path = daily_note_path(today)
    if today_path.exists():
        return RunResult(
            status="skipped_exists",
            today=today,
            today_path=today_path,
            prev_date=None,
            prev_path=None,
            events=None,
            detail=f"이미 존재: {today_path}",
        )

    prev_date, prev_path = _find_previous_note(today)
    if prev_path is not None:
        parsed = parse_daily_note(prev_path, prev_date)
    else:
        parsed = DailyNoteParsed(note_date=today - timedelta(days=1))
        prev_date = parsed.note_date

    events = classify_events(parsed)

    if dry_run:
        return RunResult(
            status="dry_run",
            today=today,
            today_path=today_path,
            prev_date=prev_date,
            prev_path=prev_path,
            events=events,
            detail="dry-run: 파일 수정 없음",
        )

    prev_summary = ensure_summary(prev_date)
    _append_events_in_order(events, prev_date, prev_summary)

    write_daily_note(today, events.carrying_over, today_path)

    if today.month != prev_date.month:
        ensure_summary(today)

    recompute_header(ensure_summary(today))
    if today.month != prev_date.month:
        recompute_header(prev_summary)

    return RunResult(
        status="created",
        today=today,
        today_path=today_path,
        prev_date=prev_date,
        prev_path=prev_path,
        events=events,
    )


def run_force(target: date) -> RunResult:
    path = daily_note_path(target)
    if path.exists():
        path.unlink()
    return run_create(target)


def run_recompute(month: date) -> Path:
    path = ensure_summary(month)
    recompute_header(path)
    return path


def _find_previous_note(today: date, max_days: int = 14):
    for i in range(1, max_days + 1):
        candidate = today - timedelta(days=i)
        if is_weekend(candidate):
            continue
        path = daily_note_path(candidate)
        if path.exists():
            return candidate, path
    return None, None


def _append_events_in_order(
    events: Events, prev_date: date, summary_path: Path
) -> None:
    for block in events.completed:
        append_summary_event(summary_path, "completed", prev_date, block)

    if events.dropped:
        drop_path = ensure_drop(prev_date)
        for block in events.dropped:
            append_dropped(drop_path, prev_date, block)
            append_summary_event(summary_path, "dropped", prev_date, block)

    if events.archived:
        arc_path = ensure_archive()
        for block in events.archived:
            append_archived(arc_path, prev_date, block)
            append_summary_event(summary_path, "archived", prev_date, block)
