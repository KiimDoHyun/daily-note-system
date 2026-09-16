#!/bin/bash
# 설치 스크립트
#
# 이 리포지토리가 놓인 위치가 macOS 문지기(TCC) 로 잠긴 폴더 안이면
# 부팅 직후 자동 실행이 실패한다. 그 상황에서는 설치를 즉시 중단해서
# 사용자가 함정에 빠지지 않도록 한다.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- 위치 검사 -------------------------------------------------------------
PROTECTED_DIRS=(
    "$HOME/Documents"
    "$HOME/Desktop"
    "$HOME/Downloads"
    "$HOME/Library/Mobile Documents"  # iCloud Drive
)

for base in "${PROTECTED_DIRS[@]}"; do
    case "$SCRIPT_DIR/" in
        "$base"/*)
            cat >&2 <<EOF
❌ 설치 위치가 macOS 문지기(TCC)로 잠긴 폴더 안입니다.

  현재 위치: $SCRIPT_DIR
  잠긴 폴더: $base

이 상태로 설치하면 macOS 부팅 직후 자동 실행이 "Operation not permitted"
로 실패합니다. 리포를 홈 폴더 바로 아래로 옮긴 뒤 다시 시도하세요.

  mv "$SCRIPT_DIR" "\$HOME/daily-note-system"
  cd "\$HOME/daily-note-system"
  ./install.sh

배경 설명은 docs/design.md 또는 CLAUDE.md 를 참고하세요.
EOF
            exit 1
            ;;
    esac
done

# ---- 볼트 경로 확인 --------------------------------------------------------
VAULT_ROOT="${1:-${DAILY_NOTE_VAULT_ROOT:-}}"
if [ -z "$VAULT_ROOT" ]; then
    echo "옵시디언 볼트 경로를 입력하세요."
    echo "예: $HOME/Documents/Obsidian Vault"
    read -r -p "볼트 경로: " VAULT_ROOT
fi
VAULT_ROOT="${VAULT_ROOT/#\~/$HOME}"

if [ ! -d "$VAULT_ROOT" ]; then
    echo "❌ 볼트 경로가 존재하지 않습니다: $VAULT_ROOT" >&2
    exit 1
fi

# ---- 파라미터 --------------------------------------------------------------
LABEL="${DAILY_NOTE_LABEL:-com.example.daily-note}"
LOG_DIR="${DAILY_NOTE_LOG_DIR:-$HOME/.local/state/daily-note}"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
TEMPLATE_PATH="$SCRIPT_DIR/launchd/com.example.daily-note.plist.template"

if [ ! -f "$TEMPLATE_PATH" ]; then
    echo "❌ plist 템플릿을 찾지 못했습니다: $TEMPLATE_PATH" >&2
    exit 1
fi

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$PLIST_PATH")"

# ---- plist 생성 ------------------------------------------------------------
sed \
    -e "s#{{LABEL}}#${LABEL}#g" \
    -e "s#{{REPO_ROOT}}#${SCRIPT_DIR}#g" \
    -e "s#{{VAULT_ROOT}}#${VAULT_ROOT}#g" \
    -e "s#{{LOG_DIR}}#${LOG_DIR}#g" \
    "$TEMPLATE_PATH" > "$PLIST_PATH"

# ---- launchd 등록 ----------------------------------------------------------
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

# ---- 안내 ------------------------------------------------------------------
cat <<EOF

✅ 설치 완료

  리포 위치      : $SCRIPT_DIR
  볼트           : $VAULT_ROOT
  로그 디렉토리  : $LOG_DIR
  자동 실행 설정 : $PLIST_PATH
  Label          : $LABEL

다음 단계

  1. macOS 문지기 권한 부여 (필수)

     시스템 설정 → 개인정보 보호 및 보안 → 전체 디스크 접근 권한
     '+' → Cmd+Shift+G → /usr/bin/python3 추가 후 토글 켜기

  2. 즉시 시험 실행

     launchctl kickstart -k "gui/\$(id -u)/$LABEL"

  3. 문제 발생 시 진단 리포트

     /usr/bin/python3 $SCRIPT_DIR/daily_note.py doctor

  4. 최종 실패가 발생하면 아래 파일에 진단 스냅샷이 저장됩니다

     $LOG_DIR/last-failure.txt

EOF
