#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="daily_note")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create", help="오늘 데일리 노트 생성")
    p_create.add_argument("--today", type=_parse_date)
    p_create.add_argument("--dry-run", action="store_true")

    p_dry = sub.add_parser("dry-run", help="파일 수정 없이 예상 동작만 출력")
    p_dry.add_argument("--today", type=_parse_date)

    p_recompute = sub.add_parser("recompute", help="특정 월 종합 상단 요약 재계산")
    p_recompute.add_argument("month", help="YYYY-MM")

    p_force = sub.add_parser("force", help="특정 날짜 데일리 노트 강제 재생성")
    p_force.add_argument("date", help="YYYY-MM-DD")

    sub.add_parser("doctor", help="설치 환경 진단 리포트 출력")

    args = parser.parse_args(argv)

    # doctor 는 볼트 설정 없이도 돌아야 하므로 config 를 건드리지 않는다.
    if args.cmd == "doctor":
        from lib.doctor import run_doctor
        return run_doctor()

    # 나머지 명령은 lib.config 가 필요하다. 여기서 import 하면
    # DAILY_NOTE_VAULT_ROOT 미설정 시 이 시점에 실패하므로 진단이 쉬워진다.
    from lib.orchestrator import run_create, run_force, run_recompute

    try:
        if args.cmd == "create":
            today = args.today or date.today()
            result = run_create(today, dry_run=args.dry_run)
            _report(result)
        elif args.cmd == "dry-run":
            today = args.today or date.today()
            result = run_create(today, dry_run=True)
            _report(result)
        elif args.cmd == "recompute":
            month = _parse_month(args.month)
            path = run_recompute(month)
            _log(f"[{month.strftime('%Y-%m')}] 종합 상단 요약 재계산 완료: {path}")
        elif args.cmd == "force":
            target = _parse_date(args.date)
            result = run_force(target)
            _report(result)
        return 0
    except Exception as exc:
        _log_error(exc)
        _notify_failure(str(exc))
        return 1


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_month(s: str) -> date:
    return datetime.strptime(s + "-01", "%Y-%m-%d").date()


def _report(result: RunResult) -> None:
    if result.status == "skipped_weekend":
        _log(f"[{result.today.isoformat()}] 주말, 스킵")
        return
    if result.status == "skipped_exists":
        _log(f"[{result.today.isoformat()}] 이미 존재, 스킵")
        return
    if result.status == "dry_run":
        _log_dry_run(result)
        return

    events = result.events
    summary = (
        f"[{result.today.isoformat()}] 데일리 노트 생성 완료\n"
        f"  이월: {len(events.carrying_over)}건\n"
        f"  완료: {len(events.completed)}건\n"
        f"  드롭: {len(events.dropped)}건\n"
        f"  보관: {len(events.archived)}건"
    )
    _log(summary)
    _notify_success(result)


def _log_dry_run(result: RunResult) -> None:
    events = result.events
    lines = [
        f"[dry-run] 오늘 = {result.today.isoformat()}",
        f"  어제 = {result.prev_date}",
        f"  이월 예정: {len(events.carrying_over)}건",
        f"  완료 이벤트: {len(events.completed)}건",
        f"  드롭 이벤트: {len(events.dropped)}건",
        f"  보관 이벤트: {len(events.archived)}건",
    ]
    for block in events.carrying_over:
        lines.append(f"    이월: {block.top_text} ({block.carryover_days}일째)")
    for block in events.completed:
        lines.append(f"    완료: {block.top_text}")
    for block in events.dropped:
        lines.append(f"    드롭: {block.top_text}")
    for block in events.archived:
        lines.append(f"    보관: {block.top_text}")
    _log("\n".join(lines))


def _log(message: str) -> None:
    print(message)
    try:
        from lib.config import LOG_PATH
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def _log_error(exc: Exception) -> None:
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(trace, file=sys.stderr)
    try:
        from lib.config import ERROR_LOG_PATH
        ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(trace + "\n")
    except Exception:
        pass


def _notify_success(result: RunResult) -> None:
    events = result.events
    body = (
        f"이월 {len(events.carrying_over)} / 완료 {len(events.completed)} / "
        f"드롭 {len(events.dropped)} / 보관 {len(events.archived)}"
    )
    _osascript_notify(f"오늘의 Daily Note가 생성되었습니다\\n{body}", "Obsidian")


def _notify_failure(message: str) -> None:
    _osascript_notify(f"실패: {message}", "Obsidian Daily Note 오류")


def _osascript_notify(message: str, title: str) -> None:
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"',
            ],
            check=False,
            timeout=5,
        )
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
