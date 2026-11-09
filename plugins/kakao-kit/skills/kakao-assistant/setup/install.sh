#!/bin/zsh
# 카톡 비서 설치. 이 스크립트는 다음만 한다. 예약 켜기는 schedule.sh on 으로 따로 한다.
#   1. kakao-mcp 를 검토한 커밋으로 받고 파이썬 의존성 설치
#   2. kakaocli 를 받아 보내기, 로그인, 동기화 명령을 지운 읽기 전용판으로 빌드 (보내기 도구는 빌드하지 않음)
#   3. ~/.config/kakao-mcp/config.json 을 보내기 꺼진 상태로 만들기
#   4. 비서 코드를 APP_DIR 로 복사하고 실행기(bin/KakaoAssistant)를 빌드
# 이미 설치돼 있으면 코드만 새로 복사한다. 실행기는 없을 때만 빌드한다(다시 빌드하면 전체 디스크 접근 권한을 다시 줘야 한다).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

SKILL="${0:A:h:h}"
APP_DIR="${APP_DIR:-$HOME/code/kakao-assistant}"
MCP_DIR="${KAKAO_MCP_DIR:-$HOME/code/kakao-mcp}"
MCP_REPO="https://github.com/Jaeha0526/kakao-mcp.git"
MCP_COMMIT="028588f447536ae4f9b06f54dbf2c876246292cc"
CLI_REPO="https://github.com/Jaeha0526/kakaocli.git"
CLI_COMMIT="2c74e63d2c8846c50d8eb1895eb6d835bfef4bc9"
B="$HOME/.local/share/kakao-mcp"

need() { command -v "$1" >/dev/null 2>&1 || { echo "필요한 프로그램이 없습니다: $1 ($2)"; exit 1; }; }
need git "Xcode 명령줄 도구: xcode-select --install"
need swift "Xcode 명령줄 도구: xcode-select --install"
need brew "Homebrew: https://brew.sh"
need uv "brew install uv"
brew list sqlcipher >/dev/null 2>&1 || { echo "sqlcipher 가 없습니다. brew install sqlcipher 를 먼저 실행하세요."; exit 1; }

checkout() {  # 저장소 커밋 폴더
  [[ -d "$3/.git" ]] || git clone --quiet "$1" "$3"
  git -C "$3" fetch --quiet origin
  git -C "$3" -c advice.detachedHead=false checkout --quiet "$2"
  [[ "$(git -C "$3" rev-parse HEAD)" == "$2" ]] || { echo "$3 의 커밋이 예상과 다릅니다"; exit 1; }
}

echo "==> 1. kakao-mcp ${MCP_COMMIT:0:7}"
checkout "$MCP_REPO" "$MCP_COMMIT" "$MCP_DIR"
(cd "$MCP_DIR" && uv sync --quiet)

echo "==> 2. 읽기 전용 kakaocli ${CLI_COMMIT:0:7}"
mkdir -p "$B/src" "$B/bin"
SRC="$B/src/kakaocli-readonly"
if [[ -d "$SRC/.git" ]]; then git -C "$SRC" checkout --quiet -- .; else rm -rf "$SRC"; fi
checkout "$CLI_REPO" "$CLI_COMMIT" "$SRC"
F="$SRC/Sources/KakaoCLI/KakaoCLI.swift"
sed -i '' -E '/^[[:space:]]+(AuthCommand|HarvestCommand|LoginCommand|SendCommand|SyncCommand)\.self,$/d' "$F"
(cd "$SRC" && swift build -c release --disable-sandbox 2>&1 | grep -E "error|Build complete" | tail -3)
otool -L "$SRC/.build/release/kakaocli" | grep -q sqlcipher || { echo "kakaocli 가 sqlcipher 와 연결되지 않았습니다"; exit 1; }
install -m 0755 "$SRC/.build/release/kakaocli" "$B/bin/kakaocli"
rm -f "$B/bin/kmsg"
if "$B/bin/kakaocli" --help 2>&1 | grep -qE "^  (send|sync|login|auth|harvest) "; then
  echo "보내기 명령이 남아 있어 중단합니다"; exit 1
fi

echo "==> 3. 설정 파일 (보내기 끔)"
CFG_DIR="$HOME/.config/kakao-mcp"
mkdir -p "$CFG_DIR" && chmod 700 "$CFG_DIR"
python3 -I - "$CFG_DIR/config.json" "$B/bin/kakaocli" <<'EOF'
import json, os, sys
path, cli = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
except (OSError, ValueError):
    d = {"user_id": None, "read": {"exclude_chat_ids": [], "default_messages": 100, "max_messages": 1000},
         "media": {"max_download_mb": 200}}
d["kakaocli_path"] = cli
d["kmsg_path"] = "/nonexistent/kmsg-disabled"
d["send"] = {"enabled": False, "allowed_chats": {}, "max_length": 1000, "confirm_ttl_seconds": 300}
old = os.umask(0o077)
json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
os.umask(old)
os.chmod(path, 0o600)
print("사용자 번호:", "저장돼 있음" if d.get("user_id") else "아직 없음 (setup/find_user_id.py 실행)")
EOF

echo "==> 4. 비서 코드를 $APP_DIR 로 복사"
mkdir -p "$APP_DIR/bin" "$APP_DIR/logs" "$APP_DIR/inbox/done"
rsync -a --exclude settings.example.env --exclude filter.json "$SKILL/app/" "$APP_DIR/"
cp "$SKILL/app/settings.example.env" "$APP_DIR/"
[[ -f "$APP_DIR/filter.json" ]] || cp "$SKILL/app/filter.json" "$APP_DIR/"
[[ -f "$APP_DIR/settings.env" ]] || { cp "$SKILL/app/settings.example.env" "$APP_DIR/settings.env"; echo "settings.env 를 만들었습니다. 이름과 폴더를 고치세요."; }
chmod 700 "$APP_DIR/run.sh" "$APP_DIR/logs" "$APP_DIR/inbox"
if [[ ! -x "$APP_DIR/bin/KakaoAssistant" ]]; then
  swiftc -O "$APP_DIR/bin/launcher.swift" -o "$APP_DIR/bin/KakaoAssistant"
  codesign -s - -f -i local.kakao-assistant "$APP_DIR/bin/KakaoAssistant"
  echo "실행기를 새로 만들었습니다. 전체 디스크 접근 권한에 아래 파일을 추가하세요."
  echo "  $APP_DIR/bin/KakaoAssistant"
else
  echo "실행기는 그대로 둡니다 (권한 유지)."
fi
echo "==> 설치 끝"
