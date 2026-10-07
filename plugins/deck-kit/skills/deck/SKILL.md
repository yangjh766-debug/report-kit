---
name: deck
description: 투자자, 경영진, 고객에게 보여 줄 디자인 덱(IR 덱, 회사소개서, 전략 보고 덱)을 PowerPoint 파일로 만든다. 결론을 먼저 말하는 컨설팅식 구성, PE와 FAS 수준의 숫자 해석, 일러스트레이터로 만든 것 같은 디자인(검은 화면 핵심 장표, 모핑, 직접 그린 차트)을 갖추고, 글자와 숫자는 PowerPoint에서 그대로 고칠 수 있다. "디자인 덱 만들어 줘", "IR 덱", "회사소개서 다시 디자인", "키노트급으로", "발표 자료 멋있게" 같은 요청에 사용한다. 문서형 보고서(Word)는 report 스킬, 상장예비심사신청서는 ipo-filing 스킬을 쓴다.
---

# 디자인 덱 만들기

결과물은 PowerPoint(pptx)다. 모든 글자, 표, 차트가 PowerPoint 도형이라 받은 사람이 바로 고칠 수 있다.
엔진은 `${CLAUDE_PLUGIN_ROOT}/skills/deck/scripts/deck_lib.js`, 규칙은 `references/`에 있다. 작업 전에 세 규칙 문서를 읽는다.

| 문서 | 내용 |
|---|---|
| `references/구성원칙.md` | 결론 먼저 쓰는 이야기 구조, 장 제목 쓰는 법, PE와 FAS 관점의 숫자 해석 목록 |
| `references/카피규칙.md` | 덱 문구 기준, 구어체와 비유를 실무 용어로 바꾸는 표, 줄바꿈 규칙 |
| `references/디자인시스템.md` | 색, 글꼴, 그리드, 장 유형 목록(엔진 함수), 사진 규칙, 점검 순서 |

## 준비 (처음 한 번)

```bash
# 작업 폴더에서
npm install pptxgenjs@3.12.0
python3 -m pip install --user pillow python-pptx
# 글꼴 Pretendard 설치: https://github.com/orioncactus/pretendard (없으면 검사 도구가 알려 준다)
K="${CLAUDE_PLUGIN_ROOT}/skills/deck"
python3 "$K/scripts/make_assets.py" glow FF4438 ./glow.png      # 강조색에 맞춘 핵심 장표 배경
```

## 절차

1. **원천을 모은다.** 기존 덱(pptx, PDF), 사업계획, 재무 숫자. 기존 덱이 있으면 장마다 글자를 뽑고 그림으로 훑어 내용과 숫자를 정리한다. 숫자는 원천 그대로 쓰고, 원천끼리 다르면 고치지 말고 목록으로 알린다.

2. **이야기 순서를 먼저 짠다.** `구성원칙.md`대로 한 장 요약과 장 제목 목록을 만든다. 장 제목만 이어 읽어도 투자 논리가 되어야 한다. 장이 많거나 처음 만드는 덱이면 이 목록을 사용자에게 먼저 보여 준다.

3. **숫자를 해석한다.** `구성원칙.md`의 지표 목록에서 이 회사에 맞는 것을 골라 계산한다(성장률, 이익률 변화, 매출 구성, 단위 경제성, 매출의 질, 배수). 계산한 숫자는 각주에 계산식을 적는다. 시장 규모처럼 근거 없는 외부 숫자는 만들지 않는다.

4. **빌드 스크립트를 쓴다.** `examples/sample_deck.js`를 본보기로, 엔진 함수로 장을 쌓는다.
   ```js
   const D = require(process.env.K + '/scripts/deck_lib.js')({ accent: 'FF4438', brand: '회사명', glow: './glow.png' });
   D.cover({...}); D.summary({...}); D.heroNumber({..., morph: 'n1'});
   const s = D.content({ no: '01', label: 'GROWTH', title: '결론 제목', sub: '근거 숫자', source: '각주', transition: 'morph' });
   D.trend(s, {..., morph: 'n1'}); D.bridge(s, {...});
   D.save('덱.pptx');
   ```
   - 핵심 장표(cover, heroNumber, heroPhoto, heroQuote, closing)는 4~6장마다 하나. 나머지는 증거 장표.
   - 사진은 원본 비율을 지킨다. 엔진이 잘림 20% 넘는 사진을 경고한다. 맞는 사진이 없으면 사진을 빼고 숫자로 짠다.
   - 같은 줄의 칸은 같은 크기로 둔다.

5. **마무리하고 검사한다.**
   ```bash
   node build.js                                                        # '사진 잘림 검사: 0건'이어야 한다
   python3 "$K/scripts/finalize.py" 덱.pptx "$(cat 덱.transitions.txt)"  # 어절 단위 줄바꿈, 모핑과 페이드 전환
   python3 "$K/scripts/check_text.py" 덱.pptx                            # 단어 끊김, 외톨이 줄, 넘침 0건이어야 한다
   zsh "$K/scripts/render_preview.sh" 덱.pptx 미리보기                    # 장마다 PNG(맥, Keynote 필요)
   ```
   검사가 0건이 아니면 문구를 의미 단위로 다시 나누거나 칸을 넓힌다.

6. **눈으로 본다.** 미리보기를 9장씩 모아 겹침, 잘림, 빈 공간, 칸 크기 불일치를 확인하고 고친다. 미리보기는 Keynote 근사치라 최종 확인은 PowerPoint에서 한다. Keynote, Word를 스크립트로 조작할 때는 활성 문서가 아니라 이름으로 집은 문서만 다룬다.

7. **보고한다.** 파일 경로, 장 구성(제목 목록), 새로 계산한 숫자와 계산식, 원천끼리 다른 숫자 목록.

## 하지 않는 것

- 원천에 없는 숫자, 사실, 시장 자료를 만들지 않는다.
- 사진을 칸에 맞춰 마음대로 자르지 않는다. 로고는 자르지 않는다(contain).
- 장마다 화려하게 하지 않는다. 강조색은 한 장에 한두 곳.
- 가운뎃점(·), 화살표(→), 줄표(—)로 문장을 잇지 않는다.
