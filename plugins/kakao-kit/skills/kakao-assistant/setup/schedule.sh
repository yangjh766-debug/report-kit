#!/bin/zsh
# 카톡 비서 예약 켜기, 끄기, 시험 실행
#   schedule.sh on      settings.env 의 근무시간대로 평일 매시 정각 실행을 등록한다
#   schedule.sh off     예약을 지운다
#   schedule.sh test    지금 한 번 돌린다 (근무시간이 아니어도)
#   schedule.sh status  등록 상태와 최근 기록을 본다
set -euo pipefail
APP_DIR="${APP_DIR:-$HOME/code/kakao-assistant}"
LABEL="local.kakao-assistant"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
[[ -f "$APP_DIR/settings.env" ]] && source "$APP_DIR/settings.env"

case "${1:-status}" in
  on)
    mkdir -p "$HOME/Library/LaunchAgents"
    python3 -I - "$PLIST" "$APP_DIR" "${WORK_START:-9}" "${WORK_END:-19}" <<'EOF'
import plistlib, sys
path, app, start, end = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
plistlib.dump({
    "Label": "local.kakao-assistant",
    "ProgramArguments": [f"{app}/bin/KakaoAssistant"],
    "StartCalendarInterval": [{"Weekday": w, "Hour": h, "Minute": 0} for w in range(1, 6) for h in range(start, end + 1)],
    "StandardOutPath": f"{app}/logs/launchd.log",
    "StandardErrorPath": f"{app}/logs/launchd.log",
}, open(path, "wb"))
EOF
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST"
    echo "예약 켬: 평일 ${WORK_START:-9}시부터 ${WORK_END:-19}시까지 매시 정각"
    ;;
  off)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null && echo "예약 끔" || echo "등록된 예약이 없습니다"
    ;;
  test)
    touch "$APP_DIR/.force_once"
    launchctl kickstart -k "$DOMAIN/$LABEL"
    echo "시험 실행 시작. 1~2분 뒤 $APP_DIR/logs/run.log 를 확인하세요."
    ;;
  status)
    launchctl print "$DOMAIN/$LABEL" 2>/dev/null | grep -E "^\s+(state|last exit code)" || echo "예약이 등록돼 있지 않습니다"
    tail -n 8 "$APP_DIR/logs/run.log" 2>/dev/null || true
    ;;
  *) echo "사용: schedule.sh on|off|test|status"; exit 1 ;;
esac
