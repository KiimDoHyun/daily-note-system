"""설치 환경 진단.

daily_note.py doctor 로 호출된다. 실행 환경(리포 위치, 환경 변수, 볼트 접근,
launchd 등록 여부, 최근 로그)을 훑어 문제 후보를 표시한다. 이 모듈은 볼트가
설정돼 있지 않아도 동작해야 하므로 lib.config 를 참조하지 않는다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROTECTED_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Library" / "Mobile Documents",
]

DEFAULT_LOG_DIR = Path.home() / ".local" / "state" / "daily-note"


def run_doctor() -> int:
    """진단 리포트를 stdout 으로 출력. 문제가 있으면 1, 없으면 0 반환."""
    print("===== Daily Note 설치 환경 진단 =====\n")
    problems: list[str] = []

    _section("리포 위치")
    repo_root = Path(__file__).resolve().parent.parent
    protected = _protected_base(repo_root)
    if protected is not None:
        _fail(f"리포가 잠긴 폴더 안에 있음: {repo_root}")
        _hint(f"잠긴 폴더: {protected}")
        _hint("macOS 부팅 직후 자동 실행이 실패할 수 있습니다.")
        _hint(f'mv "{repo_root}" "$HOME/daily-note-system"')
        problems.append("repo_in_protected_dir")
    else:
        _ok(f"안전한 위치: {repo_root}")

    _section("파이썬")
    print(f"  실행 파일: {sys.executable}")
    print(f"  버전: {sys.version.split()[0]}")
    if sys.executable != "/usr/bin/python3":
        _warn("launchd 는 보통 /usr/bin/python3 을 호출합니다. 다른 파이썬을 쓰는 경우 plist 를 맞춰야 합니다.")

    _section("환경 변수")
    vault_env = os.environ.get("DAILY_NOTE_VAULT_ROOT")
    log_env = os.environ.get("DAILY_NOTE_LOG_DIR")
    if vault_env:
        _ok(f"DAILY_NOTE_VAULT_ROOT = {vault_env}")
    else:
        _fail("DAILY_NOTE_VAULT_ROOT 미설정")
        _hint("install.sh 로 설치하거나 plist 의 EnvironmentVariables 에 추가하세요.")
        problems.append("vault_env_missing")
    if log_env:
        print(f"  DAILY_NOTE_LOG_DIR = {log_env}")
    else:
        print(f"  DAILY_NOTE_LOG_DIR = (기본값 {DEFAULT_LOG_DIR})")

    _section("볼트 접근")
    if vault_env:
        vault_path = Path(vault_env).expanduser()
        if not vault_path.exists():
            _fail(f"볼트 경로 없음: {vault_path}")
            problems.append("vault_missing")
        elif not os.access(vault_path, os.R_OK | os.W_OK):
            _fail(f"볼트 읽기/쓰기 불가: {vault_path}")
            _hint("macOS 문지기(TCC) 가 접근을 막고 있을 수 있습니다.")
            _hint("시스템 설정 → 개인정보 보호 → 전체 디스크 접근 목록에 파이썬이 있는지 확인하세요.")
            problems.append("vault_permission_denied")
        else:
            _ok(f"읽기/쓰기 가능: {vault_path}")
    else:
        _warn("DAILY_NOTE_VAULT_ROOT 가 없어 확인 생략")

    _section("로그 디렉토리")
    log_dir = Path(log_env).expanduser() if log_env else DEFAULT_LOG_DIR
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        probe = log_dir / ".doctor_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        _ok(f"쓰기 가능: {log_dir}")
    except Exception as exc:
        _fail(f"쓰기 실패: {log_dir} ({exc})")
        problems.append("log_dir_unwritable")

    _section("LaunchAgent 등록")
    matches = _list_daily_note_agents()
    if matches:
        for m in matches:
            _ok(m)
    else:
        _warn("daily-note 라벨을 launchctl list 에서 찾지 못했습니다.")
        _hint("install.sh 로 재설치하거나 plist 를 수동 로드하세요.")

    _section("최근 로그")
    _report_log_file(log_dir / "daily-note.log", "표준 출력 로그")
    _report_log_file(log_dir / "daily-note-error.log", "에러 로그")
    _report_log_file(log_dir / "supervisor.log", "감독 로그")
    _report_log_file(log_dir / "last-failure.txt", "최근 실패 진단")

    print()
    if problems:
        _fail(f"진단 완료. 문제 {len(problems)}건 발견.")
        return 1
    _ok("진단 완료. 문제 없음.")
    return 0


def _protected_base(path: Path) -> Path | None:
    try:
        resolved = path.resolve()
    except OSError:
        return None
    for base in PROTECTED_DIRS:
        try:
            base_resolved = base.resolve()
        except OSError:
            continue
        try:
            resolved.relative_to(base_resolved)
            return base_resolved
        except ValueError:
            continue
    return None


def _list_daily_note_agents() -> list[str]:
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return []
    matches: list[str] = []
    for line in result.stdout.splitlines():
        if "daily-note" in line.lower() or "obsidian-daily" in line.lower():
            matches.append(line.strip())
    return matches


def _report_log_file(path: Path, label: str) -> None:
    if not path.exists():
        print(f"  {label}: (없음)")
        return
    size = path.stat().st_size
    mtime = path.stat().st_mtime
    from datetime import datetime
    ts = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(f"  {label}: {path} ({size}B, {ts})")


def _section(title: str) -> None:
    print(f"\n[{title}]")


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _hint(msg: str) -> None:
    print(f"        → {msg}")
