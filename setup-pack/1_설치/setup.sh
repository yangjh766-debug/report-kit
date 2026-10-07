#!/bin/zsh
# AI 작업환경 기본 설치 (맥, 관리자 권한 없이)
# 하는 일: node 설치 → codex, gemini CLI 설치 → PATH 등록 → 전역 지침, 에이전트, 보조 도구 복사 → python-docx 설치
# 보고서, 워딩 스킬과 글쓰기 규칙은 report-kit 플러그인으로 따로 받는다(맨 아래 안내).
# 여러 번 실행해도 괜찮다. 이미 있는 설정은 덮어쓰지 않는다. 키나 비밀번호는 다루지 않는다.
set -e
PACK="${0:A:h:h}"            # 이 팩의 최상위 폴더
NODE_VER="v24.20.0"          # LTS. 필요하면 https://nodejs.org/dist/ 에서 최신 v24 번호로 바꾼다

say() { print -P "%F{blue}▶%f $1"; }

# 0) git (맥 기본 개발도구). 없으면 설치 창이 뜬다
if ! xcode-select -p >/dev/null 2>&1; then
  say "git이 없어 Command Line Tools 설치 창을 띄웁니다. 설치가 끝나면 이 스크립트를 다시 실행하세요."
  xcode-select --install; exit 0
fi

# 1) node (~/.local/node, 관리자 권한 불필요)
if [[ ! -x ~/.local/node/bin/node ]]; then
  ARCH=$( [[ $(uname -m) == arm64 ]] && echo arm64 || echo x64 )
  say "node $NODE_VER ($ARCH) 내려받는 중"
  mkdir -p ~/.local && cd ~/.local
  curl -fsSL "https://nodejs.org/dist/$NODE_VER/node-$NODE_VER-darwin-$ARCH.tar.gz" -o node.tgz
  tar xzf node.tgz && rm node.tgz && rm -rf node && mv "node-$NODE_VER-darwin-$ARCH" node
fi
export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"

# 2) PATH를 ~/.zshrc에 등록 (한 번만)
if ! grep -q '.local/node/bin' ~/.zshrc 2>/dev/null; then
  say "~/.zshrc에 PATH 추가"
  print '\n# node, codex, gemini 경로 (AI 작업환경 세팅팩)\nexport PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"\nexport GEMINI_CLI_TRUST_WORKSPACE=true' >> ~/.zshrc
fi

# 3) 코덱스, 제미나이 CLI
say "codex, gemini CLI 설치"
npm install -g @openai/codex @google/gemini-cli >/dev/null

# 4) 전역 지침, 에이전트, 코덱스 진행 보기 도구
say "전역 지침, 에이전트, 보조 도구 복사"
mkdir -p ~/.claude/agents ~/.local/bin
[[ -f ~/.claude/CLAUDE.md ]] || cp "$PACK/3_설정예시/CLAUDE.md" ~/.claude/CLAUDE.md
cp -n "$PACK/3_설정예시/agents/"*.md ~/.claude/agents/ 2>/dev/null || true
cp "$PACK/4_도구/codexlog" ~/.local/bin/ && chmod +x ~/.local/bin/codexlog
if [[ -f ~/.claude/settings.json ]]; then
  say "settings.json이 이미 있어 건드리지 않았습니다. 필요하면 Claude에게 '3_설정예시/settings.json을 내 설정에 합쳐 줘'라고 하세요."
else
  cp "$PACK/3_설정예시/settings.json" ~/.claude/settings.json
fi

# 5) Word 변환에 필요한 파이썬 패키지
say "python-docx, pillow, openpyxl 설치"
python3 -m pip install --user --quiet python-docx pillow openpyxl || say "pip 설치 실패: 나중에 python3 -m pip install --user python-docx pillow openpyxl"

say "완료. 새 터미널을 열고 아래를 차례로 실행하세요."
print "   codex login          # ChatGPT 계정으로 로그인 (브라우저가 열림)"
print "   gemini               # 처음 실행 시 인증 방식 선택 (API 키 권장, 가이드 6단계 참고)"
print ""
print "   그다음 VS Code의 Claude Code 입력창에서 보고서, 워딩 스킬을 받습니다:"
print "   /plugin marketplace add yangjh766-debug/report-kit"
print "   /plugin install report-kit@report-kit"
print "   /plugin install deck-kit@report-kit"
