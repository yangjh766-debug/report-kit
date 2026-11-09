"""Claude 결과(JSON)를 저장하고 할 일 목록과 대시보드를 새로 만든다.

사용: save_result.py <결과 파일> <수집 파일> <출력 폴더>
- data/<시각>.json: 실행마다 결과 하나
- TASKS.md: 할 일 누적
- 요약/<날짜>.md: 날짜별 읽기용 기록
- 카톡비서.html: 최근 14일 결과를 보여 주는 화면
마지막 줄에 알림용 한 줄을 출력한다.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEEP_DAYS = 14


def parse(result: str) -> dict:
    m = re.search(r"```json\s*(\{.*\})\s*```", result, re.S) or re.search(r"(\{.*\})", result, re.S)
    if not m:
        raise ValueError("결과에서 JSON을 찾지 못했습니다")
    d = json.loads(m.group(1))
    d.setdefault("headline", "")
    for k in ("rooms", "tasks", "drafts", "others", "files"):
        d[k] = d.get(k) or []
    cal = d.get("calendar") or {}
    d["calendar"] = {"added": cal.get("added") or [], "unsure": cal.get("unsure") or []}
    return d


def merge_files(att_dir: Path | None, notes: list[dict]) -> list[dict]:
    """받은 첨부 목록에 Claude가 남긴 요약을 붙인다. 파일은 모두, 사진은 Claude가 열어 본 것만 남긴다."""
    if not att_dir or not (att_dir / "attachments.json").exists():
        return []
    by_id = {str(n.get("id")): n for n in notes}
    out = []
    for a in json.loads((att_dir / "attachments.json").read_text(encoding="utf-8")):
        note = by_id.get(str(a.get("id")), {})
        if a["kind"] != "file" and not note.get("opened"):
            continue
        out.append({**a, "path": str(att_dir / a["file"]) if a.get("file") else None,
                    "opened": bool(note.get("opened")), "summary": note.get("summary") or "",
                    "important": bool(note.get("important"))})
    return out


def to_markdown(stamp: str, d: dict) -> str:
    out = [f"## {stamp}", "", f"**{d['headline']}**" if d["headline"] else ""]
    out += ["", "### 방별 요약"] + [f"- **{r.get('name')}** ({r.get('category', '')}): {r.get('summary', '')}" for r in d["rooms"]]
    if d["others"]:
        out.append(f"- 그 밖의 방: {', '.join(d['others'])}")
    out += ["", "### 할 일"] + ([f"- [ ] {t.get('text')} ({t.get('from', '')}, {t.get('room', '')}{', 마감 ' + t['due'] if t.get('due') else ''})" for t in d["tasks"]] or ["- 없음"])
    out += ["", "### 답장 초안"]
    for x in d["drafts"] or []:
        out += [f"#### {x.get('room')}", f"> {x.get('quote', '')}", f"초안: {x.get('draft', '')}", ""]
    if not d["drafts"]:
        out.append("- 없음")
    if d.get("files"):
        out += ["", "### 받은 파일"]
        out += [f"- {f.get('name') or '사진'} ({f.get('room')}, {f.get('sender')}){': ' + f['summary'] if f.get('summary') else ''}" for f in d["files"]]
    out += ["", "### 캘린더 반영"]
    out += [f"- 넣은 일정: {e.get('when')} {e.get('title')}" for e in d["calendar"]["added"]] or ["- 넣은 일정: 없음"]
    out += [f"- 확인 필요: {e.get('text')}" for e in d["calendar"]["unsure"]]
    return "\n".join(out) + "\n\n---\n\n"


OUT_DIR = Path(os.environ.get("KAKAO_OUT_DIR", Path.home() / "Documents/카톡비서"))
KST = timezone(timedelta(hours=9))


def add_ids(rec: dict) -> dict:
    """할 일과 초안마다 고유 번호를 붙인다. 예전 기록에도 같은 규칙으로 붙는다."""
    base = re.sub(r"\D", "", rec["stamp"])
    for kind, key in (("t", "tasks"), ("d", "drafts")):
        for i, x in enumerate(rec.get(key) or []):
            x.setdefault("id", f"{kind}-{base}-{i}")
    return rec


def load_runs(out_dir: Path) -> list[dict]:
    cutoff = f"{datetime.now() - timedelta(days=KEEP_DAYS):%Y-%m-%d}"
    runs = []
    for p in sorted((out_dir / "data").glob("*.json"), reverse=True):
        if p.name[:10] < cutoff:
            continue
        try:
            runs.append(add_ids(json.loads(p.read_text(encoding="utf-8"))))
        except (OSError, ValueError, KeyError):
            pass
    return runs


def load_done(out_dir: Path) -> dict:
    try:
        return json.loads((out_dir / "done.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def update_done(out_dir: Path, runs: list[dict], done_tasks: list[dict]) -> int:
    """카톡에서 답장한 초안과 Claude가 끝났다고 본 할 일을 자동으로 완료 처리한다."""
    done = load_done(out_dir)
    state = json.loads((HERE / "state.json").read_text(encoding="utf-8")) if (HERE / "state.json").exists() else {}
    my_sent = state.get("my_sent", {})
    before = len(done)
    for r in runs:
        made = datetime.strptime(r["stamp"], "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        for x in r.get("drafts") or []:
            sent = my_sent.get(x.get("room") or "")
            if x["id"] not in done and sent and datetime.fromisoformat(sent) > made:
                done[x["id"]] = f"카톡에서 답장함 ({sent[5:10].replace('-', '/')} {sent[11:16]})"
    open_ids = {x["id"] for r in runs for x in r.get("tasks") or []}
    for t in done_tasks:
        if t.get("id") in open_ids and t["id"] not in done:
            done[t["id"]] = f"자동 완료: {t.get('reason') or '새 대화에서 끝난 것으로 보임'}"
    p = out_dir / "done.json"
    p.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    p.chmod(0o600)
    return len(done) - before


def print_open_tasks(out_dir: Path) -> None:
    """Claude에게 넘길 남은 할 일 목록."""
    done = load_done(out_dir)
    rows = [f"- [{x['id']}] {x.get('text')} ({x.get('room', '')}, {x.get('from', '')}{', 마감 ' + x['due'] if x.get('due') else ''})"
            for r in load_runs(out_dir) for x in r.get("tasks") or [] if x["id"] not in done]
    print("\n".join(rows[:40]) or "없음")


def main() -> None:
    result_path, inbox_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    att_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    now = datetime.now()
    stamp = f"{now:%Y-%m-%d %H:%M}"
    text = inbox_path.read_text(encoding="utf-8") if inbox_path.exists() else ""
    count = sum(int(n) for n in re.findall(r"^# 새 카톡 .*?(\d+)개\)", text, re.M))
    d = parse(result_path.read_text(encoding="utf-8"))
    done_tasks = d.pop("done_tasks", None) or []

    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "요약").mkdir(exist_ok=True)
    rec = add_ids({"stamp": stamp, "count": count, **d, "files": merge_files(att_dir, d.get("files") or [])})
    p = data_dir / f"{now:%Y-%m-%d_%H%M}.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    p.chmod(0o600)

    with (out_dir / "요약" / f"{now:%Y-%m-%d}.md").open("a", encoding="utf-8") as f:
        f.write(to_markdown(stamp, rec))
    if d["tasks"]:
        tasks_md = out_dir / "TASKS.md"
        if not tasks_md.exists():
            tasks_md.write_text("# 할 일\n", encoding="utf-8")
        with tasks_md.open("a", encoding="utf-8") as f:
            f.write(f"\n<!-- 카톡 {stamp} -->\n")
            for t in d["tasks"]:
                f.write(f"- [ ] {t.get('text')} ({t.get('from', '')}, {t.get('room', '')}{', 마감 ' + t['due'] if t.get('due') else ''})\n")

    auto = update_done(out_dir, load_runs(out_dir), done_tasks)
    build_dashboard(out_dir)
    files = f", 받은 파일 {len(rec['files'])}개" if rec["files"] else ""
    autos = f", 자동 완료 {auto}개" if auto else ""
    print(f"할 일 {len(d['tasks'])}개, 답장 초안 {len(d['drafts'])}개, 일정 {len(d['calendar']['added'])}개{files}{autos} | {d['headline'][:60]}")


def build_dashboard(out_dir: Path) -> None:
    runs = load_runs(out_dir)
    template = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    safe = lambda v: json.dumps(v, ensure_ascii=False).replace("</", "<\\/")  # noqa: E731
    html = template.replace("/*__DATA__*/[]", safe(runs)).replace("/*__DONE__*/{}", safe(load_done(out_dir)))
    target = out_dir / "카톡비서.html"
    target.write_text(html, encoding="utf-8")
    target.chmod(0o600)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--rebuild":
        build_dashboard(OUT_DIR)
    elif len(sys.argv) == 2 and sys.argv[1] == "--open-tasks":
        print_open_tasks(OUT_DIR)
    else:
        main()
