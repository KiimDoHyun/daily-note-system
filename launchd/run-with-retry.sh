#!/bin/bash
# 감독 스크립트 (supervisor)
#
# launchd 가 RunAtLoad 로 이 스크립트를 호출한다. 부팅 직후 macOS TCC 데몬이
# 완전히 준비되기 전에 파이썬을 실행하면 잠긴 폴더 접근이 거절될 수 있어서,
# (1) 사용자 세션 앵커(Finder) 가 뜰 때까지 짧게 대기하고,
# (2) 파이썬 실행 실패 시 짧은 간격으로 여러 번 재시도하고,
# (3) 최종 실패 시 진단 파일을 남기고 알림을 띄운다.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${DAILY_NOTE_PYTHON:-/usr/bin/python3}"
LOG_DIR="${DAILY_NOTE_LOG_DIR:-$HOME/.local/state/daily-note}"
DIAG_FILE="$LOG_DIR/last-failure.txt"
SUPERVISOR_LOG="$LOG_DIR/supervisor.log"

MAX_ATTEMPTS="${DAILY_NOTE_MAX_ATTEMPTS:-10}"
RETRY_INTERVAL_SECONDS="${DAILY_NOTE_RETRY_INTERVAL:-5}"
FINDER_WAIT_SECONDS="${DAILY_NOTE_FINDER_WAIT:-30}"

mkdir -p "$LOG_DIR"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$SUPERVISOR_LOG"
}

log "supervisor 시작 (repo=$REPO_ROOT)"

# (1) 사용자 세션 앵커 대기.
# Finder 가 살아있으면 TCC 데몬도 준비된 상태로 간주한다.
for _ in $(seq 1 "$FINDER_WAIT_SECONDS"); do
    if pgrep -u "$USER" -x Finder >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! pgrep -u "$USER" -x Finder >/dev/null 2>&1; then
    log "Finder 확인 실패 ${FINDER_WAIT_SECONDS}초 초과. 계속 진행."
fi

# (2) 재시도 루프.
last_output=""
last_exit=0
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    if output="$("$PYTHON" "$REPO_ROOT/daily_note.py" create 2>&1)"; then
        log "attempt $attempt: 성공"
        printf '%s\n' "$output"
        exit 0
    fi
    last_exit=$?
    last_output="$output"
    log "attempt $attempt/$MAX_ATTEMPTS 실패 (exit=$last_exit): ${output:0:200}"
    if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
        sleep "$RETRY_INTERVAL_SECONDS"
    fi
done

# (3) 최종 실패. 진단 파일 작성.
{
    echo "===== Daily Note 자동 생성 실패 진단 ====="
    echo "시각: $(date)"
    echo "시도: ${MAX_ATTEMPTS}회 (간격 ${RETRY_INTERVAL_SECONDS}초)"
    echo "리포 위치: $REPO_ROOT"
    echo "파이썬: $PYTHON"
    echo
    echo "--- 스크립트 파일 접근 ---"
    ls -la "$REPO_ROOT/daily_note.py" 2>&1
    echo
    echo "--- 볼트 경로 접근 ---"
    if [ -n "${DAILY_NOTE_VAULT_ROOT:-}" ]; then
        ls -la "$DAILY_NOTE_VAULT_ROOT" 2>&1 | head -20
    else
        echo "(DAILY_NOTE_VAULT_ROOT 미설정)"
    fi
    echo
    echo "--- 로그 디렉토리 ---"
    ls -la "$LOG_DIR" 2>&1
    echo
    echo "--- 관련 환경 변수 ---"
    env | grep -E '^DAILY_NOTE_' || echo "(없음)"
    echo
    echo "--- 마지막 파이썬 출력 ---"
    printf '%s\n' "$last_output"
    echo
    echo "===== 대응 힌트 ====="
    echo "1. 리포가 잠긴 폴더(~/Documents, ~/Desktop, ~/Downloads) 안에 있으면 홈 폴더 밖으로 이동."
    echo "2. 시스템 설정 → 개인정보 보호 → 전체 디스크 접근 목록에 $PYTHON 이 있는지 확인."
    echo "3. 세션이 살아있는 상태라면: launchctl kickstart -k gui/\$(id -u)/<Label>"
} > "$DIAG_FILE" 2>&1

log "최종 실패. 진단 파일: $DIAG_FILE"

# 알림 (osascript). 첫 사용 시 macOS 알림 권한이 필요할 수 있음.
/usr/bin/osascript \
    -e "display notification \"${MAX_ATTEMPTS}회 재시도 실패. 진단: $DIAG_FILE\" with title \"Daily Note 자동 생성 실패\" sound name \"Basso\"" \
    >/dev/null 2>&1 || log "osascript 알림 호출 실패"

exit 1
