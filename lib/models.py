from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class TaskBlock:
    top_text: str
    children: list[str] = field(default_factory=list)
    is_completed: bool = False
    is_dropped_immediate: bool = False
    has_archive_marker: bool = False
    has_long_marker: bool = False
    carryover_days: int = 0
    origin_date: Optional[date] = None

    def render_top_line(self, checkbox: str = "[ ]") -> str:
        return f"- {checkbox} {self.top_text}"

    def render_block(self, checkbox: str = "[ ]") -> list[str]:
        return [self.render_top_line(checkbox)] + list(self.children)


@dataclass
class DailyNoteParsed:
    note_date: date
    active_blocks: list[TaskBlock] = field(default_factory=list)
    carryover_blocks: list[TaskBlock] = field(default_factory=list)
    memo_lines: list[str] = field(default_factory=list)


@dataclass
class Events:
    completed: list[TaskBlock] = field(default_factory=list)
    dropped: list[TaskBlock] = field(default_factory=list)
    archived: list[TaskBlock] = field(default_factory=list)
    carrying_over: list[TaskBlock] = field(default_factory=list)
