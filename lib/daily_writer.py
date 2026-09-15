from datetime import date
from pathlib import Path

from .config import (
    DROP_WARNING_SUFFIX,
    FOOTER,
    SECTION_CARRYOVER_NEW,
    SECTION_MEMO,
    SECTION_TODO_NEW,
    WARN_ORANGE,
    WARN_ORANGE_DAY,
    WARN_RED,
    WARN_RED_DAY,
    monthly_drop_wikilink,
    monthly_summary_wikilink,
)
from .models import TaskBlock


def render_daily_note(today: date, carrying_over: list[TaskBlock]) -> str:
    sorted_blocks = sorted(carrying_over, key=lambda b: -b.carryover_days)
    carry_body = _render_carryover_blocks(sorted_blocks)
    footer = FOOTER.format(
        summary_link=monthly_summary_wikilink(today),
        drop_link=monthly_drop_wikilink(today),
    )

    parts = [
        "---",
        f"date: {today.isoformat()}",
        "tags: [daily]",
        "---",
        "",
        f"# {today.isoformat()} 데일리",
        "",
        SECTION_TODO_NEW,
        "- [ ] ",
        "- [ ] ",
        "- [ ] ",
        "",
        SECTION_CARRYOVER_NEW,
    ]
    if carry_body:
        parts.append(carry_body)
    parts.extend([
        "",
        SECTION_MEMO,
        "",
        "",
        footer,
        "",
    ])
    return "\n".join(parts)


def _render_carryover_blocks(blocks: list[TaskBlock]) -> str:
    lines: list[str] = []
    for block in blocks:
        lines.extend(_render_single_block(block))
    return "\n".join(lines)


def _render_single_block(block: TaskBlock) -> list[str]:
    top = _render_top_line(block)
    return [top] + list(block.children)


def _render_top_line(block: TaskBlock) -> str:
    origin_str = _format_origin(block.origin_date)
    tag = f"({block.carryover_days}일째 이월, {origin_str}~)"
    prefix = ""
    suffix = ""
    if not block.has_long_marker:
        if block.carryover_days == WARN_ORANGE_DAY:
            prefix = f"{WARN_ORANGE} "
            suffix = f" {DROP_WARNING_SUFFIX}"
        elif block.carryover_days >= WARN_RED_DAY:
            prefix = f"{WARN_RED} "
            suffix = f" {DROP_WARNING_SUFFIX}"
    return f"{prefix}- [ ] {block.top_text} {tag}{suffix}"


def _format_origin(origin) -> str:
    if origin is None:
        return "??-??"
    return f"{origin.month:02d}-{origin.day:02d}"


def write_daily_note(today: date, carrying_over: list[TaskBlock], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_daily_note(today, carrying_over), encoding="utf-8")
