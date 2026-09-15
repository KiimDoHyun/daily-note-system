from dataclasses import replace
from datetime import date
from typing import Optional

from .config import DROP_THRESHOLD_DAYS
from .models import DailyNoteParsed, Events, TaskBlock


def classify_events(parsed: DailyNoteParsed) -> Events:
    events = Events()

    for block in parsed.active_blocks:
        _dispatch(block, events, from_active=True, source_note_date=parsed.note_date)

    for block in parsed.carryover_blocks:
        _dispatch(block, events, from_active=False, source_note_date=parsed.note_date)

    return events


def _dispatch(
    block: TaskBlock,
    events: Events,
    from_active: bool,
    source_note_date: date,
) -> None:
    if block.is_dropped_immediate:
        events.dropped.append(_finalize_for_event(block, from_active, source_note_date))
        return
    if block.is_completed:
        events.completed.append(_finalize_for_event(block, from_active, source_note_date))
        return
    if block.has_archive_marker:
        events.archived.append(_finalize_for_event(block, from_active, source_note_date))
        return

    if from_active:
        carried = _clone_for_carryover(
            block, days=1, origin=source_note_date
        )
        events.carrying_over.append(carried)
        return

    new_days = block.carryover_days + 1
    if new_days >= DROP_THRESHOLD_DAYS and not block.has_long_marker:
        threshold_block = replace(block, carryover_days=new_days)
        events.dropped.append(threshold_block)
        return

    carried = _clone_for_carryover(
        block, days=new_days, origin=block.origin_date
    )
    events.carrying_over.append(carried)


def _finalize_for_event(
    block: TaskBlock, from_active: bool, source_note_date: date
) -> TaskBlock:
    if from_active:
        return replace(block, carryover_days=0, origin_date=source_note_date)
    return block


def _clone_for_carryover(
    block: TaskBlock, days: int, origin: Optional[date]
) -> TaskBlock:
    return replace(
        block,
        carryover_days=days,
        origin_date=origin,
        is_completed=False,
        is_dropped_immediate=False,
    )
