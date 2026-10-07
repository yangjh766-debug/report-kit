# report-kit

한국어 업무 문서를 Claude Code로 쓸 때 쓰는 플러그인입니다. 숫자가 틀리지 않고, AI가 쓴 티가 나지 않고, 표와 문서 모양이 실무 전문가의 검토보고서처럼 보이는 Word를 만드는 데 초점을 맞췄습니다.

## 들어 있는 것

| 구성 | 하는 일 |
|---|---|
| `report` 스킬 | 문서 종류에 따라 두 문체로 씁니다. 내부 검토자료는 회색톤 검토보고서 양식(제목 이중선, Ⅰ. 절 제목, 개조식, 위아래 이중괘선 표, [표 N] 캡션, 머리글과 쪽번호), 대외 글은 서술식 경어체. 표 서식 엔진, 표 그림 확인, 기존 회사 양식을 재는 도구 포함 |
| `wording` 스킬 | Claude가 쓴 글을 코덱스(ChatGPT)에게 넘겨 문장만 자연스럽게 다시 쓰게 하고, 숫자와 표식이 하나라도 바뀌면 결과를 버림 |
| 기본 규칙 | 대화를 시작할 때마다 짧은 글쓰기 규칙(가운뎃점 금지, 원/만원/억원 단위 등)을 Claude에게 알려 줌 |
| 문서 검사 | Claude가 .md 문서를 저장할 때마다 금지 표현을 찾아 Claude가 바로 고치게 함 |

## 설치

Claude Code 입력창에 차례로 입력합니다.

```
/plugin marketplace add yangjh766-debug/report-kit
/plugin install report-kit@report-kit
```

터미널에서는 다음과 같습니다.

```bash
claude plugin marketplace add yangjh766-debug/report-kit
claude plugin install report-kit@report-kit
```

설치한 뒤 Claude Code를 다시 시작합니다. 새 버전이 나오면 `/plugin` 메뉴에서 업데이트하거나 `claude plugin update report-kit@report-kit`를 실행합니다.

### 함께 필요한 것

- Word 변환: `python3 -m pip install --user python-docx pillow`
- wording 스킬: 코덱스 CLI와 ChatGPT 계정(Plus 이상)
  ```bash
  npm install -g @openai/codex
  codex login
  ```
  코덱스가 없어도 report 스킬은 동작합니다. 문장 다듬기 단계만 건너뜁니다.

## 쓰는 법

따로 명령을 외울 필요는 없습니다. 평소처럼 말하면 Claude가 알맞은 스킬을 엽니다.

- "이 엑셀로 3분기 실적 보고서 써 줘. 표 넣어서 docx로"
- "방금 쓴 메일 워딩 다듬어 줘"
- "이 표 Word에서 예쁘게 보이게 만들어 줘"

꼭 그 스킬을 쓰게 하고 싶을 때만 `/report-kit:report`, `/report-kit:wording`을 입력합니다.

## 문서 양식

- 검토보고 모양: `md2docx_table.py 원고.md 결과.docx --look review "--header=내부 검토자료 │ Strictly Confidential"`
- 회사 양식에 맞추기: `docx_spec.py 기존자료.docx`로 여백, 글꼴, 괘선, 정렬을 재서 다른 값만 맞춥니다.
- 상장예비심사신청서처럼 제출 서식이 정해진 문서와, 프로젝트 지침이 양식을 따로 정한 작업에는 쓰지 않습니다. 그런 프로젝트에서는 `.claude/settings.json`에 `"enabledPlugins": {"report-kit@report-kit": false}`를 넣어 끌 수 있습니다.

## 규칙 고치기

- 공통 금지 표현: `plugins/report-kit/skills/report/references/워딩규칙.md`
- 문체: 같은 폴더의 `문체_검토보고.md`(개조식), `문체_서술형.md`(서술식)
- 표 서식: `plugins/report-kit/skills/report/references/표서식규칙.md`
- 저장할 때 검사하는 목록: `plugins/report-kit/scripts/doc_check.py`의 `BAN`, `OTHER`
- 대화마다 알려 주는 짧은 규칙: `plugins/report-kit/hooks/core-rules.md`

이 저장소를 포크해 자기 규칙으로 바꾼 뒤, 자기 저장소 주소로 설치하면 됩니다.


## 주의

- wording 스킬은 글을 OpenAI 서버로 보냅니다. 회사 기밀 문서는 회사 정책을 먼저 확인하세요.
- 표 서식 엔진은 맑은 고딕 글자 폭을 재서 열 폭을 정합니다. Microsoft Word가 설치된 맥에서 가장 정확하고, 없으면 근사치로 계산합니다.

## 라이선스

MIT
