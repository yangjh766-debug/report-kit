"""collect.py 가 남긴 첨부 목록(*.attach.json)을 보고 사진과 파일을 받아 온다.

사용: fetch_attachments.py <받을 폴더> <첨부 목록 파일>...
- 카톡 DB는 열지 않고, 카카오 서버에서도 받지 않는다(인터넷을 쓰지 않는다).
- 파일은 내가 카톡에서 저장해 다운로드 폴더에 있는 것만 쓴다. 이름과 크기가 같은 것을 찾는다.
- 사진은 카톡 앱이 암호화해 두므로 열지 않고 목록에만 남긴다.
- Claude가 볼 수 있게 사진은 줄이고, 문서는 글자만 뽑아 <id>_보기.* 로 둔다.
- 받은 폴더에 attachments.json 을 남기고, Claude에게 넘길 첨부 안내를 출력한다.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

MAX_FILES = 8
MAX_PHOTOS = 10
MAX_BYTES = 25 * 1024 * 1024
DOWNLOADS = Path.home() / "Downloads"
MAX_TEXT = 30_000
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".tiff"}
TEXTUTIL_EXTS = {".doc", ".docx", ".rtf", ".odt", ".html", ".htm", ".webarchive"}
PLAIN_EXTS = {".txt", ".csv", ".md", ".json"}


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\n\r\t]', "_", name).strip()[:80] or "첨부"


def office_text(path: Path) -> str:
    """xlsx, pptx 안의 글자만 뽑는다."""
    with zipfile.ZipFile(path) as z:
        if path.suffix.lower() == ".xlsx":
            parts = [n for n in z.namelist() if n == "xl/sharedStrings.xml" or n.startswith("xl/worksheets/sheet")]
        else:
            parts = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                           key=lambda n: int(re.search(r"(\d+)", n).group(1)))
        out = []
        for n in parts:
            xml = z.read(n).decode("utf-8", "ignore")
            words = re.findall(r"<(?:a:t|t|v)[^>]*>([^<]*)</", xml)
            if words:
                out.append(f"[{n.rsplit('/', 1)[-1]}] " + " ".join(w for w in words if w.strip()))
        return "\n".join(out)


def find_saved(name: str | None, size: int | None) -> Path | None:
    """다운로드 폴더에서 카톡으로 받은 파일을 찾는다. 같은 이름이 여럿이면 크기가 같은 것을 고른다."""
    if not name:
        return None
    stem, ext = Path(name).stem, Path(name).suffix
    cands = [p for p in [DOWNLOADS / name, *DOWNLOADS.glob(f"{glob_escape(stem)} (*){glob_escape(ext)}")] if p.is_file()]
    for p in cands:
        if not size or p.stat().st_size == size:
            return p
    return None


def glob_escape(s: str) -> str:
    return re.sub(r"([*?\[])", r"[\1]", s)


def make_view(src: Path, dest: Path) -> Path | None:
    ext = src.suffix.lower()
    try:
        if ext in IMAGE_EXTS:
            subprocess.run(["/usr/bin/sips", "-Z", "1024", "-s", "format", "jpeg", str(src), "--out", str(dest.with_suffix(".jpg"))],
                           capture_output=True, timeout=60, check=True, stdin=subprocess.DEVNULL)
            return dest.with_suffix(".jpg")
        if ext == ".pdf":
            return src
        text = None
        if ext in TEXTUTIL_EXTS:
            r = subprocess.run(["/usr/bin/textutil", "-convert", "txt", "-stdout", str(src)],
                               capture_output=True, timeout=60, check=True, stdin=subprocess.DEVNULL)
            text = r.stdout.decode("utf-8", "ignore")
        elif ext in (".xlsx", ".pptx"):
            text = office_text(src)
        elif ext in PLAIN_EXTS:
            text = src.read_text(encoding="utf-8", errors="ignore")
        if text is not None:
            out = dest.with_suffix(".txt")
            out.write_text(text[:MAX_TEXT] + ("\n...(뒷부분 생략)" if len(text) > MAX_TEXT else ""), encoding="utf-8")
            return out
    except (OSError, subprocess.SubprocessError, zipfile.BadZipFile, ValueError):
        return None
    return None


def main() -> None:
    dest = Path(sys.argv[1])
    items = []
    for man in sys.argv[2:]:
        items += json.loads(Path(man).read_text(encoding="utf-8"))
    if not items:
        return
    dest.mkdir(parents=True, exist_ok=True)
    dest.chmod(0o700)

    files = [i for i in items if i["kind"] == "file"][:MAX_FILES]
    photos = [i for i in items if i["kind"] in ("photo", "photos")][:MAX_PHOTOS]
    skipped = len(items) - len(files) - len(photos)
    done, lines = [], []
    for it in files + photos:
        rec = {k: it.get(k) for k in ("id", "room", "room_kind", "sender", "time", "kind", "name")}
        try:
            if it["kind"] == "file" and (it.get("size") or 0) > MAX_BYTES:
                raise ValueError("파일이 커서 받지 않음")
            if it["kind"] != "file":
                raise ValueError("사진은 열지 않음")
            got = find_saved(it.get("name"), it.get("size"))
            if not got:
                raise ValueError("카톡에서 아직 저장하지 않은 파일")
            orig = dest / f"{it['id']}_{safe(it['name'])}"
            shutil.copyfile(got, orig)
            orig.chmod(0o600)
            view = make_view(orig, dest / f"{it['id']}_보기")
            rec.update(status="ok", file=orig.name, view=view.name if view else None)
        except Exception as e:  # 못 찾은 파일, 용량 초과 등은 건너뛰고 기록만 남긴다
            rec.update(status=f"받지 못함: {str(e)[:80]}", file=None, view=None)
        done.append(rec)
        what = "사진" if it["kind"] != "file" else f"파일 {rec.get('name') or ''}".strip()
        how = f"읽을 파일: {rec['view']}" if rec.get("view") else ("내용을 읽을 수 없는 형식" if rec["status"] == "ok" else rec["status"])
        lines.append(f"- 첨부 {it['id']} ({what}, {it['room']}, 보낸 사람 {it['sender']}): {how}")

    (dest / "attachments.json").write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    if skipped:
        lines.append(f"- 그 밖의 첨부 {skipped}개는 개수 제한으로 받지 않음")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
