# daily-note-system

옵시디언 볼트에서 하루 하나씩 자동 생성되는 데일리 노트에 **이월·완료·드롭·보관** 흐름을 얹은 자동화 시스템.

사용자는 데일리 노트에 할일과 메모만 적으면, 스크립트가 매일 아침 다음을 자동 처리한다.

- 어제 미완료 항목을 오늘 노트의 "이월된 할일" 로 옮김 (영업일 카운터·시작일 표기 포함)
- 3~4일 이월된 항목에 🟠/🔴 시각 경고 부착
- 5영업일 이상 이월된 항목은 자동으로 월간 드롭 문서로 이동
- `#보관` 마커가 붙은 항목은 상시 보관함 문서로 이동
- `[-]` 마커가 붙은 항목은 즉시 드롭
- 완료·드롭·보관 이벤트를 월간 종합 문서에 자동 기록·집계

옵시디언 앱에 종속되지 않는다. 마크다운 파일과 폴더 구조에만 의존하므로 다른 마크다운 에디터에서도 열람·편집 가능. wikilink(`[[...]]`) 하나만 옵시디언 전용 문법.

## 주요 개념

| 상태 | 표기 | 의미 |
|---|---|---|
| 활성 | `- [ ] 할일` | 오늘 새로 추가한 항목 |
| 이월 (1~2일) | `- [ ] 할일 (N일째 이월, MM-DD~)` | 어제 못 끝내고 넘어온 항목 |
| 보류 (3~4일) | `🟠/🔴 - [ ] 할일 ... (드롭 예정입니다)` | 곧 자동 드롭될 항목 |
| 완료 | `- [x] 할일` | 사용자가 체크 → 월간 종합에 로그 |
| 드롭 | 월간 드롭 문서로 이동 | 5일 초과 또는 `[-]` 마커 |
| 보관 | 보관함 문서로 이동 | `#보관` 마커 |

상세는 [docs/design.md](docs/design.md) 참고.

## 폴더 구조

이 저장소:

```
daily-note-system/
├── daily_note.py           # CLI 진입점
├── lib/                    # 라이브러리 모듈
├── tests/                  # unittest 테스트
├── launchd/                # macOS launchd plist 템플릿
└── docs/design.md          # 설계 문서
```

배포 시 볼트 안:

```
YourVault/
└── Notes/
    ├── 보관함.md
    ├── 2026-09/
    │   ├── 2026-09 종합.md
    │   ├── 2026-09 드롭.md
    │   ├── 1주차/
    │   │   └── 📅 2026-09-01.md
    │   └── 2주차/...
    └── 2026-10/...
```

## 설치

### 요구사항

- macOS (Linux 는 launchd 대신 systemd/cron 필요, 미검증)
- Python 3.9 이상 (macOS 시스템 `/usr/bin/python3` 사용 가능)
- 옵시디언 볼트 또는 임의의 마크다운 노트 폴더

### 절차

1. 저장소 클론
   ```bash
   git clone https://github.com/KiimDoHyun/daily-note-system.git ~/daily-note-system
   ```

2. 로그 디렉터리 생성
   ```bash
   mkdir -p ~/.local/state/daily-note
   ```

3. 동작 확인
   ```bash
   cd ~/daily-note-system
   DAILY_NOTE_VAULT_ROOT="/path/to/your/Obsidian Vault" \
     /usr/bin/python3 daily_note.py dry-run
   ```

4. launchd plist 생성
   ```bash
   sed \
     -e "s#{{REPO_ROOT}}#$HOME/daily-note-system#g" \
     -e "s#{{VAULT_ROOT}}#$HOME/Documents/Obsidian Vault#g" \
     -e "s#{{LOG_DIR}}#$HOME/.local/state/daily-note#g" \
     launchd/com.example.daily-note.plist.template \
     > ~/Library/LaunchAgents/com.example.daily-note.plist
   ```

5. 전체 디스크 접근 권한 부여
   - 시스템 설정 → 개인정보 보호 및 보안 → 전체 디스크 접근
   - `+` 클릭 → `Cmd+Shift+G` → `/usr/bin/python3` 추가 후 토글 켬
   - 볼트가 `~/Documents/` 안에 있을 때 필수

6. launchd 로드
   ```bash
   launchctl load ~/Library/LaunchAgents/com.example.daily-note.plist
   launchctl kickstart -k "gui/$(id -u)/com.example.daily-note"
   ```

## 사용법

### CLI 서브커맨드

```bash
python3 daily_note.py create                  # 오늘 데일리 노트 생성 (launchd 기본)
python3 daily_note.py dry-run                 # 파일 수정 없이 예상 동작만 출력
python3 daily_note.py force 2026-09-15        # 특정 날짜 강제 재생성
python3 daily_note.py recompute 2026-09       # 특정 월 종합 상단 요약 재계산
```

`--today YYYY-MM-DD` 옵션으로 "오늘" 을 임의 날짜로 오버라이드 가능. 테스트·과거 노트 재생성에 유용.

### 마커

데일리 노트의 할일에 붙일 수 있는 마커:

- `#장기` — 5영업일 드롭 규칙 면제, 무한 이월
- `#보관` — 다음 날 노트 생성 시 보관함으로 이동
- `[-]` — 다음 날 노트 생성 시 즉시 드롭 (체크박스 자리에 `-`)

### 데일리 노트 섹션

- `## 📌 할일` — 오늘 새로 시작할 항목
- `## ✅ 이월된 할일` — 자동 생성, 어제부터 넘어온 항목
- `## 💬 메모` — 자유 서술, 이월 대상 아님

하위 항목·메모는 반드시 인덴트(탭 또는 공백) 후 작성. 인덴트 없으면 새 최상위 블록으로 인식됨.

## 테스트

```bash
cd daily-note-system
/usr/bin/python3 -m unittest discover tests
```

87 개 테스트 (단위 + 통합 19 시나리오) 자동 실행. 테스트는 임시 디렉터리를 사용하므로 실제 볼트를 건드리지 않는다.

## 환경 변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `DAILY_NOTE_VAULT_ROOT` | O | 볼트 루트 절대 경로 |
| `DAILY_NOTE_NOTES_SUBDIR` | X | 볼트 안 노트 하위 폴더 (기본 `Notes`) |
| `DAILY_NOTE_LOG_DIR` | X | 로그 디렉터리 (기본 `~/.local/state/daily-note`) |

## 라이센스

MIT
