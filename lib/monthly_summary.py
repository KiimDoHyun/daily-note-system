import re
from datetime import date
from pathlib import Path
from typing import Optional

from .calendar_utils import all_weeks_of_month, week_of_month
from .config import monthly_summary_path
from .models import TaskBlock

HEADER_START = "## 📈 이번 달 요약"
COMPLETED_HEADER = "### ✅ 완료"
DROPPED_HEADER = "### ⏭️ 드롭"
ARCHIVED_HEADER = "### 📦 보관 이동"
WEEK_HEADER_RE = re.compile(r"^## (\d+)주차 \(\d{2}-\d{2} ~ \d{2}-\d{2}\)$")
EVENT_LINE_RE = re.compile(r"^- (\d{2}-\d{2}) (.+)$")


def ensure_summary(month: date) -> Path:
    path = monthly_summary_path(month)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    ym = f"{month.year:04d}-{month.month:02d}"
    path.write_text(_build_skeleton(month, ym), encoding="utf-8")
    return path


def _build_skeleton(month: date, ym: str) -> str:
    parts = [
        "---",
        f"tags: [monthly-summary, {ym}]",
        "---",
        "",
        f"# {ym} 월간 종합",
        "",
        "> 이 문서는 스크립트가 매일 자동 갱신합니다.",
        "",
        HEADER_START,
        "- 완료: 0건",
        "- 드롭: 0건",
        "- 보관 이동: 0건",
        "- 평균 완료 소요: -",
        "",
    ]
    for num, start, end in all_weeks_of_month(month):
        parts.append(
            f"## {num}주차 ({start.month:02d}-{start.day:02d} ~ "
            f"{end.month:02d}-{end.day:02d})"
        )
        parts.append("")
        parts.append(COMPLETED_HEADER)
        parts.append("")
        parts.append(DROPPED_HEADER)
        parts.append("")
        parts.append(ARCHIVED_HEADER)
        parts.append("")
    return "\n".join(parts)


def append_event(
    summary_path: Path,
    event_type: str,
    event_date: date,
    block: TaskBlock,
) -> None:
    line = _format_event_line(event_type, event_date, block)
    lines = summary_path.read_text(encoding="utf-8").splitlines()
    wk = week_of_month(event_date)
    insert_idx = _find_insertion_index(lines, wk, event_type)
    if insert_idx is None:
        raise RuntimeError(
            f"Cannot find week {wk} + {event_type} section in {summary_path}"
        )
    lines.insert(insert_idx, line)
    if insert_idx + 1 < len(lines) and lines[insert_idx + 1].startswith(("### ", "## ")):
        lines.insert(insert_idx + 1, "")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_insertion_index(
    lines: list[str], wk: int, event_type: str
) -> Optional[int]:
    subsection_header = _subsection_header(event_type)
    in_week = False
    in_sub = False
    sub_header_idx: Optional[int] = None
    last_event_idx: Optional[int] = None
    for i, line in enumerate(lines):
        wm = WEEK_HEADER_RE.match(line)
        if wm:
            if in_sub:
                return _resolve_insert(sub_header_idx, last_event_idx, i)
            in_week = int(wm.group(1)) == wk
            in_sub = False
            sub_header_idx = None
            last_event_idx = None
            continue
        if in_week and line.startswith("### "):
            if in_sub:
                return _resolve_insert(sub_header_idx, last_event_idx, i)
            in_sub = line == subsection_header
            sub_header_idx = i if in_sub else None
            last_event_idx = None
            continue
        if in_sub and EVENT_LINE_RE.match(line):
            last_event_idx = i
    if in_sub:
        return _resolve_insert(sub_header_idx, last_event_idx, len(lines))
    return None


def _resolve_insert(
    sub_header_idx: Optional[int],
    last_event_idx: Optional[int],
    boundary_idx: int,
) -> int:
    if last_event_idx is not None:
        return last_event_idx + 1
    if sub_header_idx is not None:
        return sub_header_idx + 2
    return boundary_idx


def _subsection_header(event_type: str) -> str:
    if event_type == "completed":
        return COMPLETED_HEADER
    if event_type == "dropped":
        return DROPPED_HEADER
    if event_type == "archived":
        return ARCHIVED_HEADER
    raise ValueError(f"Unknown event_type: {event_type}")


def _format_event_line(event_type: str, event_date: date, block: TaskBlock) -> str:
    md = f"{event_date.month:02d}-{event_date.day:02d}"
    text = block.top_text
    if event_type == "completed":
        suffix = _format_completed_suffix(block, event_date)
        return f"- {md} {text} {suffix}"
    if event_type == "dropped":
        suffix = _format_dropped_suffix(block, event_date)
        return f"- {md} {text} {suffix}"
    if event_type == "archived":
        return f"- {md} {text}"
    raise ValueError(event_type)


def _format_completed_suffix(block: TaskBlock, event_date: date) -> str:
    days = block.carryover_days
    if days <= 0 or block.origin_date is None or block.origin_date == event_date:
        return "(당일)"
    origin = f"{block.origin_date.month:02d}-{block.origin_date.day:02d}"
    return f"({days}영업일 소요, {origin} 시작)"


def _format_dropped_suffix(block: TaskBlock, event_date: date) -> str:
    if block.is_dropped_immediate:
        return "(즉시 드롭)"
    if block.origin_date is None:
        return f"({block.carryover_days}영업일 이월 후 드롭)"
    origin = f"{block.origin_date.month:02d}-{block.origin_date.day:02d}"
    return f"({origin} 시작, {block.carryover_days}영업일 이월 후 드롭)"


def recompute_header(summary_path: Path) -> None:
    lines = summary_path.read_text(encoding="utf-8").splitlines()
    completed = _collect_events(lines, COMPLETED_HEADER)
    dropped = _collect_events(lines, DROPPED_HEADER)
    archived = _collect_events(lines, ARCHIVED_HEADER)

    avg = _compute_average_days(completed)
    new_header_lines = [
        HEADER_START,
        f"- 완료: {len(completed)}건",
        f"- 드롭: {len(dropped)}건",
        f"- 보관 이동: {len(archived)}건",
        f"- 평균 완료 소요: {avg}",
    ]

    out = _replace_header_block(lines, new_header_lines)
    summary_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _collect_events(lines: list[str], subsection_header: str) -> list[str]:
    events: list[str] = []
    in_sub = False
    for line in lines:
        if line.startswith("## "):
            in_sub = False
            continue
        if line.startswith("### "):
            in_sub = line == subsection_header
            continue
        if in_sub and EVENT_LINE_RE.match(line):
            events.append(line)
    return events


COMPLETED_SAME_DAY_RE = re.compile(r"\(당일\)$")
COMPLETED_DURATION_RE = re.compile(r"\((\d+)영업일 소요")


def _compute_average_days(completed: list[str]) -> str:
    if not completed:
        return "-"
    total = 0
    count = 0
    for line in completed:
        if COMPLETED_SAME_DAY_RE.search(line):
            total += 0
            count += 1
            continue
        m = COMPLETED_DURATION_RE.search(line)
        if m:
            total += int(m.group(1))
            count += 1
    if count == 0:
        return "-"
    avg = total / count
    return f"{avg:.1f} 영업일"


def _replace_header_block(lines: list[str], new_header: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line == HEADER_START:
            out.extend(new_header)
            i += 1
            while i < n and not lines[i].startswith("##"):
                i += 1
            out.append("")
            continue
        out.append(line)
        i += 1
    return out
