import os
from pathlib import Path


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"환경 변수 {name} 가 설정되지 않았습니다.\n"
            "README 의 '설치' 섹션을 참고해 launchd plist 또는 셸에서 export 하세요."
        )
    return value


VAULT_ROOT = Path(_require_env("DAILY_NOTE_VAULT_ROOT")).expanduser()
NOTES_ROOT = VAULT_ROOT / os.environ.get("DAILY_NOTE_NOTES_SUBDIR", "Notes")

_default_log_dir = Path.home() / ".local" / "state" / "daily-note"
LOG_DIR = Path(os.environ.get("DAILY_NOTE_LOG_DIR", str(_default_log_dir))).expanduser()
LOG_PATH = LOG_DIR / "daily-note.log"
ERROR_LOG_PATH = LOG_DIR / "daily-note-error.log"

SECTION_TODO_NEW = "## 📌 할일"
SECTION_TODO_OLD = "## 📌 오늘의 목표"
SECTION_CARRYOVER_NEW = "## ✅ 이월된 할일"
SECTION_CARRYOVER_OLD = "## ✅ 미완료 이월"
SECTION_MEMO = "## 💬 메모"

TODO_SECTION_HEADERS = (SECTION_TODO_NEW, SECTION_TODO_OLD)
CARRYOVER_SECTION_HEADERS = (SECTION_CARRYOVER_NEW, SECTION_CARRYOVER_OLD)

MARKER_ARCHIVE = "#보관"
MARKER_LONG = "#장기"

WARN_ORANGE = "🟠"
WARN_RED = "🔴"
DROP_WARNING_SUFFIX = "(드롭 예정입니다)"

DROP_THRESHOLD_DAYS = 5
WARN_ORANGE_DAY = 3
WARN_RED_DAY = 4

FOOTER = """---
📎 마커: `#장기`(드롭 면제) · `#보관`(보관함 이동) · `[-]`(즉시 드롭)
📎 하위 항목·메모는 반드시 들여쓰기(탭 또는 공백) 후 작성.
📂 {summary_link} · {drop_link} · [[보관함]]"""


def daily_note_dir(d) -> Path:
    from .calendar_utils import week_of_month
    ym = f"{d.year:04d}-{d.month:02d}"
    wk = week_of_month(d)
    return NOTES_ROOT / ym / f"{wk}주차"


def daily_note_path(d) -> Path:
    return daily_note_dir(d) / f"📅 {d.isoformat()}.md"


def monthly_summary_path(d) -> Path:
    ym = f"{d.year:04d}-{d.month:02d}"
    return NOTES_ROOT / ym / f"{ym} 종합.md"


def monthly_drop_path(d) -> Path:
    ym = f"{d.year:04d}-{d.month:02d}"
    return NOTES_ROOT / ym / f"{ym} 드롭.md"


def archive_path() -> Path:
    return NOTES_ROOT / "보관함.md"


def monthly_summary_wikilink(d) -> str:
    ym = f"{d.year:04d}-{d.month:02d}"
    return f"[[{ym} 종합]]"


def monthly_drop_wikilink(d) -> str:
    ym = f"{d.year:04d}-{d.month:02d}"
    return f"[[{ym} 드롭]]"
