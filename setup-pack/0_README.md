# AI 작업환경 세팅팩

VS Code + Claude Code를 중심으로 코덱스(ChatGPT), 제미나이, Aside를 함께 쓰는 업무 환경을 새 맥에 꾸리는 꾸러미입니다.
비개발자가 하루 안에 세팅하는 것을 기준으로 만들었습니다.

**받는 법:** https://github.com/yangjh766-debug/report-kit/archive/refs/heads/main.zip 을 받아 압축을 풀면 `setup-pack` 폴더가 이 팩입니다. 터미널에서는 `git clone https://github.com/yangjh766-debug/report-kit` 로 받아도 됩니다.

보고서, 워딩 스킬과 글쓰기 규칙은 이 팩이 아니라 플러그인으로 받습니다. 한 곳에서 고치면 받은 사람 모두에게 반영되기 때문입니다.

```
/plugin marketplace add yangjh766-debug/report-kit
/plugin install report-kit@report-kit
/plugin install deck-kit@report-kit     ← 디자인 덱(IR, 회사소개서)을 만들 때
/plugin install ipo-filing@report-kit   ← 상장예비심사신청서 작업을 할 때만
```

## 들어 있는 것

| 파일 | 내용 | 설치 위치 |
|---|---|---|
| 1_설치/setup.sh | node, 코덱스, 제미나이 설치와 아래 파일 복사를 한 번에 | 실행만 |
| 2_참고/메일자동화_가이드.md | Aside, ChatGPT, Apps Script로 메일 자동화 | 읽기용 |
| 3_설정예시/CLAUDE.md | 전역 지침 템플릿([대괄호]를 자기 것으로) | ~/.claude/CLAUDE.md |
| 3_설정예시/settings.json | 모델, 언어, 권한, 알림 설정 예시 | ~/.claude/settings.json |
| 3_설정예시/agents/ | 서브에이전트 예시 | ~/.claude/agents/ |
| 4_도구/codexlog | 코덱스 작업 진행 상황을 터미널에서 보기 | ~/.local/bin/ |
| 5_예시_개선루프/ | 전략, 실행, 검토 에이전트가 점수 기준으로 되풀이하는 루프의 예시. /improve-loop로 직접 부를 때만 돌고, 시작 전과 라운드마다 승인을 받는다 | 설치 안 함 |

## 세팅 순서 (요약)

1. VS Code 설치 → 한국어 언어팩, Claude Code 확장 설치 → Claude 계정 로그인
2. 작업 폴더 만들기 → VS Code에서 폴더 열기
3. 터미널에서 `zsh 1_설치/setup.sh`
4. Claude Code 입력창에서 report-kit 플러그인 설치
5. 새 터미널에서 `codex login`, 제미나이 API 키 등록
6. `~/.claude/CLAUDE.md`의 [대괄호]를 자기 정보로 채우기
7. GitHub, Claude 커넥터, Aside, ChatGPT Gmail 연결
8. 시험: 짧은 보고서를 시키고 docx까지

자세한 화면 설명과 흐름도는 함께 받은 가이드 페이지에 있습니다.

## 지켜야 할 것
- API 키, 로그인 파일(`~/.codex/auth.json`, `~/.gemini/.env`)은 남에게 주거나 저장소에 넣지 않습니다.
- 회사 기밀 자료를 외부 AI(코덱스, 제미나이, ChatGPT)에 넣어도 되는지 회사 정책을 먼저 확인합니다.
- 메일 발송, 결제, 서명, 신고 제출은 자동화하지 않거나 마지막 클릭을 사람이 합니다.
