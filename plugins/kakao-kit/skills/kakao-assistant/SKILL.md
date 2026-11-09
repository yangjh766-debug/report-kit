---
name: kakao-assistant
description: 맥 카카오톡 대화를 근무시간에 매시 읽어 요약, 할 일, 답장 초안, 캘린더 일정, 받은 파일을 대시보드 하나(카톡비서.html)로 정리하는 카톡 비서를 설치하고 관리한다. 카톡은 절대 보내지 않는다(보내기 기능을 지운 읽기 전용 빌드). "카톡 비서 설치", "카톡 자동 요약 세팅", "카톡 할 일 뽑기 자동화", "카톡비서 멈춰", "카톡방 빼 줘", "카톡 비서 대시보드 열어" 같은 요청에 사용.
---

# 카톡 비서 (kakao-assistant)

맥 카카오톡에 쌓인 대화를 평일 근무시간에 1시간마다 읽어서 다음을 만든다.

- 방별 요약과 이번 시간에 가장 중요한 일 한 줄
- 할 일 목록(TASKS.md)과, 연락할 일이면 바로 보낼 초안, 직접 할 일이면 하는 방법
- 답장이 필요한 메시지마다 답장 초안 (코덱스가 있으면 카톡 말투로 한 번 더 다듬음)
- 날짜와 시간이 분명한 약속은 Google 캘린더에 "[카톡]"을 붙여 추가 (커넥터가 있을 때)
- 카톡에서 저장해 둔 문서 파일 훑어보기
- 내가 카톡으로 답했거나 끝난 일은 대시보드에서 자동으로 완료 표시

결과는 `OUT_DIR/카톡비서.html` 한 파일에서 본다. 할 일 체크는 브라우저에 저장된다.

## 이 스킬을 쓸 때 지킬 것

- **카톡을 보내는 일은 어떤 경우에도 하지 않는다.** 설치 스크립트가 kakaocli 의 보내기, 로그인, 동기화 명령을 지우고 빌드한다. 보내기 도구는 받지도 빌드하지도 않는다.
- 사용자 번호와 DB 키는 화면이나 로그에 출력하지 않는다.
- `kakaocli status` 와 kakaocli 의 사용자 번호 자동 찾기는 돌리지 않는다. 무차별 대입이라 CPU를 몇 분씩 쓰고 맥이 뜨거워진다. 번호는 `setup/find_user_id.py` 로 찾는다.
- 빌드처럼 몇 분 걸리고 팬이 돌 수 있는 일은 시작 전에 사용자에게 말한다.
- 밖으로 나가는 설정(커넥터 연결, 예약 켜기)과 Homebrew 설치는 실행 전에 확인을 받는다.
- 사용자에게는 쉬운 말로 설명한다. 이 스킬을 쓰는 사람은 개발자가 아닐 수 있다.

## 시작 전에 꼭 알려 줄 것

설치를 시작하기 전에 아래 세 가지를 사용자에게 그대로 알리고 동의를 받는다.

1. **카카오 계정 제한 가능성**: 카카오가 공식 지원하는 방식이 아니다. 대화를 읽는 일은 맥 안에서만 일어나고 카카오 서버에는 접속하지 않지만, 카카오 운영정책상 이용 제한 가능성이 0이라고 말할 수 없다.
2. **대화가 AI 회사로 간다**: 새 메시지 본문이 매시 Claude(Anthropic)로, 답장 초안이 코덱스(OpenAI)로 간다. 비밀번호, 인증번호, 주민번호는 맥에서 가린 뒤 보낸다. 전화번호, 메일, 계좌번호까지 가리려면 `KAKAO_MASK_MODE=strict` 를 쓴다.
3. **다른 사람의 대화**: 상대방 메시지도 함께 처리된다. 내 업무 정리용으로만 쓰고 다른 사람 대화를 모으는 데 쓰지 않는다.

## 설치 순서

이 스킬 폴더를 `SKILL_DIR` 이라 부른다(이 SKILL.md 가 있는 폴더). 비서가 설치되는 곳은 `~/code/kakao-assistant`, 카톡을 읽는 도구는 `~/code/kakao-mcp` 다.

### 1. 준비물 확인

```bash
xcode-select -p && command -v brew uv claude && brew list sqlcipher
```

- 없는 것만 사용자 확인 후 설치한다: `xcode-select --install`, `brew install uv sqlcipher`.
- `claude` 가 없으면 Claude Code 설치부터 안내한다. 예약 실행은 `claude -p` 로 돌기 때문에 Claude 로그인이 돼 있어야 한다.
- 맥 카카오톡이 설치돼 있고 로그인돼 있어야 한다.

### 2. 설치 스크립트 실행 (3~5분, 빌드 중 팬이 돌 수 있음)

```bash
zsh "$SKILL_DIR/setup/install.sh"
```

마지막에 "실행기를 새로 만들었습니다"가 나오면 5단계에서 그 파일에 권한을 준다.

### 3. 카카오 사용자 번호 찾기

카톡 DB를 여는 열쇠를 계산하는 데 필요한 내 계정 번호다. 비밀번호가 아니고, 이 맥 밖에서는 쓸모가 없다. 인터넷을 막은 상태로 돌린다.

```bash
sandbox-exec -p '(version 1)(allow default)(deny network*)' ~/code/kakao-mcp/.venv/bin/python -I "$SKILL_DIR/setup/find_user_id.py"
```

- macOS가 "다른 앱의 데이터에 접근하려고 합니다"라고 물으면 허용하라고 안내한다.
- "확인된 번호가 하나가 아닙니다"가 나오면 저장되지 않은 것이다. 이때는 kakao-mcp README의 사용자 번호 안내를 따르되, 무차별 대입은 시간이 오래 걸리고 맥이 뜨거워진다고 먼저 말한다.

### 4. 설정 고치기

`~/code/kakao-assistant/settings.env` 를 연다. 사용자에게 이름과 결과 폴더만 물어 고친다. 나머지는 기본값을 둔다.

| 항목 | 뜻 | 기본값 |
|---|---|---|
| OWNER_NAME | 요약과 초안에서 나를 부를 이름 | 사용자 |
| OUT_DIR | 대시보드와 요약이 쌓이는 폴더 | ~/Documents/카톡비서 |
| WORK_START, WORK_END | 평일 실행 시각 범위 | 9, 19 |
| CLAUDE_MODEL | 요약 모델 | sonnet |

빼고 싶은 방은 `filter.json` 의 `exclude_chat_ids` 에 방 번호를 넣는다. 광고 채널과 오픈채팅은 기본으로 빠진다.

### 5. 전체 디스크 접근 권한 주기 (사용자가 직접)

카톡 DB는 macOS가 보호하는 폴더에 있어서, 예약 실행에 권한이 필요하다. 권한은 실행기 한 파일에만 준다.

1. 시스템 설정 > 개인정보 보호 및 보안 > 전체 디스크 접근 권한
2. 아래 + 를 누르고 Cmd+Shift+G 로 `~/code/kakao-assistant/bin/KakaoAssistant` 를 연다
3. 켜짐 상태인지 확인한다

실행기를 다시 빌드하면 권한이 풀린다. 그래서 install.sh 는 실행기가 있으면 다시 만들지 않는다.

### 6. 선택: Gmail, 캘린더, 코덱스

- **캘린더 일정 추가와 Gmail 임시보관함 요약**: claude.ai 설정의 커넥터 메뉴(https://claude.ai/settings/connectors)에서 Google Calendar 와 Gmail 을 연결한다. 연결하지 않아도 나머지는 돈다. Gmail 은 받는 사람을 비운 임시보관함 초안만 만들고 보내지 않는다.
- **코덱스로 초안 다듬기**: `codex` 명령이 있고 로그인돼 있으면 자동으로 쓴다. 없으면 Claude 초안을 그대로 쓴다.

### 7. 예약 켜고 시험 실행

```bash
zsh "$SKILL_DIR/setup/schedule.sh" on
zsh "$SKILL_DIR/setup/schedule.sh" test
```

1~2분 뒤 `schedule.sh status` 로 기록을 본다. "끝"이 찍히고 오류가 없으면 `open "$OUT_DIR/카톡비서.html"` 로 대시보드를 열어 보여 준다. 새 메시지가 없던 시간이면 "새 메시지 없음"만 찍힌다.

## 설치 뒤 자주 하는 일

| 요청 | 하는 일 |
|---|---|
| 대시보드 열어 줘 | `open "$OUT_DIR/카톡비서.html"` |
| 멈춰 줘 | `zsh "$SKILL_DIR/setup/schedule.sh" off` |
| 다시 켜 줘 | `zsh "$SKILL_DIR/setup/schedule.sh" on` |
| 지금 한 번 돌려 줘 | `zsh "$SKILL_DIR/setup/schedule.sh" test` |
| 시간대 바꿔 줘 | settings.env 의 WORK_START, WORK_END 를 고치고 `schedule.sh on` |
| 이 방은 빼 줘 | filter.json 의 exclude_chat_ids 에 방 번호 추가 (방 번호는 `~/code/kakao-assistant/inbox/done/*.attach.json` 의 chat_id 나, 사용자 동의 후 kakao-mcp 로 방 목록을 읽어 찾는다) |
| 업데이트 | `zsh "$SKILL_DIR/setup/install.sh"` 를 다시 실행 (설정과 기록은 그대로) |
| 완전히 지우기 | `schedule.sh off` 후 `~/code/kakao-assistant`, `~/code/kakao-mcp`, `~/.local/share/kakao-mcp`, `~/.config/kakao-mcp`, `~/Library/LaunchAgents/local.kakao-assistant.plist` 삭제. 전체 디스크 접근 권한 목록에서도 뺀다 |

## 문제가 생기면

`~/code/kakao-assistant/logs/run.log` 를 먼저 본다.

| 기록 | 원인과 해결 |
|---|---|
| `Not logged in` | 터미널에서 `claude` 를 한 번 실행해 로그인한다 |
| `authorization denied`, DB 를 못 연다 | 5단계 권한을 확인한다. 실행기를 다시 빌드했다면 목록에서 지우고 다시 추가한다 |
| `config.json 에 user_id 가 없습니다` | 3단계를 다시 한다 |
| 요약 문장에 Gmail 오류가 섞임 | Gmail 커넥터 로그인이 만료된 것이다. 커넥터 메뉴에서 다시 연결한다 |
| `코덱스 다듬기 건너뜀` | 코덱스가 없거나 로그인이 풀린 것이다. Claude 초안으로 정상 저장된다 |

## 어떻게 돌아가나

매시 정각에 launchd 가 실행기를 깨우면 `run.sh` 가 아래 순서로 돈다.

1. **수집** (`collect.py`, 인터넷 막음): 읽기 전용 kakaocli 로 지난 실행 뒤 대화가 오간 방의 새 메시지만 읽고, 비밀번호류를 가려 `inbox/` 에 마크다운으로 둔다.
2. **첨부** (`fetch_attachments.py`, 인터넷 막음): 카톡에서 저장해 다운로드 폴더에 있는 파일만 이름과 크기로 찾아 글자를 뽑는다. 카카오 서버에서는 받지 않는다. 사진은 카톡 앱이 암호화해 두므로 열지 않는다.
3. **요약** (`claude -p`): Claude 는 그 시간의 첨부 폴더 안 파일 읽기, Gmail 초안 만들기, 캘린더 보기와 추가만 할 수 있다. 명령 실행, 파일 쓰기, 웹, 카톡 도구는 모두 쓸 수 없게 해 두었다. 메시지 안의 지시는 따르지 않도록 지시문에 적어 두었다.
4. **다듬기** (`polish_drafts.py`): 초안과 받는 사람, 상대 문장 한 줄만 코덱스에 넘긴다. 숫자나 빈칸 "[ ]" 개수가 바뀌면 원래 문장을 쓴다. 코덱스는 문서와 카톡 폴더를 읽지 못하게 막은 상태로 돈다.
5. **저장** (`save_result.py`): 기록(data/), 요약(요약/), TASKS.md, 대시보드를 갱신하고 맥 알림을 띄운다. 가린 수집 파일은 7일, 받은 파일 사본은 30일 뒤 지운다.

비용은 메시지 양에 따라 다르다. 한 번 실행에 API 요금으로 환산하면 대략 0.1달러 안팎이었다 [확인 필요: 원화 환율]. Claude 구독 사용량에서 차감되는 경우 따로 청구되지 않는다.

## 출처

- 카톡 읽기: [Jaeha0526/kakao-mcp](https://github.com/Jaeha0526/kakao-mcp) (MIT), [Jaeha0526/kakaocli](https://github.com/Jaeha0526/kakaocli) (silver-flight-group/kakaocli 기반). install.sh 가 검토한 커밋으로 고정해 받는다.
