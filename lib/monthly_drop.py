from datetime import date
from pathlib import Path

from .config import monthly_drop_path
from .models import TaskBlock


def ensure_drop(month: date) -> Path:
    path = monthly_drop_path(month)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    ym = f"{month.year:04d}-{month.month:02d}"
    parts = [
        "---",
        f"tags: [monthly-drop, {ym}]",
        "---",
        "",
        f"# {ym} 드롭된 업무",
        "",
        "> 5일 초과 이월 또는 즉시 드롭(`[-]`) 처리된 항목.",
        "> 살리려면 항목 텍스트만 복사해서 오늘 데일리의 `할일` 섹션에 붙여넣기 (이월 태그 제거).",
        "",
    ]
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def append_dropped(drop_path: Path, event_date: date, block: TaskBlock) -> None:
    lines = drop_path.read_text(encoding="utf-8").splitlines()
    while lines and lines[-1].strip() == "":
        lines.pop()
    has_prior_entry = any(line.startswith("- [-] ") for line in lines)
    if not has_prior_entry:
        lines.append("")
    lines.append(_render_drop_top(block, event_date))
    for child in block.children:
        lines.append(child)
    drop_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_drop_top(block: TaskBlock, event_date: date) -> str:
    md = f"{event_date.month:02d}-{event_date.day:02d}"
    if block.is_dropped_immediate:
        suffix = f"({md} 즉시 드롭)"
    elif block.origin_date is None:
        suffix = f"({md} 드롭, {block.carryover_days}영업일 이월 후)"
    else:
        origin = f"{block.origin_date.month:02d}-{block.origin_date.day:02d}"
        suffix = f"({origin} 시작, {md} 드롭, {block.carryover_days}영업일 이월)"
    return f"- [-] {block.top_text} {suffix}"
