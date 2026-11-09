"""카톡 메시지를 Claude에 넘기기 전에 개인정보를 가린다.

표준입력으로 받은 글을 가려서 표준출력으로 내보낸다. JSON이면 문자열 값만 가린다.

모드 (환경변수 KAKAO_MASK_MODE)
- work (기본): 일에 필요 없는 비밀번호, 인증번호, 주민번호만 가린다.
- strict: 전화, 메일, 10자리 이상 숫자까지 모두 가린다.
"""
import json
import os
import re
import sys

# 순서가 중요하다. 비밀번호와 이메일을 먼저 가리고, 긴 숫자는 맨 뒤에 가린다.
RULES = [
    # 비밀번호, 인증번호처럼 앞에 단어가 붙은 값
    (re.compile(r"((?:비밀\s*번호|비번|패스워드|password|passwd|pw|인증\s*번호|인증\s*코드|OTP|PIN)\s*(?:은|는|:|=|：)?\s*)(\S+)",
                re.IGNORECASE), r"\1[가림]"),
    # 이메일
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[메일]"),
    # 주민등록번호, 외국인등록번호
    (re.compile(r"(?<!\d)\d{6}\s*-\s*[1-8]\d{6}(?!\d)"), "[주민번호]"),
    # 휴대폰과 일반 전화 (010-1234-5678, 01012345678, 02-123-4567, +82 10-1234-5678)
    (re.compile(r"(?<!\d)(?:\+82[\s-]?|0)(?:1[016789]|2|[3-6][1-5]|70)[\s.-]?\d{3,4}[\s.-]?\d{4}(?!\d)"), "[전화]"),
    # 계좌번호, 카드번호, 사업자번호처럼 숫자가 10자리 이상 이어지는 값 (하이픈과 공백 허용)
    (re.compile(r"(?<![\d,.])\d(?:[\s-]?\d){9,}(?![\d,.])"), "[번호]"),
]


# work 모드에서 쓰는 규칙: 비밀번호류와 주민번호
WORK_RULES = [RULES[0], RULES[2]]


def mask(text: str, mode: str | None = None) -> str:
    mode = mode or os.environ.get("KAKAO_MASK_MODE", "work")
    for pattern, repl in (RULES if mode == "strict" else WORK_RULES):
        text = pattern.sub(repl, text)
    return text


def mask_json(value, mode: str | None = None):
    if isinstance(value, str):
        return mask(value, mode)
    if isinstance(value, list):
        return [mask_json(v, mode) for v in value]
    if isinstance(value, dict):
        return {k: mask_json(v, mode) for k, v in value.items()}
    return value


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except ValueError:
        sys.stdout.write(mask(raw))
        return
    json.dump(mask_json(data), sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
