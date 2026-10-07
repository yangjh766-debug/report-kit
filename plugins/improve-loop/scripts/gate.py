# -*- coding: utf-8 -*-
"""개선 루프 종료 관문(Stop 훅).

Claude가 대화를 끝내려 할 때 실행된다. 프로젝트 폴더의 .loop/state.json을 보고,
루프가 진행 중(status=running)인데 목표 점수와 최대 라운드 어느 쪽에도 닿지 않았으면
끝내지 못하게 하고 다음 라운드를 진행하라고 Claude에게 알려 준다.

- state.json이 없거나 status가 running이 아니면 아무것도 하지 않는다(다른 작업에는 영향 없음).
- 같은 라운드에서 세 번 넘게 붙잡았는데 라운드가 늘지 않으면 놓아주고 status를 stalled로 바꾼다(무한 반복 방지).
"""
import json, sys
from pathlib import Path

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

state_path = Path(data.get("cwd") or ".") / ".loop" / "state.json"
if not state_path.exists():
    sys.exit(0)
try:
    st = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    sys.exit(0)

if st.get("status") != "running":
    sys.exit(0)

rnd, score = int(st.get("round", 0)), float(st.get("score", 0))
target, max_rounds = float(st.get("target", 90)), int(st.get("max_rounds", 4))

if score >= target or rnd >= max_rounds:
    sys.exit(0)   # 끝낼 조건에 닿았다. 스킬이 status를 정리한다.

# 같은 라운드에서 계속 붙잡히면 놓아준다
gate = st.get("_gate", {})
if gate.get("round") == rnd:
    gate["count"] = gate.get("count", 0) + 1
else:
    gate = {"round": rnd, "count": 1}
st["_gate"] = gate
if gate["count"] > 3:
    st["status"] = "stalled"
    state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0)
state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

reason = (f"개선 루프가 아직 끝나지 않았다: 라운드 {rnd}/{max_rounds}, 점수 {score:g}/{target:g}. "
          f"improve-loop 스킬의 절차대로 직전 review.json의 must_fix를 반영해 라운드 {rnd + 1}을 진행하라. "
          "사람의 판단이 꼭 필요해 멈춰야 한다면 .loop/state.json의 status를 'paused'로 바꾸고 이유를 알린 뒤 멈춰라.")
print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
sys.exit(0)
