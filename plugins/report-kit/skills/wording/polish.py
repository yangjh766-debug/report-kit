#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""긴 글을 코덱스(ChatGPT)에게 작게 나눠 맡겨 문장만 다듬고, 결과를 합친 뒤 검증 보고서를 만든다.

사용법:
    python3 polish.py 원문.md 결과.md [--chunk 2000] [--jobs 3] [--timeout 240] [--retry 1] [--style 규칙.md ...] [--fresh]

v2 (2026-09-04) 동작:
  1. 보호: 표(| 줄 묶음), [표제목], (단위:…), <!-- 주석 -->, (출처:…) 단독 줄은 통째로 ⟦보존N⟧ 표식으로 바꿔 코덱스에 보내지 않는다.
     문장 안의 (출처: …)와 [확인 필요: …]도 ⟦출처N⟧ ⟦확인N⟧ 표식으로 바꾼다. 코덱스는 문장만 본다.
  2. 조각: 제목 단위로 자르고 --chunk 글자(기본 2000)를 넘으면 문단 경계에서 다시 자른다. 조각이 작을수록 실수가 적다.
  3. 호출: 조각마다 codex exec(읽기 전용 sandbox)를 프로세스 그룹으로 실행하고, 시간 초과 시 그룹째 죽인다(고아 방지).
  4. 조각별 검증: 숫자 집합, 표식이 원문과 같아야 통과. 실패하면 --retry 횟수만큼 다시 시도하고, 그래도 안 되면 원문을 그대로 둔다.
  5. 이어하기: 결과.work/ 폴더에 조각별 결과를 저장한다. 다시 실행하면 통과한 조각은 건너뛴다(--fresh 로 무시).
  6. 복원 후 전체 검증 보고서(결과.report.md): 등급, 조각별 상태, 숫자, 표식, 제목 대조.
"""
import argparse
import hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

PROMPT = (
    "먼저 context.md 파일을 읽어 이 글이 어떤 문서의 어느 부분인지(문서 목적, 전체 목차, 고정 용어, 앞뒤 문맥)를 파악하라. context.md의 내용은 출력하지 말고 참고만 하라.\n"
    "그다음 {name} 파일의 글을 읽고, 한국어 원어민이 쓴 것처럼 자연스럽고 읽기 좋은 글로 다시 써라. 문서 전체와 어휘, 어투가 일관되게, 앞 조각의 문맥에 자연스럽게 이어지게 써라.\n"
    "이 글은 AI가 쓴 초안이라 표현이 어색할 수 있다. 문장을 합치거나 나누고, 늘리거나 줄여도 된다.\n"
    "지킬 것:\n"
    "- 숫자, 날짜, 금액, 비율, 고유명사는 단 하나도 빼거나 바꾸거나 새로 만들지 마라. 원문의 숫자가 결과에 전부 그대로 있어야 한다.\n"
    "- 사실 관계와 주장은 바꾸지 마라.\n"
    "- 글의 목적과 논리 순서, 제목(#로 시작하는 줄)은 유지하라.\n"
    "- ⟦보존1⟧ ⟦출처2⟧ ⟦확인3⟧ 같은 ⟦…⟧ 표식은 글자 하나 바꾸지 말고, 빼지 말고, 그 자리에 그대로 둬라. ⟦보존N⟧은 표, 표제목, 단위 줄이고, ⟦출처N⟧은 최종 문서에 나타나지 않는 출처 표기이며, ⟦확인N⟧은 확인 사항이다. 표식 앞뒤에 '다음과 같습니다' 같은 안내 문장을 새로 만들어 넣지 마라. 원문에 있는 안내 문장만 다듬어라.\n"
    "- 마크다운 형식을 유지하라.\n"
    "- 설명, 인사말, 코드블록 표시 없이 다시 쓴 본문만 출력하라."
    "{style}{extra}"
)
STYLE_HEADER = "\n\n추가 문체 규칙 (반드시 지켜라):\n"
NUM_RE = re.compile(r"\d[\d,./:-]*\d|\d")
MARK_RE = re.compile(r"⟦(보존|출처|확인)\d+⟧")
BLOCK_LINE = re.compile(r"^\||^\[[^\]]*\]\s*$|^\(단위|^<!--|^\(출처:")
INLINE_SRC = re.compile(r"\(출처:[^()]*(?:\([^()]*\)[^()]*)*\)")
INLINE_CHK = re.compile(r"\[(?:확인 필요|작성 대기)[^\]]*\]")


# ---------- 보호, 복원 ----------
def protect(text: str):
    """표, 표제목, 단위, 주석, 출처 줄과 문장 안 표식을 ⟦…⟧ 표식으로 바꾼다. (보호된 글, 표식→원문 사전)"""
    store: dict[str, str] = {}
    out_lines: list[str] = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        ln = lines[i]
        if BLOCK_LINE.match(ln):
            if ln.startswith("|"):          # 표는 연속 줄을 한 덩어리로
                j = i
                while j < len(lines) and lines[j].startswith("|"):
                    j += 1
                block = "".join(lines[i:j]); i = j
            else:
                block = ln; i += 1
            kind = "출처" if block.startswith("(출처:") or block.startswith("<!--") else "보존"   # 출처, 주석 줄은 문서에 안 보이므로 따로 표시
            key = f"⟦{kind}{len(store) + 1}⟧"
            store[key] = block.rstrip("\n")
            out_lines.append(key + "\n")
            continue
        def _sub(m, kind):
            key = f"⟦{kind}{len(store) + 1}⟧"; store[key] = m.group(0); return key
        ln = INLINE_SRC.sub(lambda m: _sub(m, "출처"), ln)
        ln = INLINE_CHK.sub(lambda m: _sub(m, "확인"), ln)
        out_lines.append(ln); i += 1
    return "".join(out_lines), store


def restore(text: str, store: dict[str, str]) -> str:
    return MARK_RE.sub(lambda m: store.get(m.group(0), m.group(0)), text)


# ---------- 조각 ----------
def split_chunks(text: str, limit: int) -> list[str]:
    sections: list[str] = []; cur: list[str] = []
    for line in text.splitlines(keepends=True):
        if re.match(r"^#{1,4} ", line) and cur:
            sections.append("".join(cur)); cur = []
        cur.append(line)
    if cur: sections.append("".join(cur))
    chunks: list[str] = []
    for sec in sections:
        if len(sec) <= limit:
            chunks.append(sec); continue
        buf = ""
        for p in re.split(r"(\n\s*\n)", sec):
            if len(buf) + len(p) > limit and buf.strip():
                chunks.append(buf); buf = ""
            buf += p
        if buf.strip(): chunks.append(buf)
    merged: list[str] = []
    for c in chunks:
        if merged and len(merged[-1]) + len(c) <= limit: merged[-1] += c
        else: merged.append(c)
    return merged


def prose_len(chunk: str) -> int:
    return len(MARK_RE.sub("", chunk))


# ---------- 코덱스 호출 ----------
def kill_tree(pid: int) -> None:
    """pid의 자손 프로세스를 모두 찾아 SIGKILL (macOS: ps로 부모-자식 관계를 읽는다). codex 런처가 새 세션을 만들면 killpg만으로는 남는다."""
    try:
        out = subprocess.run(["ps", "-eo", "pid=,ppid="], capture_output=True, text=True).stdout
    except Exception:
        return
    children: dict[int, list[int]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    stack = [pid]; seen: list[int] = []
    while stack:
        p = stack.pop(); seen.append(p); stack += children.get(p, [])
    for p in reversed(seen):
        try: os.kill(p, signal.SIGKILL)
        except Exception: pass


def build_context(chunks: list[str], idx: int, doc: str) -> str:
    """조각마다 코덱스에 함께 주는 문서 맥락: 문서 설명, 전체 목차(이 조각 위치 표시), 앞 조각 끝, 뒤 조각 시작 문맥.
    (사용자 지시 2026-09-05: 조각만 주면 단어 선택이 뒤죽박죽 되므로 전체 맥락을 같이 준다)"""
    heads = []
    for i, c in enumerate(chunks):
        for ln in c.splitlines():
            if ln.startswith("#"): heads.append((i, ln.strip()))
    title = next((h for i, h in heads if h.startswith("# ")), "")
    outline = "\n".join(("▶ " if i == idx else "  ") + h for i, h in heads if h.count("#") <= 4)
    def prose(t: str) -> str:
        return "\n".join(l for l in t.splitlines() if l.strip() and not l.startswith("#") and not MARK_RE.fullmatch(l.strip()))
    prev = prose(chunks[idx - 1])[-600:] if idx > 0 else "(문서 시작)"
    nxt = prose(chunks[idx + 1])[:400] if idx + 1 < len(chunks) else "(문서 끝)"
    return (f"# 문서 맥락 (참고용, 출력 금지)\n\n## 문서\n{doc or title or '(제목 없음)'}\n"
            f"이 조각은 전체 {len(chunks)}조각 중 {idx + 1}번째다. 목차에서 ▶ 표시가 이 조각에 들어 있는 절이다.\n\n"
            f"## 전체 목차\n{outline}\n\n## 앞 조각의 끝(이미 다듬어진 문체로 이어질 부분, 수정 대상 아님)\n{prev}\n\n## 뒤 조각의 시작(수정 대상 아님)\n{nxt}\n\n"
            "## 어휘 일관성\n- 같은 대상은 문서 전체에서 같은 낱말로 부른다(예: 당사, 제품명, 고객사, 매출액). 조각마다 다른 낱말로 바꾸지 마라.\n- ⟦보존N⟧은 표, 표제목, 단위, ⟦출처N⟧은 최종 문서에 나오지 않는 출처 표기다. 표식 앞뒤에 새 문장(예: '다음과 같습니다')을 만들어 넣지 말고 원문 문장만 다듬어라.\n")


def call_codex(d: str, chunk: str, timeout: int, style: str, extra: str, context: str = "") -> tuple[str, str]:
    os.makedirs(d, exist_ok=True)
    name = "draft.md"
    with open(os.path.join(d, name), "w", encoding="utf-8") as f: f.write(chunk)
    with open(os.path.join(d, "context.md"), "w", encoding="utf-8") as f: f.write(context)
    out = os.path.abspath(os.path.join(d, "polished.md"))   # cwd=d 로 실행하므로 -o 는 절대경로여야 한다 (2026-09-10 수정: 상대경로면 결과 파일 없음)
    if os.path.exists(out): os.remove(out)
    cmd = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", "-o", out,
           PROMPT.format(name=name, style=style, extra=extra)]
    # stdin을 닫아 준다: codex는 stdin이 열려 있으면 "Reading additional input from stdin..." 상태로 끝없이 기다릴 수 있다(2026-09-05 원인 추정)
    proc = subprocess.Popen(cmd, cwd=d, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)                       # 자식 codex(별도 세션을 만들기도 함)까지 트리째 종료
        try: os.killpg(proc.pid, signal.SIGKILL)
        except Exception: pass
        proc.wait()
        return "", "시간 초과"
    if not os.path.exists(out): return "", "결과 파일 없음"
    with open(out, encoding="utf-8") as f: result = f.read()
    result = re.sub(r"^```[a-z]*\n", "", result.strip()); result = re.sub(r"\n```$", "", result)
    if not result.strip(): return "", "빈 결과"
    return result.rstrip("\n") + "\n", ""


def check_chunk(orig: str, res: str) -> str:
    """조각 검증. 문제 없으면 빈 문자열."""
    o_n, r_n = set(NUM_RE.findall(orig)), set(NUM_RE.findall(res))
    probs = []
    if o_n - r_n: probs.append("숫자 사라짐 " + ", ".join(sorted(o_n - r_n)[:8]))
    if r_n - o_n: probs.append("숫자 생김 " + ", ".join(sorted(r_n - o_n)[:8]))
    o_m, r_m = sorted(MARK_RE.findall(orig) and re.findall(r"⟦[^⟧]+⟧", orig)), sorted(re.findall(r"⟦[^⟧]+⟧", res))
    if o_m != r_m: probs.append(f"표식 불일치(원문 {len(o_m)}, 결과 {len(r_m)})")
    # 출처 표식(문서에 안 나옴) 바로 앞에 '다음과 같습니다' 안내 문장을 새로 만들어 넣었는지
    def intro_before_src(t: str):
        ls = [l.strip() for l in t.splitlines() if l.strip()]; hits = []
        for a, b in zip(ls, ls[1:]):
            if re.match(r"^⟦출처\d+⟧$", b) and re.search(r"다음과 같습니다\.?$", a): hits.append(a[-30:])
        return hits
    added = [h for h in intro_before_src(res) if h not in intro_before_src(orig)]
    if added: probs.append("출처 표식 앞에 안내 문장 추가 " + " / ".join(added[:3]))
    return "; ".join(probs)


def polish_chunk(idx: int, chunk: str, workdir: str, timeout: int, style: str, retry: int, fresh: bool, context: str = ""):
    """(idx, 결과, 상태문자열). 캐시가 있으면 재사용(조각, 문체 규칙, 맥락이 같을 때)."""
    key = hashlib.sha1((chunk + style + context).encode("utf-8")).hexdigest()[:12]
    d = os.path.join(workdir, f"part{idx:02d}_{key}")
    ok_path = os.path.join(d, "ok.md")
    if not fresh and os.path.exists(ok_path):
        with open(ok_path, encoding="utf-8") as f: return idx, f.read(), "캐시"
    if not chunk.strip() or prose_len(chunk) < 20:          # 표식만 있거나 거의 빈 조각은 보낼 필요 없음
        return idx, chunk, "생략(문장 없음)"
    extra = ""; last = ""
    t0 = time.time()
    for attempt in range(retry + 1):
        res, err = call_codex(os.path.join(d, f"try{attempt}"), chunk, timeout, style, extra, context)
        if err: last = err
        else:
            last = check_chunk(chunk, res)
            if not last:
                with open(ok_path, "w", encoding="utf-8") as f: f.write(res)
                return idx, res, f"완료({attempt + 1}회, {time.time() - t0:.0f}초)"
        extra = f"\n\n주의: 이전 시도가 실패했다 ({last}). 원문의 숫자와 ⟦…⟧ 표식을 하나도 빠뜨리지 마라."
        print(f"  조각 {idx + 1}: {attempt + 1}회 실패 - {last}", flush=True)
    return idx, chunk, f"실패({last}) → 원문 유지"


# ---------- 전체 검증 ----------
def headings(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if re.match(r"^#{1,6} ", l)]


def verify(original: str, polished: str, status: list[tuple[int, int, str]]) -> tuple[str, str]:
    problems: list[str] = []; notes: list[str] = []
    o_nums, p_nums = NUM_RE.findall(original), NUM_RE.findall(polished)
    missing = sorted(set(o_nums) - set(p_nums)); added = sorted(set(p_nums) - set(o_nums))
    if missing: problems.append("원문에 있던 숫자가 결과에서 사라짐: " + ", ".join(missing[:20]))
    if added: problems.append("원문에 없던 숫자가 결과에 생김: " + ", ".join(added[:20]))
    for label, pat in (("[확인 필요] 표식", r"\[(?:확인 필요|작성 대기)[^\]]*\]"), ("(출처: …) 표식", r"\(출처:[^)]*\)")):
        o_m, p_m = sorted(re.findall(pat, original)), sorted(re.findall(pat, polished))
        if o_m != p_m: problems.append(f"{label}이 달라짐 (원문 {len(o_m)}개, 결과 {len(p_m)}개)")
    o_t, p_t = [l for l in original.splitlines() if l.startswith("|")], [l for l in polished.splitlines() if l.startswith("|")]
    if o_t != p_t: problems.append(f"표 줄이 달라짐 (원문 {len(o_t)}줄, 결과 {len(p_t)}줄)")
    if MARK_RE.search(polished): problems.append("복원되지 않은 ⟦…⟧ 표식이 남음")
    o_h, p_h = headings(original), headings(polished)
    if o_h != p_h: notes.append(f"제목 구성이 달라짐 (원문 {len(o_h)}개, 결과 {len(p_h)}개)")
    failed = [s for s in status if s[2].startswith("실패")]
    if failed: problems.append(f"실패해 원문을 그대로 둔 조각 {len(failed)}개: " + ", ".join(f"{s[0]}번" for s in failed) + " → 결과를 쓰면 안 됨(빨강). 다시 실행하면 통과한 조각은 캐시에서 재사용")
    grade = "빨강, 차단" if problems else ("노랑, 검토" if notes else "녹색, 통과")
    lines = ["# 워딩 다듬기 보고서", "", f"- 등급: **{grade}**",
             f"- 원문 {len(original):,}자 / 결과 {len(polished):,}자 (비율 {len(polished) / max(len(original), 1):.0%})",
             f"- 숫자 {len(o_nums)}개 중 그대로 남은 것 {len(o_nums) - len(missing)}개",
             f"- 제목 {len(o_h)}개 {'유지' if o_h == p_h else '변경됨'}, 표 줄 {len(o_t)}줄 {'유지' if o_t == p_t else '변경됨'}", ""]
    if problems: lines += ["## 불일치 (반드시 확인)"] + [f"- {n}" for n in problems] + [""]
    if notes: lines += ["## 참고"] + [f"- {n}" for n in notes] + [""]
    lines += ["## 조각별 상태", "", "| 조각 | 문장 글자 수 | 상태 |", "|---:|---:|---|"] + [f"| {i} | {n:,} | {s} |" for i, n, s in status] + [""]
    return "\n".join(lines), grade


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--chunk", type=int, default=1000, help="조각 최대 글자 수(표 제외). 작을수록 한 번 실패의 손실이 적다")
    ap.add_argument("--jobs", type=int, default=1, help="동시 코덱스 호출 수. 코덱스가 느릴 때는 1")
    ap.add_argument("--timeout", type=int, default=180, help="조각당 제한 시간(초)")
    ap.add_argument("--retry", type=int, default=1, help="조각 실패 시 재시도 횟수")
    ap.add_argument("--style", action="append", default=[], help="문체 규칙 파일(.md). '## 코덱스에게 전달할' 절 아래 '- ' 줄만 전달")
    ap.add_argument("--fresh", action="store_true", help="이전 조각 결과(캐시)를 쓰지 않음")
    ap.add_argument("--doc", default="", help="문서 설명 한두 문장(조각마다 맥락으로 전달). 비우면 첫 제목을 쓴다")
    a = ap.parse_args()

    rules: list[str] = []
    for path in a.style:
        with open(path, encoding="utf-8") as f: raw = f.read()
        m = re.search(r"^## 코덱스에게 전달할[^\n]*\n(.*)", raw, re.S | re.M)
        found = [l for l in (m.group(1) if m else "").splitlines() if l.startswith("- ")]
        print(f"문체 규칙 {len(found)}줄 적용: {path}", flush=True); rules += found
    style = STYLE_HEADER + "\n".join(rules) if rules else ""

    if shutil.which("codex") is None:
        print("codex 명령을 찾을 수 없습니다. PATH에 ~/.local/node/bin 을 넣어 주세요.", file=sys.stderr); return 2

    with open(a.src, encoding="utf-8") as f: original = f.read()
    protected, store = protect(original)
    chunks = split_chunks(protected, a.chunk)
    workdir = re.sub(r"\.md$", "", a.dst) + ".work"
    os.makedirs(workdir, exist_ok=True)
    print(f"원문 {len(original):,}자(문장 {prose_len(protected):,}자, 보호 표식 {len(store)}개) → {len(chunks)}조각, 동시 {a.jobs}개, 조각당 {a.timeout}초, 재시도 {a.retry}회", flush=True)

    results: dict[int, str] = {}; status: list[tuple[int, int, str]] = []
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = [ex.submit(polish_chunk, i, c, workdir, a.timeout, style, a.retry, a.fresh, build_context(chunks, i, a.doc)) for i, c in enumerate(chunks)]
        for fut in futs:
            idx, text, st = fut.result()
            results[idx] = text; status.append((idx + 1, prose_len(chunks[idx]), st))
            print(f"  조각 {idx + 1}/{len(chunks)}: {st}", flush=True)

    polished = "".join(results[i] if results[i].endswith("\n") else results[i] + "\n" for i in range(len(chunks)))
    polished = restore(polished, store)
    with open(a.dst, "w", encoding="utf-8") as f: f.write(polished)
    report, grade = verify(original, polished, status)
    report_path = re.sub(r"\.md$", "", a.dst) + ".report.md"
    with open(report_path, "w", encoding="utf-8") as f: f.write(report)
    print(f"결과: {a.dst}\n보고서: {report_path}\n등급: {grade}")
    return 0 if not grade.startswith("빨강") else 1


if __name__ == "__main__":
    sys.exit(main())
