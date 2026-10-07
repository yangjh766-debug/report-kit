#!/bin/zsh
# pptx를 슬라이드별 PNG로 뽑는다(미리보기 확인용).
# 사용: zsh render_preview.sh 덱.pptx 출력폴더
# - AppleScript의 open 명령은 Keynote가 자주 충돌해서 쓰지 않는다. macOS 기본 open으로 열고,
#   문서가 목록에 나타날 때까지 기다린 뒤 그 문서만 이름으로 집어 내보내고 닫는다(다른 문서는 건드리지 않음).
set -e
src="${1:A}"; out="${2:A}"
name=$(python3 -c "import sys,unicodedata,os;print(unicodedata.normalize('NFC',os.path.splitext(os.path.basename(sys.argv[1]))[0]))" "$src")   # 한글 파일명은 NFC로 맞춰야 Keynote가 찾는다
[[ -f "$src" ]] || { echo "파일 없음: $src"; exit 1; }
rm -rf "$out"; mkdir -p "$out"
open -a Keynote "$src"
for i in {1..60}; do
  if osascript -e 'tell application "Keynote" to get name of every document' 2>/dev/null | python3 -c "import sys,unicodedata;sys.exit(0 if unicodedata.normalize('NFC',sys.argv[1]) in unicodedata.normalize('NFC',sys.stdin.read()) else 1)" "$name"; then break; fi
  sleep 1
done
osascript - "$name" "$out" <<'OSA'
on run argv
  set docName to item 1 of argv
  set outDir to item 2 of argv
  tell application "Keynote"
    set d to document docName
    export d to (POSIX file outDir) as slide images with properties {image format:PNG}
    close d saving no
  end tell
end run
OSA
echo "그림 $(ls "$out" | wc -l | tr -d ' ')장: $out"
