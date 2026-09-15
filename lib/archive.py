from datetime import date
from pathlib import Path

from .config import archive_path
from .models import TaskBlock


def ensure_archive() -> Path:
    path = archive_path()
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        "---",
        "tags: [archive]",
        "---",
        "",
        "# 보관함",
        "",
        "> 지금은 아니지만 나중에 참고할 할일들.",
        "> 살리려면 항목 텍스트만 복사해서 오늘 데일리의 `할일` 섹션에 붙여넣기.",
        "",
    ]
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def append_archived(archive_path_: Path, event_date: date, block: TaskBlock) -> None:
    ym = f"{event_date.year:04d}-{event_date.month:02d}"
    group_header = f"## {ym}"
    lines = archive_path_.read_text(encoding="utf-8").splitlines()

    group_end_idx = _find_group_end(lines, group_header)
    md = f"{event_date.month:02d}-{event_date.day:02d}"
    entry = [f"- [ ] {block.top_text} (보관: {md})"]
    for child in block.children:
        entry.append(child)

    if group_end_idx is None:
        while lines and lines[-1].strip() == "":
            lines.pop()
        lines.append("")
        lines.append(group_header)
        lines.extend(entry)
    else:
        for i, e in enumerate(entry):
            lines.insert(group_end_idx + i, e)
        next_after = group_end_idx + len(entry)
        if next_after < len(lines) and lines[next_after].startswith("## "):
            lines.insert(next_after, "")

    archive_path_.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_group_end(lines: list[str], group_header: str):
    in_group = False
    last_content_idx = None
    for i, line in enumerate(lines):
        if line == group_header:
            in_group = True
            last_content_idx = i
            continue
        if in_group and line.startswith("## "):
            return last_content_idx + 1
        if in_group and line.strip() != "":
            last_content_idx = i
    if in_group:
        return (last_content_idx or 0) + 1
    return None
