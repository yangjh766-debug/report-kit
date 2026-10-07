# report-kit

Claude Code 플러그인 세 개와 작업 환경 세팅팩을 담은 저장소입니다.

| 플러그인 | 하는 일 | 설치 |
|---|---|---|
| report-kit | 한국어 업무 보고서(검토보고 양식, 서술형), 표가 깔끔한 Word, 코덱스 문장 다듬기 | `/plugin install report-kit@report-kit` |
| ipo-filing | 코스닥 상장예비심사신청서 작성 범용 플레이북 | `/plugin install ipo-filing@report-kit` |
| deck-kit | IR, 회사소개 디자인 덱(고칠 수 있는 PowerPoint) | `/plugin install deck-kit@report-kit` |

## 세팅팩 (setup-pack)

새 맥에 VS Code, Claude Code, 코덱스, 제미나이 작업 환경을 꾸리는 꾸러미입니다. 설치 스크립트, 전역 지침과 설정 예시, 에이전트 예시, 메일 자동화 가이드, 개선 루프 예시가 들어 있습니다.

- 받기: [main.zip 다운로드](https://github.com/yangjh766-debug/report-kit/archive/refs/heads/main.zip) 후 압축을 풀고 `setup-pack` 폴더를 엽니다.
- 시작: `setup-pack/0_README.md`를 읽고 터미널에서 `zsh setup-pack/1_설치/setup.sh`를 실행합니다.
- 개선 루프 예시는 `/improve-loop`로 직접 부를 때만 돌고, 시작 전과 라운드마다 승인을 받습니다.

세 플러그인 모두 먼저 `/plugin marketplace add yangjh766-debug/report-kit`을 한 번 실행한 뒤 설치합니다. 신청서 작업 폴더에서는 report-kit을 꺼 두면 보고서 양식과 섞이지 않습니다.

# report-kit 플러그인

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


# ipo-filing 플러그인

코스닥 상장예비심사신청서를 회사 자료로 작성할 때 쓰는 플레이북입니다. 실제 작업 한 건에서 정리한 방법과 규칙을 회사 이름, 사람, 숫자 없이 다른 회사에 다시 쓸 수 있게 옮겼습니다.

| 문서 | 내용 |
|---|---|
| 00_README, 순서도.html | 전체 흐름, 처음 할 일 |
| 01 착수와 작업흐름 | 착수 첫날 확인할 것, 폴더 구조, 단계별 산출물 |
| 02 자료가공과 검증 | 원천 추출, 대조표 엑셀, 재계산 검증 |
| 03 표서식 | 거래소 양식 열 구성, 실측 열 폭, 정렬, 주기, 주주와 임원 표 |
| 04 문장과 워딩 | 관용 문장 틀, 금지 표현, 숫자 불변 확인 |
| 05 회사자료요청 | 첫 요청 세트, 요청 리스트 관리, 회신 반영 |
| 06 docx 피드백루프 | 회사가 Word를 고치기 시작한 뒤의 판 관리 |
| 07 장별 체크포인트 | Ⅰ~Ⅸ장별 쓸 것과 함정 |
| 08 실수사례와 교훈 | 실제로 지적받은 실수와 예방법 |
| 09 도구 레시피 | docx, 엑셀, PDF 처리 코드 조각 |

설치:
```
/plugin marketplace add yangjh766-debug/report-kit
/plugin install ipo-filing@report-kit
```

"새 회사 신청서 착수하자", "신청서 Ⅰ장 써 줘"처럼 말하면 이 스킬이 열립니다. 프로젝트 폴더에 자체 지침(CLAUDE.md, 지침 폴더)이 있으면 그 지침이 우선합니다. 순서도.html은 archify(MIT)로 만들었습니다.

# deck-kit 플러그인

투자자나 경영진 앞에서 쓰는 디자인 덱을 PowerPoint로 만듭니다. 글자, 표, 차트가 모두 PowerPoint 도형이라 받은 사람이 바로 고칠 수 있습니다.

- **구성:** 결론을 먼저 말하는 한 장 요약, 장 제목만 이어 읽어도 논리가 되는 이야기 순서
- **숫자 해석:** 성장률, 이익률 변화, 매출 구성, 단위 경제성, 매출의 질, 배수를 원천에서 계산하고 계산식을 각주에
- **디자인:** 검은 화면 핵심 장표(숫자 하나, 전면 사진, 한 문장), PowerPoint 모핑, 직접 그린 추이와 다리형 차트, 파이프라인, 비교 막대. 강조색만 바꾸면 회사 색으로
- **검사:** 사진 잘림 20% 초과 경고, 단어 끊김과 외톨이 줄 검사, 장별 미리보기

설치:
```
/plugin marketplace add yangjh766-debug/report-kit
/plugin install deck-kit@report-kit
```

작업 폴더에서 `npm install pptxgenjs@3.12.0`을 한 번 실행하고, 글꼴 [Pretendard](https://github.com/orioncactus/pretendard)를 설치합니다. "이 사업계획으로 IR 덱 만들어 줘", "회사소개서 키노트급으로 다시 디자인해 줘"처럼 말하면 됩니다.

`plugins/deck-kit/skills/deck/examples/`에 가상의 회사(MediNote)로 만든 13장 예시 덱과 빌드 스크립트가 있습니다. 회사와 숫자는 모두 가상입니다.

## 주의

- wording 스킬은 글을 OpenAI 서버로 보냅니다. 회사 기밀 문서는 회사 정책을 먼저 확인하세요.
- 표 서식 엔진은 맑은 고딕 글자 폭을 재서 열 폭을 정합니다. Microsoft Word가 설치된 맥에서 가장 정확하고, 없으면 근사치로 계산합니다.

## 라이선스

MIT
