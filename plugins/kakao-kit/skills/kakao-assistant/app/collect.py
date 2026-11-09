"""지난 실행 이후 대화가 오간 카톡방을 모두 찾아, 새 메시지만 가림 처리한 뒤 마크다운으로 내보낸다.

- 뺄 방: filter.json 의 exclude_chat_ids(방 번호)와 exclude_types(방 종류)를 읽지 않는다.
  기본으로 "unknown"(광고 채널, 오픈채팅)은 뺀다.
- 이어 읽기: state.json 에 마지막 실행 시각과 방마다 마지막으로 읽은 위치(cursor)를 저장한다.
  처음 실행할 때는 최근 FIRST_RUN_SINCE 만큼만 읽는다.
- 출력: 새 메시지가 있으면 inbox/<시각>.md 를 만들고 그 경로를 출력한다. 없으면 아무것도 출력하지 않는다.
- 첨부: 사진과 파일은 본문에 "[첨부 HHMM-N: 이름]"으로 표시하고, 내려받는 데 필요한 정보는
  inbox/<시각>.attach.json 에 따로 적는다. 파일을 찾아 오는 일은 fetch_attachments.py 가 맡는다.

인터넷 없이 돌도록 run.sh 가 sandbox-exec 안에서 실행한다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(os.environ.get("KAKAO_MCP_DIR", Path.home() / "code/kakao-mcp")) / "src"))

from kakao_mcp import keyderive  # noqa: E402
from kakao_mcp.config import load_config  # noqa: E402
from kakao_mcp.messages import KST, message_view, parse_time  # noqa: E402
from kakao_mcp.runner import KakaoCli  # noqa: E402

from mask import mask  # noqa: E402

FILTER = HERE / "filter.json"
STATE = HERE / "state.json"
INBOX = HERE / "inbox"
FIRST_RUN_SINCE = "1h"
PAGE = 200
MAX_PER_ROOM = 600  # 한 번에 방 하나에서 이보다 많이 오면 뒷부분은 다음 실행에서 읽는다
MAX_CHATS = 200


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def read_new(cli: KakaoCli, chat_id: int, cursor: str | None, since: int, my_id: int | None):
    """cursor(없으면 since 시각) 이후 메시지를 오래된 것부터 읽는다. (메시지 목록, 원본 행, 새 cursor)"""
    rows: list[dict] = []
    if cursor is None:
        rows = cli.history(chat_id=chat_id, since=since, limit=MAX_PER_ROOM)
        rows.reverse()  # 최신순으로 오므로 뒤집는다
    else:
        after = cursor
        while len(rows) < MAX_PER_ROOM:
            page = cli.history(chat_id=chat_id, after=after, limit=PAGE)
            if not page:
                break
            rows += page
            after = page[-1]["cursor"]
            if len(page) < PAGE:
                break
    new_cursor = rows[-1]["cursor"] if rows else cursor
    return [message_view(m, my_user_id=my_id) for m in rows], rows, new_cursor


ATTACH_KINDS = {"photo", "photos", "file"}


def fmt(m: dict, label: str | None = None) -> str:
    t = f"{m['time'][5:7]}/{m['time'][8:10]} {m['time'][11:16]}"
    who = "나" if m["sender"] == "me" else m["sender"]
    body = m.get("text") or ""
    if m.get("attachment"):
        a = m["attachment"]
        what = {"photo": "사진", "photos": f"사진 {a.get('count', '')}장", "file": "파일", "video": "동영상", "voice": "음성"}.get(m["type"], m["type"])
        name = f": {a['name']}" if a.get("name") else ""
        body = (body + " " if body else "") + (f"[첨부 {label} {what}{name}]" if label else f"[{what}{name}]")
    elif not body:
        body = f"[{m['type']}]"
    if m.get("reply_to"):
        body = f"(답장: \"{(m['reply_to'].get('text') or '')[:40]}\") {body}"
    return f"- {t} {who}: {mask(body)}"


def utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def main() -> None:
    flt = load_json(FILTER, {})
    excluded = {int(x) for x in flt.get("exclude_chat_ids", [])}
    excluded_types = set(flt.get("exclude_types", ["unknown"]))
    state = load_json(STATE, {})
    cursors: dict[str, str] = state.get("cursors", {})
    my_sent: dict[str, str] = state.get("my_sent", {})  # 방 이름별로 내가 마지막에 보낸 시각 (답장 자동 체크용)
    started = datetime.now(timezone.utc)
    last_run = utc(state["last_run"]) if state.get("last_run") else None
    since = int(last_run.timestamp()) if last_run else parse_time(FIRST_RUN_SINCE)

    config = load_config()
    if config.user_id is None:
        sys.exit("config.json 에 user_id 가 없습니다.")
    uid = config.user_id
    cli = KakaoCli(config.kakaocli_path, resolve_db=lambda: keyderive.resolve_database(uid))

    now = datetime.now(KST)
    sections, total, attachments = [], 0, []
    for c in cli.chats(MAX_CHATS):
        cid = str(c["id"])
        if c["id"] in excluded or c.get("type") in excluded_types:
            continue
        if not c.get("last_message_at") or utc(c["last_message_at"]).timestamp() < since:
            continue
        msgs, raw, cursor = read_new(cli, c["id"], cursors.get(cid), since, uid)
        if cursor:
            cursors[cid] = cursor
        if not msgs:
            continue
        total += len(msgs)
        kind = {"direct": "1:1", "group": f"{c.get('member_count')}명 단체방", "self": "나와의 채팅"}.get(c.get("type"), "")
        lines = []
        for m, r in zip(msgs, raw):
            label = None
            if m["type"] in ATTACH_KINDS and m.get("attachment"):
                label = f"{now:%H%M}-{len(attachments) + 1}"
                attachments.append({
                    "id": label, "room": c.get("display_name"), "room_kind": kind,
                    "sender": "나" if m["sender"] == "me" else m["sender"], "time": m["time"],
                    "kind": m["type"], "name": m["attachment"].get("name"), "size": m["attachment"].get("size"),
                    "row": {k: r.get(k) for k in ("chat_id", "log_id", "type_code", "attachment", "local_file_path")},
                })
            lines.append(fmt(m, label))
            if m["sender"] == "me":
                my_sent[c.get("display_name")] = m["time"]
        sections.append(f"## {c.get('display_name')} ({kind}, 새 메시지 {len(msgs)}개)\n" + "\n".join(lines))

    state = {"last_run": started.isoformat(), "cursors": cursors, "my_sent": my_sent}
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    STATE.chmod(0o600)
    if not total:
        return
    INBOX.mkdir(exist_ok=True)
    out = INBOX / f"{now:%Y-%m-%d_%H%M}.md"
    if attachments:
        man = out.with_suffix(".attach.json")
        man.write_text(json.dumps(attachments, ensure_ascii=False, indent=1), encoding="utf-8")
        man.chmod(0o600)
    out.write_text(f"# 새 카톡 ({now:%Y-%m-%d %H:%M} 기준, {total}개)\n\n" + "\n\n".join(sections) + "\n",
                   encoding="utf-8")
    out.chmod(0o600)
    print(out)


if __name__ == "__main__":
    main()
