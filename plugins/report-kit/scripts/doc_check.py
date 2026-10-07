# -*- coding: utf-8 -*-
"""Claude Code PostToolUse 훅. Claude가 .md/.txt 문서를 쓰거나 고칠 때마다 워딩 규칙 위반을 찾아 Claude에게 바로 알려 준다.

- 편집은 막지 않는다. 문제를 Claude 대화에 「추가 맥락」으로 넣어 Claude가 스스로 고치게 한다.
- 규칙 문서(파일명에 '규칙'이 들어가거나 '지침', 'references' 폴더 안)는 예시로 금지어를 담고 있으니 검사하지 않는다.
- 단독 실행도 된다: python3 문서검사.py 파일.md

금지 목록은 아래 BAN, PII, OTHER를 각자 고쳐 쓴다.
"""
import json, re, sys
from pathlib import Path

# (정규식, 설명)
BAN = [
    (r"·", "가운뎃점 → 쉼표, '및', '와/과'"),
    (r"\d[\d.,]*\s?(m|bn|mn|M|B|k|K)(?![A-Za-z])", "영어 금액 단위 → 원, 만원, 억원"),
    (r"최고의|유일한|압도적|혁신적|획기적|세계적", "근거 없는 최상급"),
    (r"[가-힣] 것입니다", "단정 미래 → '~할 계획입니다', '~로 예상됩니다'"),
    (r"(?m)(함|임|음)\.?\s*$", "개조식 어미(~함, ~임) → '~습니다'"),
    (r"→", "화살표로 문장 잇기"),
    (r"—", "줄표(—) 덧붙임"),
    (r"단수\s?차이|반올림으로 .{0,10}차이", "반올림 해명 문구"),
    (r"(결산\s?자료로|기준으로) 작성하였", "작업 과정 문구"),
    (r"\|\s*상동\s*\|", "표 안 '상동' → 셀 병합"),
    (r"이식|막는다|막습니다|막아 줍니다|차단", "딱딱한 직역투 → 옮기기, 공유, 멈춘다, 걸러낸다"),
]
PII = [
    (r"\d{6}-[1-4]\d{6}", "주민등록번호"),
    (r"(?<![\d-])010-?\d{4}-?\d{4}(?!\d)", "휴대전화 번호"),
]
OTHER = []   # 섞여 들어오면 안 되는 다른 회사 이름, 예: ["A사", "B전자"]


def check(text):
    out = []
    lines = text.splitlines()
    for pat, why in BAN + PII + [(re.escape(n), "다른 회사 이름") for n in OTHER]:
        for i, ln in enumerate(lines, 1):
            if ln.lstrip().startswith(("```", "    ")):
                continue
            m = re.search(pat, ln)
            if m:
                out.append(f"{i}행 [{why}] …{ln[max(0, m.start()-15):m.end()+15].strip()}…")
    pending = len(re.findall(r"\[확인 필요", text))
    if pending:
        out.append(f"(참고) [확인 필요] 표식 {pending}개 남음")
    return out


def skip(p: Path):
    return p.suffix not in (".md", ".txt") or "규칙" in p.name or "지침" in p.parts or "references" in p.parts or not p.exists()


if __name__ == "__main__":
    if len(sys.argv) > 1:                      # 단독 실행
        p = Path(sys.argv[1])
        res = check(p.read_text(encoding="utf-8"))
        print("\n".join(res) if res else "문제 없음")
        sys.exit(0)
    try:                                       # 훅 실행: 표준입력으로 훅 JSON을 받는다
        data = json.load(sys.stdin)
        p = Path((data.get("tool_input") or {}).get("file_path") or "")
    except Exception:
        sys.exit(0)
    if skip(p):
        sys.exit(0)
    res = [r for r in check(p.read_text(encoding="utf-8")) if not r.startswith("(참고)")]
    if res:
        msg = f"{p.name} 워딩 규칙 위반 {len(res)}건. 고친 뒤 다시 저장하라:\n" + "\n".join(res[:30])
        # exit 0 + stdout 그냥 출력은 Claude에게 전달되지 않는다. additionalContext로 넘겨야 Claude가 본다.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}, ensure_ascii=False))
    sys.exit(0)
