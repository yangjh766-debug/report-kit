#!/bin/zsh
# 매시 실행: 새 카톡 수집(인터넷 차단) 후, 처리할 메시지가 있을 때만 Claude로 요약한다.
# Claude에게는 Gmail 초안과 캘린더 도구만 허락한다. 카톡 도구, 파일 읽기, 명령 실행은 막는다.
# 실패하면 수집 파일을 inbox/ 에 남겨 두고 다음 실행 때 같이 처리한다.
set -euo pipefail
setopt null_glob

# 예약 실행에서는 환경 변수가 거의 비어 있다. claude가 키체인에서 로그인 정보를 찾으려면 USER가 필요하다.
export USER="${USER:-$(id -un)}" LOGNAME="${LOGNAME:-$(id -un)}"

HERE="${0:A:h}"
# 사람마다 다른 값은 settings.env 에 둔다 (settings.example.env 참고)
[[ -f "$HERE/settings.env" ]] && source "$HERE/settings.env"
OUT="${OUT_DIR:-$HOME/Documents/카톡비서}"
export KAKAO_MCP_DIR="${KAKAO_MCP_DIR:-$HOME/code/kakao-mcp}" KAKAO_OUT_DIR="$OUT"
PY="$KAKAO_MCP_DIR/.venv/bin/python"
CLAUDE="${CLAUDE_BIN:-$(command -v claude || echo /opt/homebrew/bin/claude)}"
LOG="$HERE/logs/run.log"
mkdir -p "$HERE/logs" "$HERE/inbox/done" "$OUT"
exec >>"$LOG" 2>&1
echo "=== $(date '+%F %T') 시작"

notify() { osascript -e "display notification \"${2//\"/}\" with title \"카톡 비서\" subtitle \"$1\"" || true; }

# 평일 근무시간에만 실행한다 (수동 실행은 FORCE=1, schedule.sh test 는 .force_once 를 남긴다)
[[ -f "$HERE/.force_once" ]] && { rm -f "$HERE/.force_once"; FORCE=1; }
if [[ -z "${FORCE:-}" ]]; then
  dow=$(date +%u); hour=$(date +%H)
  if (( dow > 5 || 10#$hour < ${WORK_START:-9} || 10#$hour > ${WORK_END:-19} )); then echo "근무시간 아님, 건너뜀"; exit 0; fi
fi

# 1. 새 카톡 수집: 인터넷을 끊은 상태로 실행한다
new=$(sandbox-exec -p '(version 1)(allow default)(deny network*)' "$PY" -I "$HERE/collect.py")
[[ -n "$new" ]] && echo "수집: $new"
pending=("$HERE"/inbox/*.md)
if (( ${#pending} == 0 )); then echo "새 메시지 없음, Claude 실행 안 함"; exit 0; fi
batch="$HERE/logs/batch.md"
cat "${pending[@]}" > "$batch"
echo "처리할 파일 ${#pending}개"
manifests=("$HERE"/inbox/*.attach.json)

# 2. 첨부 찾기: 카톡 DB도 카카오 서버도 쓰지 않고, 다운로드 폴더에 저장된 파일만 가져온다.
# Claude는 이 폴더 안의 파일만 읽을 수 있다.
att_dir="$OUT/받은파일/$(date '+%Y-%m-%d_%H%M')"
mkdir -p "$att_dir"
att_list=""
if (( ${#manifests} )); then
  att_list=$(sandbox-exec -p '(version 1)(allow default)(deny network*)' "$PY" -I "$HERE/fetch_attachments.py" "$att_dir" "${manifests[@]}") || att_list="- 첨부를 받는 중 오류가 나서 열 수 없음"
  echo "첨부 $(( $(echo "$att_list" | grep -c '^- 첨부') ))개 처리"
fi

# 3. Claude로 요약, 할 일, 답장 초안, 첨부 훑어보기, 캘린더 반영
stamp=$(date '+%Y-%m-%d %H:%M')
result="$HERE/logs/result.md"
set +e
{
  prompt=$(<"$HERE/prompt.md"); prompt=${prompt//\{\{시각\}\}/$stamp}; print -r -- "${prompt//\{\{이름\}\}/${OWNER_NAME:-사용자}}"
  echo; echo "<messages>"; cat "$batch"; echo "</messages>"
  echo; echo "<attachments>"; echo "${att_list:-없음}"; echo "</attachments>"
  echo; echo "<open_tasks>"; "$PY" -I "$HERE/save_result.py" --open-tasks; echo "</open_tasks>"
} | (cd "$att_dir" && "$CLAUDE" -p \
      --model "${CLAUDE_MODEL:-sonnet}" \
      --max-turns 15 \
      --settings '{"disableAllHooks": true}' \
      --allowedTools "Read(./**) mcp__claude_ai_Gmail__create_draft mcp__claude_ai_Google_Calendar__create_event mcp__claude_ai_Google_Calendar__list_events" \
      --disallowedTools "Bash Write Edit MultiEdit Glob Grep NotebookEdit WebFetch WebSearch Agent Task Skill mcp__kakao Read(~/Library/**) Read(~/.config/**) Read(~/.ssh/**) Read(~/.claude/**) Read(~/code/**) Read(/private/**) Read(/etc/**)" \
      --output-format json) >"$HERE/logs/result.json"
set -e
"$PY" -I -c '
import json, sys
d = json.load(open(sys.argv[1]))
open(sys.argv[2], "w").write(d.get("result") or "")
print("턴", d.get("num_turns"), "| API 요금 환산(달러)", round(d.get("total_cost_usd") or 0, 3), "| 거부된 도구", [x.get("tool_name") for x in d.get("permission_denials", [])])
if d.get("is_error"):
    print("Claude 오류:", (d.get("result") or d.get("terminal_reason") or "")[:300])
    sys.exit(1)
' "$HERE/logs/result.json" "$result" || { notify "실패" "요약하지 못했습니다. 다음 실행 때 다시 시도합니다."; exit 1; }

# 4. 답장 초안을 코덱스로 다듬는다. 안 되면 Claude 초안을 그대로 쓴다.
PATH="$HOME/.local/node/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" "$PY" -I "$HERE/polish_drafts.py" "$result" || echo "코덱스 단계 오류, 건너뜀"

# 5. 결과 저장, 대시보드 갱신, Mac 알림
note=$("$PY" -I "$HERE/save_result.py" "$result" "$batch" "$OUT" "$att_dir")
echo "$note"
mv "${pending[@]}" "${manifests[@]}" "$HERE/inbox/done/"
rmdir "$att_dir" 2>/dev/null || true
notify "카톡비서.html에서 확인" "$note"

# 가린 수집 파일은 7일 지나면 지운다
find "$HERE/inbox/done" -type f -mtime +7 -delete
# 받은 첨부는 30일 지나면 지운다
find "$OUT/받은파일" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
echo "=== $(date '+%F %T') 끝"
