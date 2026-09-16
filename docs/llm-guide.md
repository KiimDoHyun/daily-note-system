# LLM 작업 가이드

이 문서는 이 리포지토리에서 코드를 읽거나 수정하는 LLM(Claude 등) 이 작업 전에 읽어야 할 안내입니다. 사람용 개요는 [../README.md](../README.md), 설계 상세는 [design.md](design.md) 를 봅니다.

---

## 1. 이 프로젝트가 하는 일

옵시디언 볼트에 매일 하나씩 데일리 노트를 생성하고, 어제 노트의 미완료 항목을 오늘로 이월시키며, 오래된 항목은 자동 드롭·보관하는 macOS 자동화 시스템입니다.

- 진입점: `daily_note.py` (CLI)
- 실행 트리거: macOS launchd 가 로그인 시 자동 실행 (`launchd/com.example.daily-note.plist.template`)
- 부팅 직후 실패 방어: `launchd/run-with-retry.sh` 가 파이썬을 감독하며 재시도
- 설치: `install.sh` 가 위치 검사 → plist 생성 → launchd 로드까지 처리
- 진단: `daily_note.py doctor`

옵시디언에 종속되지 않습니다. 마크다운 파일과 폴더 구조만 다룹니다. `[[wikilink]]` 하나만 옵시디언 전용.

---

## 2. 아키텍처 요약

```
daily_note.py                # CLI 파싱 + main()
└─ lib/
   ├─ config.py              # 경로·상수·환경 변수 (VAULT_ROOT 등)
   ├─ orchestrator.py        # 최상위 실행 흐름 (run_create/run_force/run_recompute)
   ├─ parser.py              # 데일리 노트 마크다운 → 블록 구조
   ├─ models.py              # Block, EventBundle 같은 데이터 클래스
   ├─ calendar_utils.py      # 영업일·주차 계산
   ├─ daily_writer.py        # 오늘 노트 파일 생성/갱신
   ├─ archive.py             # 보관함.md 갱신
   ├─ monthly_drop.py        # 월간 드롭 문서 갱신
   ├─ monthly_summary.py     # 월간 종합 문서 갱신
   ├─ events.py              # 어제 노트 → 이월/완료/드롭/보관 이벤트 분류
   └─ doctor.py              # 설치 환경 진단 (config 의존 안 함)
```

핵심 흐름: `orchestrator.run_create(today)` 가

1. 어제 노트 읽기 → `parser` 로 블록 분해
2. `events.classify_blocks()` 로 이월/완료/드롭/보관으로 분류
3. `daily_writer` 로 오늘 노트 생성 (이월 블록 포함)
4. `archive`, `monthly_drop`, `monthly_summary` 갱신

---

## 3. 절대 하지 말 것

### 3.1 리포를 잠긴 폴더로 옮기지 말 것

macOS TCC 는 다음 폴더를 잠급니다.

- `~/Documents/`, `~/Desktop/`, `~/Downloads/`, `~/Library/Mobile Documents/`

이 안에 리포가 놓이면 launchd 로 뜨는 파이썬이 **스크립트 파일을 여는 순간부터** 거절당합니다. 부팅 직후엔 특히 심합니다. `install.sh` 가 이 위치를 검사해서 중단하지만, 수동 배치 시엔 반드시 홈 폴더 바로 아래(`~/daily-note-system/` 등)를 씁니다.

이 규칙은 실제 사고에서 학습된 것입니다. 초기 배치를 `~/Documents/workspace/daily-note-system/` 에 했다가 부팅 직후 자동 실행이 계속 실패했습니다. 배경 상세는 이 파일 하단 "부록 A" 참고.

### 3.2 config.py 를 doctor 에서 참조하지 말 것

`lib/doctor.py` 는 **`DAILY_NOTE_VAULT_ROOT` 미설정 상태에서도 돌아야 합니다.** `lib.config` 는 로드 즉시 이 환경 변수를 요구하므로 doctor 에서 import 하면 크래시합니다. doctor 는 os.environ 을 직접 읽습니다.

같은 이유로 `daily_note.py` 의 `_log`, `_log_error` 는 `lib.config` 를 함수 내부에서 지연 import 합니다. 최상위 import 로 되돌리지 말 것.

### 3.3 외부 의존성 추가 금지

macOS 표준(Python 3.9 + 시스템 라이브러리 + bash + osascript) 만 사용합니다. `pip install`, Homebrew 도구, 서드파티 라이브러리 추가는 배포 마찰을 만듭니다. 알림도 `osascript` 로 처리합니다 (`terminal-notifier` 등 도입 금지).

### 3.4 launchd 우회 대안 도입 금지

launchd 대신 cron, `at`, 서드파티 스케줄러 등을 섞지 말 것. macOS 표준 방식으로 통일. cross-platform 확장은 별도 리포에서 다룹니다.

### 3.5 진단 억제 금지

`doctor` 나 `install.sh` 의 실패 조건을 완화·비활성화하는 방향의 수정은 하지 말 것. 실패가 나는 이유가 있고, 그 실패를 조기에 잡는 것이 이 시스템의 방어 계층 중 하나입니다.

---

## 4. 자주 하는 작업

### 새 마커 추가

1. `lib/config.py` 에 상수 정의 (예: `MARKER_LONG = "#장기"`)
2. `lib/parser.py` 에서 블록에서 마커 감지
3. `lib/events.py` 에서 분류 로직 반영
4. `tests/test_parser.py`, `tests/test_events.py` 에 케이스 추가
5. `README.md` 마커 표 갱신

### 새 이벤트 타입 추가 (예: 지연, 재개)

1. `lib/models.py` 의 `EventBundle` 에 필드 추가
2. `lib/events.py` 분류 로직에 반영
3. `lib/monthly_summary.py`, `lib/daily_writer.py` 등 소비 지점에서 렌더링 추가
4. 전체 테스트 재실행 (`python3 -m unittest discover tests`)

### 감독 스크립트 동작 조정

- 재시도 횟수·간격은 환경 변수(`DAILY_NOTE_MAX_ATTEMPTS`, `DAILY_NOTE_RETRY_INTERVAL`) 로 주입.
- 스크립트 상수 하드코딩 지양.
- Finder 대기 로직을 삭제하지 말 것. 이건 부팅 직후 TCC 데몬이 준비될 시간을 벌기 위한 것이지, 순수 지연이 아닙니다.

---

## 5. 디버깅

### "부팅 시 안 돌더라" 신고를 받으면

1. 로그 위치 (기본): `~/.local/state/daily-note/`
   - `supervisor.log` — 재시도 시도 기록
   - `last-failure.txt` — 최종 실패 시 진단 스냅샷
   - `daily-note.log`, `daily-note-error.log` — 파이썬 출력
2. `python3 daily_note.py doctor` 실행 → 리포트 확인
3. 리포가 잠긴 폴더 안이면 이사부터 지시
4. FDA 목록에 `/usr/bin/python3` 이 있는지 확인 (사용자 GUI 필요)

### 테스트 실행

```bash
/usr/bin/python3 -m unittest discover tests
```

87개 이상이어야 합니다 (2026-09-16 기준). 신규 기능은 반드시 테스트를 함께 추가.

### 특정 날짜로 재현

```bash
DAILY_NOTE_VAULT_ROOT="/path/to/vault" \
  /usr/bin/python3 daily_note.py create --today 2026-09-15
```

또는 파괴적이지 않게:

```bash
/usr/bin/python3 daily_note.py dry-run --today 2026-09-15
```

---

## 6. 릴리스·커밋 규칙

- 커밋 메시지는 영어. 대문자 명령형 동사로 시작 (`Add`, `Improve`, `Fix`, `Refactor`, `Document`). 기존 히스토리 스타일을 따릅니다.
- 테스트가 깨진 상태로 커밋 금지.
- README 는 사용자용, 이 문서는 LLM/미래의 자기 자신용. 서로 중복 최소화, 대신 상호 링크.
- launchd plist 템플릿을 수정하면 반드시 `install.sh` 의 sed 치환식도 검토.

---

## 부록 A. 부팅 직후 실행 실패 사건 (2026-09-16)

**증상**: 맥북을 켜자마자 로그인 시 launchd 가 파이썬을 실행하려다 `can't open file '...daily_note.py': Operation not permitted` 로 실패. 로그인 후 `launchctl kickstart` 로 수동 실행하면 성공.

**원인 후보 두 가지 (인터넷 사례 조사 결과 모두 관측됨)**:

1. **정적 권한 문제** (Sam Nunn 계열 진단): launchd 로 뜬 파이썬 프로세스에 대한 TCC 판정이 부팅 초기엔 유효하지 않은 상태로 시작한다.
2. **부팅 시 TCC 데몬 준비 지연**: TCC 데몬(`tccd`) 이 부팅 순간엔 요청을 못 받는 상태이고, launchd 는 이걸 기다리지 않고 LaunchAgent 를 발화시킨다.

**옛 셸 스크립트 시절엔 왜 안 걸렸나**: 옛 스크립트는 `~/.claude/scripts/` (잠긴 폴더 밖) 에 있어서 bash 가 스크립트 파일을 여는 순간이 TCC 검사 대상이 아니었습니다. 볼트 접근은 bash 의 오래된 TCC 캐시로 통과. 새 파이썬 스크립트는 `~/Documents/workspace/` (잠긴 폴더 안) 에 있어서 스크립트 파일 자체를 여는 첫 단계부터 TCC 대상이 되었고 부팅 직후에 걸렸습니다.

**결정적 변수는 "스크립트 위치"**. 그래서 이 프로젝트는 다음 세 층으로 방어합니다.

- **문서 예방**: README·CLAUDE.md 가 잠긴 폴더에 두지 말 것을 명시
- **설치 시점 차단**: `install.sh` 가 잠긴 폴더 안에서 실행되면 중단
- **런타임 복구**: `launchd/run-with-retry.sh` 가 Finder 대기 + 재시도 + 실패 알림

이 세 층 중 하나만 있어도 대부분 막히지만, 셋 다 있는 이유는 각각이 다른 사고 시나리오를 잡기 때문입니다. 방어층을 임의로 제거하지 말 것.

**참고 자료** (사고 조사 시 참조):

- Sam Nunn, "Why Won't launchd Run My Script?" (2023) — https://nunn.au/2023/11/28/tcc-launchd-woes
- Apple Discussions Thread 250843548 (Python + launchd + Downloads 폴더)
- Apple Developer Forums Thread 118508 (LaunchAgent/Daemon FDA 제약)
