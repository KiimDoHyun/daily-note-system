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
├── install.sh              # 설치 자동화 (위치 검사 포함)
├── lib/                    # 라이브러리 모듈
├── launchd/
│   ├── com.example.daily-note.plist.template
│   └── run-with-retry.sh   # 부팅 시 감독 스크립트 (재시도 + 실패 알림)
├── tests/                  # unittest 테스트
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

## ⚠️ 설치 전 반드시 읽을 것 — 클론 위치

**다음 폴더 안에는 클론하지 마세요.**

- `~/Documents/`
- `~/Desktop/`
- `~/Downloads/`
- 아이클라우드 드라이브 폴더 (`~/Library/Mobile Documents/`)

macOS의 파일 접근 통제 시스템(TCC) 이 이 폴더들을 잠급니다. 리포가 이 안에 있으면 **macOS 부팅 직후 launchd 가 파이썬 스크립트를 실행하려다 "Operation not permitted" 로 튕깁니다.** 사용자가 로그인해서 수동으로 실행하면 되지만, 매일 아침 자동으로 도는 이 프로젝트의 목적을 잃습니다.

**권장 위치**: `~/daily-note-system/` (홈 폴더 바로 아래)

`install.sh` 는 실행 위치를 검사해서 잠긴 폴더 안이면 즉시 중단합니다. 상세 배경은 [CLAUDE.md](CLAUDE.md) 의 "왜 홈 폴더에 놓아야 하나" 참고.

## 설치

### 요구사항

- macOS (Linux 는 launchd 대신 systemd/cron 필요, 미검증)
- Python 3.9 이상 (macOS 시스템 `/usr/bin/python3` 사용 가능)
- 옵시디언 볼트 또는 임의의 마크다운 노트 폴더

### 절차

1. 저장소 클론 — **반드시 홈 폴더 바로 아래**

   ```bash
   git clone https://github.com/KiimDoHyun/daily-note-system.git ~/daily-note-system
   cd ~/daily-note-system
   ```

2. 설치 스크립트 실행

   ```bash
   ./install.sh
   ```

   실행 위치 검사 → 볼트 경로 확인 → plist 생성 → launchd 로드 까지 자동으로 처리.
   볼트 경로를 미리 지정하려면:

   ```bash
   ./install.sh "$HOME/Documents/Obsidian Vault"
   ```

3. 전체 디스크 접근 권한 부여 (**필수**)

   - 시스템 설정 → 개인정보 보호 및 보안 → 전체 디스크 접근 권한
   - `+` 클릭 → `Cmd+Shift+G` → `/usr/bin/python3` 추가 후 토글 켬

4. 즉시 시험 실행

   ```bash
   launchctl kickstart -k "gui/$(id -u)/com.example.daily-note"
   ```

5. 설치 상태 확인

   ```bash
   /usr/bin/python3 ~/daily-note-system/daily_note.py doctor
   ```

## 부팅 시 자동 실행이 실패한다면

부팅 직후 몇 초 동안 macOS 문지기 데몬이 완전히 준비되지 않아 실행이 튕길 수 있습니다. `launchd/run-with-retry.sh` 감독 스크립트가 자동으로 대응합니다.

1. 사용자 세션 앵커(Finder) 가 뜰 때까지 최대 30초 대기
2. 파이썬 실행 실패 시 5초 간격으로 최대 10회 재시도
3. 그래도 실패하면 **진단 파일을 남기고 알림 표시**
   - 진단 파일: `~/.local/state/daily-note/last-failure.txt`
   - 알림에 진단 파일 경로가 함께 표시됨

알림을 받은 뒤 대응 순서:

1. 진단 파일을 열어 실패 지점 확인
2. `doctor` 명령으로 환경 재확인
3. 세션이 살아있는 상태라면 즉시 재시도:
   ```bash
   launchctl kickstart -k "gui/$(id -u)/com.example.daily-note"
   ```

첫 실패 알림이 조용히 사라지면 macOS 알림 권한이 필요할 수 있습니다. 알림 센터 설정에서 "스크립트 편집기" 항목이 허용 상태인지 확인하세요.

## 사용법

### CLI 서브커맨드

```bash
python3 daily_note.py create                  # 오늘 데일리 노트 생성 (launchd 기본)
python3 daily_note.py dry-run                 # 파일 수정 없이 예상 동작만 출력
python3 daily_note.py force 2026-09-15        # 특정 날짜 강제 재생성
python3 daily_note.py recompute 2026-09       # 특정 월 종합 상단 요약 재계산
python3 daily_note.py doctor                  # 설치 환경 진단 리포트
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
| `DAILY_NOTE_LABEL` | X | launchd Label (기본 `com.example.daily-note`) |
| `DAILY_NOTE_MAX_ATTEMPTS` | X | 감독 스크립트 재시도 횟수 (기본 10) |
| `DAILY_NOTE_RETRY_INTERVAL` | X | 재시도 간격 초 (기본 5) |
| `DAILY_NOTE_FINDER_WAIT` | X | Finder 대기 초 (기본 30) |
| `DAILY_NOTE_PYTHON` | X | 파이썬 실행 파일 경로 (기본 `/usr/bin/python3`) |

## 라이센스

MIT
