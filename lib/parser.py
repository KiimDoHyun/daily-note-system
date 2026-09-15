import re
from datetime import date
from pathlib import Path
from typing import Optional

from .config import (
    CARRYOVER_SECTION_HEADERS,
    MARKER_ARCHIVE,
    MARKER_LONG,
    SECTION_MEMO,
    TODO_SECTION_HEADERS,
    WARN_ORANGE,
    WARN_RED,
)
from .models import DailyNoteParsed, TaskBlock

TOP_LEVEL_LINE_RE = re.compile(
    r"^(?P<warn>🟠 |🔴 )?- \[(?P<check>[ x\-])\] (?P<text>.*)$"
)

CARRYOVER_TAG_RE = re.compile(
    r"\s*\((?P<days>\d+)일째 이월, (?P<mm>\d{2})-(?P<dd>\d{2})~\)"
    r"(\s*\(드롭 예정입니다\))?\s*$"
)


def parse_daily_note(path: Path, note_date: date) -> DailyNoteParsed:
    text = path.read_text(encoding="utf-8")
    return parse_daily_note_text(text, note_date)


def parse_daily_note_text(text: str, note_date: date) -> DailyNoteParsed:
    lines = text.splitlines()
    sections = _split_sections(lines)
    todo_lines = _pick_section(sections, TODO_SECTION_HEADERS)
    carry_lines = _pick_section(sections, CARRYOVER_SECTION_HEADERS)
    memo_lines = _pick_section(sections, (SECTION_MEMO,))

    active_blocks = _parse_blocks(todo_lines, note_date, is_carryover=False)
    carryover_blocks = _parse_blocks(carry_lines, note_date, is_carryover=True)
    memo_clean = _strip_footer(memo_lines)

    return DailyNoteParsed(
        note_date=note_date,
        active_blocks=active_blocks,
        carryover_blocks=carryover_blocks,
        memo_lines=memo_clean,
    )


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_header: Optional[str] = None
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("## "):
            current_header = stripped
            sections.setdefault(current_header, [])
        elif current_header is not None:
            sections[current_header].append(line)
    return sections


def _pick_section(
    sections: dict[str, list[str]], candidates: tuple[str, ...]
) -> list[str]:
    for header in candidates:
        if header in sections:
            return sections[header]
    return []


def _parse_blocks(
    lines: list[str], note_date: date, is_carryover: bool
) -> list[TaskBlock]:
    blocks: list[TaskBlock] = []
    current: Optional[TaskBlock] = None
    current_children: list[str] = []

    for raw in lines:
        if _is_top_level_line(raw):
            if current is not None:
                current.children = _trim_trailing_blank(current_children)
                blocks.append(current)
            current, current_children = _new_block_from_line(
                raw, note_date, is_carryover
            )
        else:
            if current is None:
                continue
            current_children.append(raw)

    if current is not None:
        current.children = _trim_trailing_blank(current_children)
        blocks.append(current)

    return blocks


def _is_top_level_line(line: str) -> bool:
    if not line:
        return False
    if line.startswith(" ") or line.startswith("\t"):
        return False
    return bool(TOP_LEVEL_LINE_RE.match(line))


def _new_block_from_line(
    line: str, note_date: date, is_carryover: bool
) -> tuple[TaskBlock, list[str]]:
    m = TOP_LEVEL_LINE_RE.match(line)
    assert m is not None
    check = m.group("check")
    text = m.group("text")

    is_completed = check == "x"
    is_dropped_immediate = check == "-"

    carryover_days = 0
    origin_date: Optional[date] = None
    if is_carryover:
        tag_match = CARRYOVER_TAG_RE.search(text)
        if tag_match:
            carryover_days = int(tag_match.group("days"))
            origin_date = _resolve_origin_date(
                note_date, int(tag_match.group("mm")), int(tag_match.group("dd"))
            )
            text = text[: tag_match.start()].rstrip()

    has_archive_marker = MARKER_ARCHIVE in text
    has_long_marker = MARKER_LONG in text

    block = TaskBlock(
        top_text=text,
        is_completed=is_completed,
        is_dropped_immediate=is_dropped_immediate,
        has_archive_marker=has_archive_marker,
        has_long_marker=has_long_marker,
        carryover_days=carryover_days,
        origin_date=origin_date,
    )
    return block, []


def _resolve_origin_date(note_date: date, mm: int, dd: int) -> date:
    year = note_date.year
    candidate = date(year, mm, dd)
    if candidate > note_date:
        candidate = date(year - 1, mm, dd)
    return candidate


def _trim_trailing_blank(children: list[str]) -> list[str]:
    end = len(children)
    while end > 0 and children[end - 1].strip() == "":
        end -= 1
    return children[:end]


def _strip_footer(memo_lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in memo_lines:
        if line.startswith("---"):
            break
        out.append(line)
    while out and out[-1].strip() == "":
        out.pop()
    return out
