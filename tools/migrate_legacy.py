#!/usr/bin/env python3
import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.config import (
    FOOTER,
    NOTES_ROOT,
    SECTION_CARRYOVER_NEW,
    SECTION_CARRYOVER_OLD,
    SECTION_TODO_NEW,
    SECTION_TODO_OLD,
    monthly_drop_wikilink,
    monthly_summary_wikilink,
)

DAILY_NAME_RE = re.compile(r"^📅 (\d{4}-\d{2}-\d{2})\.md$")
YM_DIR_RE = re.compile(r"^\d{4}-\d{2}$")
FOOTER_MARKER = "📎 마커"
FOOTER_START_MARKER_RE = re.compile(r"^---\s*$")


def find_daily_notes(root: Path):
    notes = []
    if not root.exists():
        return notes
    for ym_dir in sorted(root.iterdir()):
        if not ym_dir.is_dir() or not YM_DIR_RE.match(ym_dir.name):
            continue
        for wk_dir in sorted(ym_dir.iterdir()):
            if not wk_dir.is_dir() or not wk_dir.name.endswith("주차"):
                continue
            for f in sorted(wk_dir.iterdir()):
                m = DAILY_NAME_RE.match(f.name)
                if m:
                    d = date.fromisoformat(m.group(1))
                    notes.append((d, f))
    return notes


def compute_changes(text: str, note_date: date, add_footer: bool, replace_footer: bool = False):
    new = text
    changes = []

    if SECTION_TODO_OLD in new:
        new = new.replace(SECTION_TODO_OLD, SECTION_TODO_NEW)
        changes.append("섹션명: 오늘의 목표 → 할일")
    if SECTION_CARRYOVER_OLD in new:
        new = new.replace(SECTION_CARRYOVER_OLD, SECTION_CARRYOVER_NEW)
        changes.append("섹션명: 미완료 이월 → 이월된 할일")

    if not add_footer:
        return new, changes

    footer = FOOTER.format(
        summary_link=monthly_summary_wikilink(note_date),
        drop_link=monthly_drop_wikilink(note_date),
    )
    has_footer = FOOTER_MARKER in new

    if has_footer and replace_footer:
        new = _strip_existing_footer(new)
        new = _append_footer(new, footer)
        changes.append("하단 안내 블록 갱신")
    elif not has_footer:
        new = _append_footer(new, footer)
        changes.append("하단 안내 블록 추가")

    return new, changes


def _append_footer(text: str, footer: str) -> str:
    if not text.endswith("\n"):
        text += "\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + footer + "\n"


def _strip_existing_footer(text: str) -> str:
    lines = text.splitlines()
    footer_start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---" and any(
            FOOTER_MARKER in lines[j] for j in range(i + 1, min(i + 8, len(lines)))
        ):
            footer_start_idx = i
            break
    if footer_start_idx is None:
        return text
    while footer_start_idx > 0 and lines[footer_start_idx - 1].strip() == "":
        footer_start_idx -= 1
    trimmed = lines[:footer_start_idx]
    while trimmed and trimmed[-1].strip() == "":
        trimmed.pop()
    return "\n".join(trimmed) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="옛 규격 데일리 노트를 새 섹션명·안내 블록으로 마이그레이션"
    )
    parser.add_argument("--apply", action="store_true", help="실제 파일 수정 (기본은 dry-run)")
    parser.add_argument("--no-footer", action="store_true", help="섹션명만 변경, 하단 안내 안 붙임")
    parser.add_argument("--replace-footer", action="store_true", help="기존 안내가 있어도 새 포맷으로 재작성")
    args = parser.parse_args()

    add_footer = not args.no_footer
    notes = find_daily_notes(NOTES_ROOT)
    print(f"NOTES_ROOT: {NOTES_ROOT}")
    print(f"발견된 데일리 노트: {len(notes)}개\n")

    changed = []
    for d, path in notes:
        original = path.read_text(encoding="utf-8")
        new_text, changes = compute_changes(original, d, add_footer, args.replace_footer)
        if changes:
            changed.append((path, changes))
            if args.apply:
                path.write_text(new_text, encoding="utf-8")

    print(f"변경 대상: {len(changed)}개\n")
    for path, chg_list in changed:
        rel = path.relative_to(NOTES_ROOT)
        print(f"  {rel}")
        for c in chg_list:
            print(f"    - {c}")

    if args.apply:
        print(f"\n✅ {len(changed)}개 파일 수정 완료")
    else:
        print("\ndry-run 모드. 실제 반영은 --apply 옵션 추가.")


if __name__ == "__main__":
    main()
