#!/usr/bin/env python3
"""에세이 위임 스크립트: 재료(brief) → 코덱스가 처음부터 집필 → 기계 검사 보고서.

/wording(polish.py)은 구조·숫자를 지키며 문장만 다듬는다. 이 스크립트는 반대로
구성과 문장을 코덱스에게 통째로 맡기고, 사실이 새지 않았는지만 검사한다.

사용:
  python3 write.py brief.md out.md [--style 규칙.md ...] [--n 2] [--effort high]
  python3 write.py brief.md out.md --revise out_1.md --notes notes.md   # 고칠 점만 반영

결과:
  out_1.md, out_2.md …  (--n 개수만큼, --n 1이면 out.md)
  out.report.md         판별 검사 결과(필수 문구, 새 숫자, 금지 표현, 리듬 지표)
  out.work/             코덱스에 준 파일과 호출 기록

종료코드: 0 = 모든 판 통과, 1 = 빨강(필수 문구 누락·새 숫자)인 판이 있음, 2 = 실행 오류
"""
from __future__ import annotations
import argparse
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STYLE = os.path.join(HERE, "styles", "linkedin.md")

WRITE_PROMPT = """현재 폴더의 style.md(문체 규칙)와 brief.md(글 재료)를 먼저 끝까지 읽어라.
그다음 brief.md의 재료로 글을 처음부터 새로 써라.

- 재료를 다 쓰지 않는다. 「이 글로 하고 싶은 말」에 필요한 재료만 골라 쓰고, 나머지는 과감히 버린다(「[필수]」만 예외).
- 구성은 네가 정한다. 재료에 적힌 순서를 따를 필요가 없다. 어디서 시작해 어디서 힘을 주고 어떻게 끝낼지 먼저 정한 뒤 써라.
- 문장도 네가 새로 짓는다. 「글쓴이 말투」 절은 글쓴이가 직접 쓴 문장이니 그 말투와 어휘를 따르되, 「그대로 넣을 것」 절의 항목만 글자 그대로 넣는다.
- 재료에 없는 사실, 사례, 숫자, 인물, 감정은 만들지 않는다. 재료에 있는 사실은 빼도 되지만 「꼭 들어갈 사실」로 표시된 것은 뺄 수 없다.
- brief.md에 「살을 붙여도 되는 것」 절이 있으면, 그 범위 안에서 글쓴이의 생각, 해석, 비유, 논증을 더 풍부하게 펼쳐도 된다. 그래도 일어나지 않은 일, 사람, 숫자, 다른 사람의 말은 만들지 않는다.
- 「어디에 올리고 누가 읽나」 절은 배경 정보다. 그 절의 글쓴이 소개를 본문에 넣지 않는다.
- brief.md에 「제목」 절이 있으면 그 제목을 글의 첫 줄에 글자 그대로 쓰고 한 줄을 띄운 뒤 본문을 시작한다.
- 「그대로 넣을 것」의 한 줄 문장(구호, 결론)은 혼자 뜬금없이 나오지 않게, 바로 앞 문단에서 그 말이 나올 이유를 깔아 준다.
- 「핵심 문단」 절이 있으면 그 문단을 글의 정점(3분의 2 지점쯤)에 두고, 앞의 장면은 모두 그 문단으로 올라가는 계단이 되게 쓴다.
- 제안이나 다짐을 습관이나 사실처럼 바꿔 쓰지 않는다(「~하자고 했다」를 「나는 늘 ~한다」로 바꾸지 않는다). 인용은 한 글자도 바꾸지 않는다.
- 완성된 글 전문만 출력한다. 설명, 제목 안내, 따옴표, 코드 블록을 붙이지 않는다.
{variant}"""

VARIANTS = [
    "",
    "- 이번 판은 앞 판과 다른 시작을 시도한다. 장면(그날 있었던 일)에서 바로 시작해 보라.",
    "- 이번 판은 글쓴이의 고백(예전의 나)에서 시작해 보라.",
]

TOPIC_PROMPT = """현재 폴더의 brief.md를 끝까지 읽어라. 글쓴이가 실제로 나눈 대화나 겪은 일이다.
이 재료로 링크드인에 올릴 1인칭 에세이의 주제 후보를 {n}개 뽑아라.

- 주제는 재료 전체를 요약하지 않는다. 재료 안에서 가장 날카로운 생각 하나를 골라 그것만 밀고 간다.
- 「AI는 도구일 뿐이다」「결국 사람이 중요하다」「효율보다 본질」처럼 누구나 하는 말은 후보에서 뺀다. 읽는 사람이 「이건 처음 듣는 관점인데」라고 느낄 것만 남긴다.
- 글쓴이만 할 수 있는 말을 우선한다. 글쓴이의 직업 배경과 실제로 한 말에서 나온 관점이어야 한다.
- 재료를 다 쓸 필요가 없다. 주제 하나에 필요한 재료 두세 개만 고르고 나머지는 버린다.
- 재료에 없는 사실, 사례, 숫자를 만들지 않는다.

후보마다 다음을 마크다운으로 적어라.
### N. 제목(30자 이내)
- 핵심 주장: 한 문장
- 왜 뻔하지 않은가: 한두 문장
- 첫 문장: 실제 글의 첫 문장 예시 하나
- 쓸 재료: 재료에서 가져올 말이나 장면 두세 개(원문 그대로 짧게)
- 약점: 이 주제로 쓸 때 위험한 점 한 문장

맨 끝에 「## 추천」으로 하나를 고르고 그 이유를 세 문장 이내로 적어라. 다른 설명은 붙이지 않는다."""

REVISE_PROMPT = """현재 폴더의 style.md(문체 규칙), brief.md(글 재료), draft.md(앞서 쓴 글), notes.md(고칠 점)를 읽어라.
notes.md에 적힌 곳만 고치고 나머지 문장은 그대로 둔다. 고친 결과도 style.md와 brief.md의 규칙을 지킨다.
재료에 없는 사실, 숫자는 만들지 않는다. 고친 글 전문만 출력한다. 설명을 붙이지 않는다."""

NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
BANNED = [
    (re.compile(r"[가-힣]+[이가] 아니라"), "「A가 아니라 B」 대조"),
    (re.compile(r"것이다[.!]"), "「~것이다」 자기 정의"),
    (re.compile(r"!"), "느낌표(감탄)"),
]


def section_items(text: str, heading: str) -> list[str]:
    """'## heading' 절 아래 '- ' 줄을 모은다(다음 ## 전까지)."""
    m = re.search(rf"^##\s*{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
    return out


def kill_tree(pid: int) -> None:
    """pid와 그 자손을 모두 SIGKILL (codex 런처가 새 세션을 만들어도 남지 않게)."""
    try:
        ps = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True).stdout
    except Exception:
        ps = ""
    kids: dict[int, list[int]] = {}
    for line in ps.splitlines():
        parts = line.split()
        if len(parts) == 2:
            kids.setdefault(int(parts[1]), []).append(int(parts[0]))
    stack, seen = [pid], []
    while stack:
        p = stack.pop()
        seen.append(p)
        stack.extend(kids.get(p, []))
    for p in reversed(seen):
        try:
            os.kill(p, signal.SIGKILL)
        except ProcessLookupError:
            pass


def call_codex(work: str, prompt: str, out: str, effort: str, model: str | None, timeout: int) -> tuple[bool, str]:
    cmd = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check",
           "-c", f'model_reasoning_effort="{effort}"', "-o", out]
    if model:
        cmd += ["-m", model]
    cmd.append(prompt)
    log = open(out + ".log", "w")
    # stdin을 닫는다: 열려 있으면 codex가 "Reading additional input from stdin..."에서 멈춘다(wording 스킬에서 확인)
    proc = subprocess.Popen(cmd, cwd=work, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)
        log.close()
        return False, f"시간 초과({timeout}초)"
    log.close()
    if proc.returncode != 0 or not os.path.exists(out) or not open(out).read().strip():
        return False, f"codex 종료코드 {proc.returncode} (기록: {out}.log)"
    return True, ""


def clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n|\n```$", "", text)
    return text.strip() + "\n"


def sentences(text: str) -> list[str]:
    body = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "http", "•", "- ", "* ")) or re.match(r"^\d+\.\s", s):
            continue
        body.append(s)
    out = []
    for para in body:
        out += [x.strip() for x in re.split(r"(?<=[.?!])\s+", para) if x.strip()]
    return out


def rhythm(text: str) -> dict:
    sents = sentences(text)
    lens = [len(s) for s in sents] or [0]
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    prose = [p for p in paras if not p.startswith(("#", "http", "•", "- "))]
    single = [p for p in prose if len(re.split(r"(?<=[.?!])\s+", p)) == 1]
    da_run, run = 0, 0
    for s in sents:
        run = run + 1 if s.endswith("다.") else 0
        da_run = max(da_run, run)
    short_run, run = 0, 0
    for n in lens:
        run = run + 1 if n <= 25 else 0
        short_run = max(short_run, run)
    return {
        "문장 수": len(sents),
        "평균 문장 길이(자)": round(mean, 1),
        "길이 변동계수": round(cv, 2),
        "가장 긴 문장(자)": max(lens),
        "산문 문단 수": len(prose),
        "한 문장짜리 문단": len(single),
        "「~다.」 최장 연속": da_run,
        "25자 이하 짧은 문장 최장 연속": short_run,
    }


REPORT_RX = re.compile(r"(?:자고|라고|다고|냐고|하자고)\s?(?:했다|제안했다|말했다|답했다)[.]")


def ending_repeats(text: str) -> list[str]:
    """문장 끝 어절이 네 번 이상 되풀이되거나, 남의 말을 전하는 꼴(「~자고 했다」)이 세 번 이상이면 경고."""
    out = []
    ends = {}
    for snt in sentences(text):
        w = re.sub(r"[\"'”’」)]+$", "", snt.split()[-1]) if snt.split() else ""
        if w and w not in ("있다.", "없다.", "된다.", "이다.", "했다.", "한다.", "였다.", "있었다."):
            ends[w] = ends.get(w, 0) + 1
    for w, n in sorted(ends.items(), key=lambda x: -x[1]):
        if n >= 4:
            out.append(f"「{w}」로 끝나는 문장 {n}개")
    rep = len(REPORT_RX.findall(text))
    if rep >= 3:
        out.append(f"남의 말을 전하는 「~자고 했다」류 {rep}개(회의록처럼 읽힘)")
    return out


def rhythm_flags(r: dict) -> list[str]:
    flags = []
    if r["길이 변동계수"] < 0.4:
        flags.append("문장 길이가 고르다(끊기는 느낌 위험)")
    if r["산문 문단 수"] and r["한 문장짜리 문단"] / r["산문 문단 수"] > 0.35:
        flags.append("한 문장짜리 문단이 많다")
    if r["25자 이하 짧은 문장 최장 연속"] >= 4:
        flags.append("짧은 문장이 네 번 넘게 이어진다")
    return flags


def check(text: str, brief: str, verbatim: list[str]) -> dict:
    missing = [v for v in verbatim if v not in text]
    brief_nums = set(NUM_RE.findall(brief))
    new_nums = sorted({n for n in NUM_RE.findall(text) if n not in brief_nums})
    banned = []
    for rx, label in BANNED:
        for m in rx.finditer(text):
            start = max(0, m.start() - 15)
            banned.append(f"{label}: …{text[start:m.end() + 10].strip()}…")
    r = rhythm(text)
    reps = ending_repeats(text)
    grade = "빨강" if (missing or new_nums) else ("노랑" if (banned or reps) else "녹색")
    return {"grade": grade, "missing": missing, "new_nums": new_nums, "banned": banned,
            "rhythm": r, "flags": rhythm_flags(r), "repeats": reps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("out")
    ap.add_argument("--style", action="append", help="문체 규칙 파일(여러 번 가능). 없으면 styles/linkedin.md")
    ap.add_argument("--n", type=int, default=2, help="만들 판 수(기본 2, 최대 3)")
    ap.add_argument("--effort", default="high", help="코덱스 생각 수준(low/medium/high)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--revise", help="고칠 대상 글(이 경우 --notes 필수, 판 1개)")
    ap.add_argument("--notes", help="고칠 점 메모 파일")
    ap.add_argument("--topics", type=int, default=0, help="글 대신 주제 후보 N개를 뽑는다(0단계)")
    ap.add_argument("--compare", help="비교용 기존 글(보고서에 리듬 지표를 나란히 적는다)")
    a = ap.parse_args()

    if shutil.which("codex") is None:
        print("codex 명령을 찾을 수 없습니다. PATH에 ~/.local/node/bin 을 넣어 주세요.", file=sys.stderr)
        return 2
    brief = open(a.brief, encoding="utf-8").read()
    styles = a.style or [DEFAULT_STYLE]
    style_text = "\n\n".join(open(s, encoding="utf-8").read() for s in styles)
    verbatim = section_items(brief, "그대로 넣을 것") + section_items(brief, "제목")

    a.out = os.path.abspath(a.out)
    base = os.path.splitext(a.out)[0]
    work = base + ".work"
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, "brief.md"), "w", encoding="utf-8") as f:
        f.write(brief)
    with open(os.path.join(work, "style.md"), "w", encoding="utf-8") as f:
        f.write(style_text)

    if a.topics:  # 0단계: 주제 후보만 뽑고 검사 없이 끝낸다
        raw = os.path.join(work, "topics.raw")
        print(f"코덱스 주제 뽑는 중: {a.topics}개 (생각 수준 {a.effort})", flush=True)
        ok, err = call_codex(work, TOPIC_PROMPT.format(n=a.topics), raw, a.effort, a.model, a.timeout)
        if not ok:
            print(f"  실패: {err}", flush=True)
            return 1
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(clean(open(raw, encoding="utf-8").read()))
        print(f"주제 후보: {a.out}")
        return 0

    jobs = []  # (결과 경로, 프롬프트)
    if a.revise:
        if not a.notes:
            print("--revise에는 --notes가 필요합니다.", file=sys.stderr)
            return 2
        shutil.copy(a.revise, os.path.join(work, "draft.md"))
        shutil.copy(a.notes, os.path.join(work, "notes.md"))
        jobs.append((a.out, REVISE_PROMPT))
    else:
        n = max(1, min(a.n, len(VARIANTS)))
        for i in range(n):
            path = a.out if n == 1 else f"{base}_{i + 1}.md"
            jobs.append((path, WRITE_PROMPT.format(variant=VARIANTS[i])))

    results = []
    for path, prompt in jobs:  # 순서대로 호출(동시 호출 시 멈춘 적이 있음)
        raw = os.path.join(work, os.path.basename(path) + ".raw")
        print(f"코덱스 집필 중: {os.path.basename(path)} (생각 수준 {a.effort})", flush=True)
        ok, err = call_codex(work, prompt, raw, a.effort, a.model, a.timeout)
        if not ok:
            results.append((path, None, err))
            print(f"  실패: {err}", flush=True)
            continue
        text = clean(open(raw, encoding="utf-8").read())
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        results.append((path, check(text, brief, verbatim), ""))
        print(f"  완료: {path}", flush=True)

    lines = ["# 에세이 검사 보고서", "", f"- 재료: {a.brief}", f"- 문체 규칙: {', '.join(styles)}",
             f"- 그대로 넣을 것: {len(verbatim)}개", ""]
    worst = 0
    for path, c, err in results:
        lines.append(f"## {os.path.basename(path)}")
        if c is None:
            lines += [f"- 등급: 빨강 (실행 실패: {err})", ""]
            worst = 1
            continue
        if c["grade"] == "빨강":
            worst = 1
        lines.append(f"- 등급: {c['grade']}")
        lines.append(f"- 빠진 필수 문구: {'없음' if not c['missing'] else ''}")
        lines += [f"  - {m}" for m in c["missing"]]
        lines.append(f"- 재료에 없는 숫자: {', '.join(c['new_nums']) if c['new_nums'] else '없음'}")
        lines.append(f"- 금지 표현: {'없음' if not c['banned'] else ''}")
        lines += [f"  - {b}" for b in c["banned"]]
        lines.append(f"- 어미 반복: {', '.join(c['repeats']) if c['repeats'] else '없음'}")
        lines.append(f"- 리듬 참고: {', '.join(c['flags']) if c['flags'] else '없음'} (등급에는 넣지 않음)")
        lines.append("")
    # 리듬 지표 비교표
    cols = [(os.path.basename(p), c["rhythm"]) for p, c, _ in results if c]
    if a.compare and os.path.exists(a.compare):
        cols.insert(0, ("기존 글", rhythm(open(a.compare, encoding="utf-8").read())))
    if cols:
        keys = list(cols[0][1].keys())
        lines += ["## 리듬 지표", "", "| 지표 | " + " | ".join(n for n, _ in cols) + " |",
                  "|---|" + "---:|" * len(cols)]
        for k in keys:
            lines.append(f"| {k} | " + " | ".join(str(r[k]) for _, r in cols) + " |")
        lines += ["", "변동계수가 클수록 긴 문장과 짧은 문장이 섞여 있다. 참고용이다. 내용이 풍부해지면 문장이 길어져 수치가 내려가기도 하니, 최종 판단은 읽어 보고 한다."]
    rep = base + ".report.md"
    with open(rep, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"보고서: {rep}")
    return worst


if __name__ == "__main__":
    sys.exit(main())
