"""카톡 DB를 여는 데 필요한 내 카카오 사용자 번호를 찾아 config.json 에 저장한다.

kakaocli 의 자동 찾기(무차별 대입)가 안 되는 맥에서 쓴다. 무차별 대입 대신 이렇게 찾는다.
- 카톡 설정 파일에는 사용자 번호가 SHA-512 해시로만 남아 있다(...REVISION:<해시> 키, 값이 True인 것).
- 카톡 앱 폴더의 파일에서 6~11자리 숫자를 모아 그 해시와 맞는 것을 고른다.
- 맞는 번호로 DB 파일 이름을 계산해 실제 파일이 있는지 한 번 더 확인한다.

번호는 화면에 출력하지 않는다. 인터넷 없이 돌도록 sandbox-exec 안에서 실행한다.
  sandbox-exec -p '(version 1)(allow default)(deny network*)' ~/code/kakao-mcp/.venv/bin/python -I find_user_id.py
"""
import hashlib
import json
import os
import plistlib
import re
import sys
from pathlib import Path

home = Path.home()
sys.path.insert(0, str(Path(os.environ.get("KAKAO_MCP_DIR", home / "code/kakao-mcp")) / "src"))
from kakao_mcp.keyderive import CONTAINER, database_name, platform_uuid  # noqa: E402

CFG = home / ".config/kakao-mcp/config.json"
BASE = home / "Library/Containers/com.kakao.KakaoTalkMac/Data"
PLIST = BASE / "Library/Preferences/com.kakao.KakaoTalkMac.plist"


def main() -> None:
    cfg = json.loads(CFG.read_text())
    if cfg.get("user_id"):
        print("이미 저장돼 있습니다.")
        return
    pl = plistlib.loads(PLIST.read_bytes())
    empty = hashlib.sha512(b"0").hexdigest()
    targets = {k.split(":", 1)[1] for k, v in pl.items()
               if re.match(r"[A-Z]+REVISION:[0-9a-f]{128}$", k) and v and k.split(":", 1)[1] != empty}
    if not targets:
        sys.exit("카톡 설정 파일에서 해시를 찾지 못했습니다. 카톡에 로그인돼 있는지 확인하세요.")

    skip = re.compile(r"^[0-9a-f]{78}(\.db)?(-wal|-shm)?$")  # 암호화된 DB 는 건너뛴다
    nums = set()
    for p in BASE.rglob("*"):
        if not p.is_file() or skip.match(p.name) or "WebKit" in p.parts:
            continue
        try:
            if p.stat().st_size > 20_000_000:
                continue
            nums.update(m.group() for m in re.finditer(rb"(?<!\d)\d{6,11}(?!\d)", p.read_bytes()))
        except OSError:
            pass

    uuid = platform_uuid()
    names = {p.name for p in CONTAINER.iterdir()}
    hit = [int(n) for n in nums if hashlib.sha512(n).hexdigest() in targets]
    hit = [n for n in hit if database_name(n, uuid) in names or database_name(n, uuid) + ".db" in names]
    if len(hit) != 1:
        sys.exit(f"확인된 번호가 하나가 아닙니다 ({len(hit)}개). 저장하지 않았습니다.")
    cfg["user_id"] = hit[0]
    CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    CFG.chmod(0o600)
    print("찾아서 저장했습니다 (DB 파일 이름으로 확인함).")


if __name__ == "__main__":
    main()
