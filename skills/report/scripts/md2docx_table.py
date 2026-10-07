# -*- coding: utf-8 -*-
"""마크다운 → 표가 예쁜 docx (표 서식 엔진 v4, 이식판).
사용: python3 md2docx_표엔진.py 문서.md [출력.docx]
템플릿: 같은 폴더의 template.docx (환경변수 MD2DOCX_TEMPLATE로 바꿀 수 있다)
규칙(서식지침): 제목 계층 → 제목_Ⅰ./제목_1./제목_가./제목_(1)/제목_(가), 본문 → 본문_표준, [표제목] → 본문_표제목, (단위: …) → 본문_단위,
주1)… → 본문_주석, ![캡션](경로) → 캡션(그림 위)+그림(가운데, 최대 16cm), (출처: …) → docx에는 넣지 않음(--with-sources 옵션일 때만 회색 9pt), [확인 필요…] → 노란 형광, 표 → 머리행 DBE5F1·9pt·숫자 오른쪽 정렬, 열 너비는 내용 비례(균등 분할 금지), 머리행이 출처·근거·원천인 열은 docx에서 뺀다. 변환 뒤 원천 표기 잔존 검사(0건이어야 한다).
v4(2026-09-06): 열 너비를 맑은 고딕 실측 폭(twips)으로 계산하고, 폭이 모자랄 때는 표 전체 행 높이(줄 수 합)가 가장 많이 줄어드는 열부터 폭을 주는 방식(물 채우기)으로 바꿨다.
  이름·회사명 같은 짧은 정보는 구분자(쉼표·가운뎃점·공백·괄호) 사이 조각이 한 줄에 들어가도록 최소 폭을 보장한다."""
import re, sys, copy, math
from pathlib import Path
import docx
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os
ROOT = Path.cwd()   # 그림 상대경로 기준
TEMPLATE = Path(os.environ.get("MD2DOCX_TEMPLATE") or Path(__file__).resolve().parent / "template.docx")
HEAD_STYLE = {1: "제목_Ⅰ.", 2: "제목_1.", 3: "제목_가.", 4: "제목_(1)", 5: "제목_(가)"}

def new_doc():
    d = docx.Document(str(TEMPLATE))
    for c in list(d.comments):   # 양식 docx에 남아 있던 남의 메모는 산출물에 넣지 않는다(2026-09-23)
        c._comment_elm.getparent().remove(c._comment_elm)
    body = d.element.body
    for child in list(body.iterchildren()):
        if child.tag != qn("w:sectPr"): body.remove(child)
    return d

def add_runs(p, text, base_size=None, color=None, italic=False):
    """**굵게**, [확인 필요…] 형광, <br> 줄바꿈 처리."""
    text = re.sub(r"\s*(\[메모:[^\]]*\])", r"\1", text.replace("<br>", "\n"))
    memos = []   # [메모: …] → 워드 메모(검토 의견). 본문에는 남기지 않고 바로 앞 run에 단다(사용자 지시 2026-09-23)
    for chunk in re.split(r"(\*\*[^*]+\*\*|\[확인 필요[^\]]*\]|\[작성 대기[^\]]*\]|\[메모:[^\]]*\])", text):
        if not chunk: continue
        if chunk.startswith("[메모:"):
            if not p.runs: p.add_run("")
            memos.append((p.runs[-1], chunk[4:-1].strip())); continue
        bold = chunk.startswith("**") and chunk.endswith("**")
        flag = chunk.startswith("[확인 필요") or chunk.startswith("[작성 대기")
        t = chunk[2:-2] if bold else chunk
        parts = t.split("\n")
        for i, part in enumerate(parts):
            if i: p.add_run().add_break()
            r = p.add_run(part); r.bold = bold or None; r.italic = italic or None
            if base_size: r.font.size = Pt(base_size)
            if color: r.font.color.rgb = RGBColor.from_string(color)
            if flag: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    for run, memo in memos:
        p.part.document.add_comment(run, text=memo, author="검토", initials="검")

def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill); tcPr.append(shd)

NUM = re.compile(r"^\(?[\d,]+\)?%?$|^-$")
SRC_COLS = {"출처", "근거", "원천", "출처·근거"}   # 마크다운(검토용)에만 두는 열. docx에는 넣지 않는다.
WIDE = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af\u4e00-\u9fff\uff00-\uffef（）]")

# ---------- 글자 폭 실측 ----------
# 표 글꼴(맑은 고딕)로 실제 폭을 잰다. 글꼴이 없으면 반각 1단위 ≈ 95twips(9pt)로 추정한다.
FONT_FILE = Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts/malgun.ttf")
_FONT = {}
try:
    from PIL import ImageFont
    if not FONT_FILE.exists(): raise ImportError
    def _font(size):
        if size not in _FONT: _FONT[size] = ImageFont.truetype(str(FONT_FILE), int(round(size * 20)))   # 1px = 1twip
        return _FONT[size]
    _MEAS = {}
    def measure(s, size=9.0):
        """문자열 한 줄의 폭(twips)."""
        key = (s, size)
        if key not in _MEAS: _MEAS[key] = _font(size).getlength(s)
        return _MEAS[key]
except ImportError:
    def measure(s, size=9.0):
        return sum(2 if WIDE.match(ch) else 1 for ch in s) * 95 * size / 9

def text_width(txt):
    """셀 글자 폭 추정 단위(한글·한자 2, 그 외 1). 여러 줄이면 가장 긴 줄. 정렬 판단 등 폭 배분 외의 용도."""
    plain = re.sub(r"\*\*", "", txt)
    return max((sum(2 if WIDE.match(ch) else 1 for ch in line) for line in re.split(r"<br>|\n", plain)), default=0)

CH, PAD = 95, 175   # CH: 추정용 반각 1단위(9pt). PAD: 셀 여백(좌우 57twips)·테두리·여유(실측과 Word 조판의 차이)
import os
ROOT = Path.cwd()   # 그림 상대경로 기준
DEBUG = bool(os.environ.get("MD2DOCX_DEBUG"))
FLAG = re.compile(r"\[(?:확인 필요|작성 대기|메모:)[^\]]*\]")   # [메모:]는 워드 메모로 빠지므로 폭 계산에서도 표식 취급

def plain_text(c):
    return re.sub(r"\*\*", "", c).strip()

def cell_lines(c):
    return [ln.strip() for ln in re.split(r"<br>|\n", plain_text(c))]

# 줄바꿈 토큰: Word처럼 영문·숫자 덩어리는 통째로, 한글·한자는 글자마다 끊을 수 있다.
TOK = re.compile(r"\s+|[A-Za-z0-9][A-Za-z0-9.,%~\-/:]*|.")
# 조각(atom): 이름·회사명처럼 끊기면 안 되는 단위. 공백·쉼표·가운뎃점·빗금·괄호에서만 나눈다.
def atoms(line):
    return [a for a in re.split(r"\s+|(?<=[,·/])(?!\d)", line) if a]   # 숫자 안의 쉼표(1,234)는 나누지 않는다. 여는 괄호 앞에서는 나누지 않는다(「대표이사(등기)」가 표마다 다르게 접히던 문제, 사용자 지적 2026-09-22)

def latin_piece(line):
    """머리행에서 끊을 수 없는 조각: 영문·숫자 덩어리만(한글은 어디서든 끊긴다)."""
    return max((measure_ref(tk) for tk in re.findall(r"[A-Za-z0-9][A-Za-z0-9.,%~\-/:()]*", line)), default=0)

def est_lines(text, avail, size):
    """셀 글이 폭 avail(twips, 여백 제외)에서 몇 줄로 접히는지 추정한다."""
    n = 0
    for ln in text.split("\n"):
        toks = TOK.findall(ln)
        cur = 0; lines = 1
        for tk in toks:
            w = measure(tk, size)
            if tk.isspace(): cur += w; continue
            if cur + w <= avail or cur == 0 and w <= avail: cur += w
            elif w > avail:   # 한 토큰이 폭보다 길면(긴 영문 단어·숫자) 폭 단위로 쪼개진다
                if cur > 0: lines += 1
                lines += int(w // avail); cur = w - int(w // avail) * avail
            else: lines += 1; cur = w
        n += lines
    return n

def col_widths(rows, total, size=9.0):
    """열 너비 배분(서식지침 4절 '표 너비'). 값은 twips.
    1) 열마다 '접지 않는 폭'(req)과 '최소 폭'(minw)을 잰다.
       - req: 본문 최장 줄(짧은 정보 열은 중앙값의 2배·최소 24단위까지, 긴 글 열은 30단위까지). 머리행은 2줄(글자 줄인 표는 3줄)까지 접는다.
       - minw: 조각(이름·단어) 최장 폭. 그 아래로는 내려가지 않는다(이름이 가운데서 끊기지 않게). 아주 긴 한글 조각은 12자까지만 보장.
       - [확인 필요…] 셀은 '[확인 필요]'만큼만 보장한다(확인 뒤 사라질 글이므로 접혀도 된다. 사용자 지시 2026-09-06).
    2) 다 들어가면 남는 폭을 긴 글 열(70%, 글 양 비례)과 모든 열(30%)에 나눈다. 긴 글 열이 없으면 똑같이 나눈다.
    3) 모자라면 minw에서 시작해 표 전체 줄 수(행마다 가장 긴 셀의 줄 수 합)가 가장 많이 줄어드는 열부터 폭을 준다(물 채우기).
    반환: (twips 목록, 짧은 정보를 접지 않고 맞췄는지)."""
    ncol = max(len(r) for r in rows)
    hl = 2 if size >= 9 else 3
    cols = []
    for j in range(ncol):
        cells = [r[j] if j < len(r) else "" for r in rows]
        hdr_lines = cell_lines(cells[0])
        global measure_ref
        measure_ref = lambda s_: measure(s_, size)
        hdr_total = sum(measure(ln, size) * 1.05 for ln in hdr_lines)   # 머리행은 굵게 → 5% 여유
        hdr_piece = max(max((latin_piece(ln) for ln in hdr_lines), default=0), hdr_total / 3)   # 머리행은 3줄까지 접혀도 된다
        hdr_one = max((measure(ln, size) * 1.05 for ln in hdr_lines), default=0)   # 머리행을 접지 않는 폭
        hdr_req = max(hdr_piece, hdr_total / hl)
        body = []   # (텍스트, 최장줄폭, 조각최장폭, 확인필요 여부)
        for c in cells[1:]:
            t = plain_text(c)
            if not t or t in ("^", "<"): continue
            lines = cell_lines(c)
            full = max(measure(ln, size) for ln in lines)
            flag = bool(FLAG.search(t))
            if flag:
                # [확인 필요: …] 안의 글은 접혀도 된다. 표식 밖 글의 조각과 '[확인 필요]' 폭만 보장.
                outside = FLAG.sub("[확인 필요]", t)
                lines_o = cell_lines(outside)
                full = max(measure(ln, size) for ln in lines_o)
                atom = max((measure(a, size) for ln in lines_o for a in atoms(ln)), default=0)
            else:
                atom = max((measure(a, size) for ln in lines for a in atoms(ln)), default=0)
            body.append((t.replace("<br>", "\n"), full, atom, flag, lines if not flag else lines_o))
        fulls = sorted(b[1] for b in body)
        typical = fulls[len(fulls) // 2] if fulls else 0
        volume = max((sum(measure(ln, size) for ln in b[0].split("\n")) for b in body), default=0)
        maxfull = max((b[1] for b in body), default=0)
        unit = 95 * size / 9   # 단위 → twips 환산(30단위 등 기준값용)
        prose = typical >= 30 * unit or volume >= 100 * unit
        cap = 30 * unit if prose else max(2 * typical, 24 * unit)
        atom_max = max((b[2] for b in body), default=0)
        # 영문·숫자 조각은 Word가 끊지 못하므로 그대로, 한글 조각은 아주 길면(회사명 등) 끊어도 된다 → 한도는 아래에서 단계적으로 낮춘다
        latin_max = max((measure(tk, size) for b in body for ln in b[0].split("\n") for tk in re.findall(r"[A-Za-z0-9][A-Za-z0-9.,%~\-/:()]*", ln)), default=0)
        atom_min = min(atom_max, 24 * unit)
        req = max(min(maxfull, cap), hdr_req, atom_min)
        cols.append(dict(hdr=hdr_req, hdr_one=int(hdr_one + PAD), hdr_piece=hdr_piece, body=body, typical=typical, volume=volume, maxfull=maxfull, prose=prose,
                         atom_max=atom_max, latin_max=latin_max, req=int(req + PAD), reqfull=int(max(maxfull, hdr_one) + PAD)))   # reqfull: 어떤 셀도 접히지 않는 폭
    floor = min(700 if ncol < 8 else 500, total // ncol)
    for c in cols: c["req"] = max(c["req"], floor)
    # 약력·주요경력 열은 표 폭의 40% 이상을 준다(사용자 지시 2026-09-22 「약력 내용 더 넓힐 수 있도록」)
    for j, c in enumerate(cols):
        h = plain_text(rows[0][j] if j < len(rows[0]) else "").replace(" ", "")
        c["force"] = int(total * 0.40) if h in ("약력", "주요경력", "경력") and ncol >= 6 else 0
        c["req"] = max(c["req"], c["force"])
    req = [c["req"] for c in cols]; reqfull = [max(c["reqfull"], c["req"]) for c in cols]
    def min_widths(atom_cap):
        """최소 폭: 영문·숫자 조각은 그대로, 한글 조각은 atom_cap 단위까지 보장."""
        out = []
        for c in cols:
            a = max(min(c["atom_max"], atom_cap * unit), min(c["latin_max"], 24 * unit))
            w = max(a, c["hdr_piece"], 3 * unit, 400 - PAD) + PAD
            out.append(int(max(min(w, c["req"]), min(floor, c["req"]), c.get("force", 0))))
        return out
    nrow = len(rows) - 1
    cache = {}
    def lines_of(j, w):
        key = (j, w)
        if key not in cache: cache[key] = [est_lines(b[0], w - PAD, size) for b in cols[j]["body"]]
        return cache[key]
    rowmap = []   # 빈 셀을 뺀 body 목록 ↔ 행 번호
    for j in range(ncol):
        idx = []
        for i, r in enumerate(rows[1:]):
            t = plain_text(r[j] if j < len(r) else "")
            if t and t not in ("^", "<"): idx.append(i)
        rowmap.append(idx)
    def row_lines(j, w):
        rl = [0] * nrow
        for i, n in zip(rowmap[j], lines_of(j, w)): rl[i] = n
        return rl
    def broken(tws):
        """짧은 정보(20단위 이하, 확인 필요 아님)가 조각 중간에서 끊기는 정도. 짧은 조각(한글 5자 이하: 이름)은 3, 긴 조각(직책명 등)은 1로 센다."""
        n = 0
        for j in range(ncol):
            avail = tws[j] - PAD
            for t, full, atom, flag, _ls in cols[j]["body"]:
                if not flag and full <= 20 * unit and full > avail and atom > avail:
                    n += 3 if atom <= 10 * unit else 1
                    if DEBUG: print(f"      끊김: 열{j} '{t[:20]}' atom={round(atom)} avail={avail}")
        return n
    def wrapped_units(tws):
        """접힌 정보 단위 수: 셀의 명시 줄(<br>로 나뉜 줄) 가운데 34단위 이하인 줄(확인 필요 제외)이 폭 때문에 더 접힌 줄 수의 합.
        약력처럼 한 셀에 여러 줄이 있는 경우 줄마다 센다."""
        return sum(col_W(j, tws[j]) for j in range(ncol))
    # 짧은 정보 줄: 셀의 명시 줄 가운데 34단위 이하인 줄(확인 필요 셀 제외)
    short_lines = [[ln for b in cols[j]["body"] if not b[3] for ln in b[4] if ln and measure(ln, size) <= 34 * unit] for j in range(ncol)]
    cacheW = {}
    def col_W(j, w):
        """열 j가 폭 w일 때 짧은 정보 줄의 접힘 수."""
        key = (j, w)
        if key not in cacheW: cacheW[key] = sum(est_lines(ln, w - PAD, size) - 1 for ln in short_lines[j])
        return cacheW[key]
    def fill(minw):
        """물 채우기: minw에서 시작해 '행 높이(줄 수) 합 + 짧은 정보 접힘 수×0.5'가 가장 많이 줄어드는 열부터 폭을 준다. (tws, 높이) 반환.
        행 높이만 보면 긴 글 열이 폭을 독차지해 짧은 정보가 접힌 채 남으므로, 접힘 수도 같이 줄인다."""
        tws = list(minw)
        cur_rl = [row_lines(j, tws[j]) for j in range(ncol)]
        cur_W = [col_W(j, tws[j]) for j in range(ncol)]
        rest = total - sum(tws)
        step0 = int(unit)
        while rest > 0:
            best = None
            base = [max(cur_rl[j][i] for j in range(ncol)) for i in range(nrow)]
            for mult in (1, 2, 4, 8, 16):
                step = min(step0 * mult, rest)
                for j in range(ncol):
                    if tws[j] >= reqfull[j]: continue
                    nw = min(tws[j] + step, reqfull[j])
                    if nw == tws[j]: continue
                    new_rl = row_lines(j, nw)
                    gain = 0
                    for i in range(nrow):
                        others = max([cur_rl[k][i] for k in range(ncol) if k != j] or [0])
                        gain += base[i] - max(others, new_rl[i])
                        gain += 0.1 * (cur_rl[j][i] - new_rl[i])   # 행 높이가 안 줄어도(같은 높이의 셀이 둘) 줄 수가 줄면 작은 이득으로 친다
                    new_W = col_W(j, nw)
                    gain += 0.5 * (cur_W[j] - new_W)
                    score = gain / (nw - tws[j])
                    if gain > 0 and (best is None or score > best[0]): best = (score, j, nw, new_rl, new_W)
                if best: break
            if best is None: break
            _, j, nw, new_rl, new_W = best
            rest -= nw - tws[j]; tws[j] = nw; cur_rl[j] = new_rl; cur_W[j] = new_W
        if rest > 0:   # 더 줄일 줄이 없으면: 긴 글 열에 글 양 비례로 70%, 나머지는 부족분 비례. 그래도 남으면 똑같이
            longs = [j for j in range(ncol) if cols[j]["prose"] and tws[j] < reqfull[j]]
            if longs:
                tv = sum(cols[j]["volume"] for j in longs) or 1
                give = int(rest * 0.7)
                for j in longs: tws[j] += min(reqfull[j] - tws[j], int(give * cols[j]["volume"] / tv))
                rest = total - sum(tws)
            deficit = [max(0, reqfull[j] - tws[j]) for j in range(ncol)]
            td = sum(deficit)
            if td and rest > 0:
                give = min(rest, td)
                for j in range(ncol): tws[j] += int(give * deficit[j] / td)
                rest = total - sum(tws)
            if rest > 0:
                for j in range(ncol): tws[j] += rest // ncol
            cur_rl = [row_lines(j, tws[j]) for j in range(ncol)]
        return tws, sum(max(cur_rl[j][i] for j in range(ncol)) for i in range(nrow))
    if sum(req) <= total:
        # 여유가 있으면 머리행부터 한 줄에 들어가게 넓힌다(왼쪽 열부터, 들어가는 만큼만)
        for j in range(ncol):
            add = cols[j]["hdr_one"] - req[j]
            if 0 < add <= total - sum(req): req[j] += add
        extra = total - sum(req)
        longs = [j for j in range(ncol) if cols[j]["prose"]]
        if not longs:
            tws = [req[j] + extra // ncol for j in range(ncol)]
        else:
            tv = sum(cols[j]["volume"] for j in longs) or 1
            tws = [req[j] + int(extra * 0.3) // ncol + (int(extra * 0.7 * cols[j]["volume"] / tv) if j in longs else 0) for j in range(ncol)]
        ok = True
    else:
        # 한글 조각 보장 한도를 24단위(12자)→18→12→8로 낮춰 가며 물 채우기를 하고, '높이 + 끊긴 짧은 정보 수×3'이 가장 작은 배분을 고른다
        best = None
        for atom_cap in (24, 18, 12, 8):
            minw = min_widths(atom_cap)
            if sum(minw) > total: continue
            tws_c, h = fill(minw); b = broken(tws_c)
            Wc = wrapped_units(tws_c)
            score = (Wc + 2 * b, b)   # 접힘 + 끊김×2가 가장 작은 변형(같으면 끊김이 적은 쪽)
            if DEBUG: print(f"  [col_widths {size}pt] atom_cap={atom_cap} 높이={h} 접힘={Wc} 끊김={b} tws={tws_c}")
            if best is None or score < best[0]: best = (score, tws_c, b)
        if best is None:   # 최소 폭(한글 4자)조차 못 넣는 표: 최소 폭에 비례해 줄인다(글자 크기를 더 줄여야 한다)
            minw = min_widths(8); tm = sum(minw)
            tws = [max(400, int(total * minw[j] / tm)) for j in range(ncol)]
            ok = False
        else:
            _, tws, b = best
            ok = b == 0
    tws = [max(400, w) for w in tws]
    scale = total / sum(tws); tws = [int(w * scale) for w in tws]
    diff = total - sum(tws); tws[max(range(ncol), key=lambda j: tws[j])] += diff
    # 접힌 정보 단위 수(W): 60단위 이하 셀(확인 필요 제외)에서 명시 줄 수보다 늘어난 줄 수의 합. 끊긴 짧은 정보 수(b)와 함께 돌려준다.
    W = wrapped_units(tws); b = broken(tws)
    return tws, b == 0, W, b

def soft_break(txt, avail, size):
    """열 폭(avail twips)을 넘는 짧은 셀(60단위 이하)을 구분되는 자리(여는 괄호·쉼표·가운뎃점·공백)에서 나눈다.
    긴 글(프로즈)은 건드리지 않는다(서식지침 4절 '정보가 많은 셀은 구분되는 자리에서 줄을 바꾼다')."""
    plain = re.sub(r"\*\*", "", txt)
    if measure(plain, size) <= avail or text_width(plain) > 60 or "[확인 필요" in plain: return txt
    best = None
    for m in re.finditer(r"(?<=[,·/])(?!\d)\s*|\s+", plain):   # 여는 괄호 앞·숫자 안 쉼표(292,960)에서는 나누지 않는다(2026-09-22)
        pos = m.end() if m.group(0) else m.start()
        if 0 < pos < len(plain) and measure(plain[:pos].rstrip(), size) <= avail: best = pos
    if best is None: return txt
    head, tail = plain[:best].rstrip(), plain[best:].lstrip()
    if not head or not tail: return txt
    return head + "<br>" + soft_break(tail, avail, size)

SMALL_LOG = []   # (표 번호, 글자 크기) — 9pt로 못 맞춰 줄인 표
WRAP_LOG = []   # (표 번호, 열 제목, 셀 글, 예상 줄 수) — 기본 정보가 접히는 셀 기록(가시성 검사)

def wrap_check(rows, tws, tid, size):
    """폭 배분 뒤 짧은 셀(20단위 이하)이 접히면 기록한다. 긴 글 열은 4줄 넘게 접히면 '라인변경 필요'로 기록."""
    ncol = len(tws)
    for r in rows[1:]:
        for j in range(min(ncol, len(r))):
            txt = plain_text(r[j])
            if not txt or txt in ("<", "^") or "[확인 필요" in txt: continue
            lines = est_lines(txt.replace("<br>", "\n"), tws[j] - PAD, size)
            explicit = txt.count("<br>") + 1
            if text_width(txt) <= 20 and lines > explicit: WRAP_LOG.append((tid, rows[0][j] if j < len(rows[0]) else j, txt, lines, "기본정보 접힘"))
            elif lines - explicit >= 4 and text_width(txt) <= 60: WRAP_LOG.append((tid, rows[0][j] if j < len(rows[0]) else j, txt[:30], lines, "라인변경 필요"))

def set_widths(t, tws):
    tbl = t._tbl; tblPr = tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        for e in tblPr.findall(qn(tag)): tblPr.remove(e)
    tblW = OxmlElement("w:tblW"); tblW.set(qn("w:w"), "5000"); tblW.set(qn("w:type"), "pct"); tblPr.append(tblW)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    for g, wv in zip(tbl.tblGrid.findall(qn("w:gridCol")), tws): g.set(qn("w:w"), str(wv))
    for row in t.rows:
        for c, wv in zip(row.cells, tws):
            tcPr = c._tc.get_or_add_tcPr()
            for e in tcPr.findall(qn("w:tcW")): tcPr.remove(e)
            tcW = OxmlElement("w:tcW"); tcW.set(qn("w:w"), str(wv)); tcW.set(qn("w:type"), "dxa"); tcPr.append(tcW)

def drop_source_cols(rows):
    hdr = rows[0]
    keep = [j for j, h in enumerate(hdr) if re.sub(r"\*\*", "", h).strip() not in SRC_COLS]
    if len(keep) == len(hdr): return rows
    return [[r[j] for j in keep if j < len(r)] for r in rows]

def keep_first(cell):
    """병합된 셀에는 첫 문단만 남긴다(python-docx merge는 문단을 이어 붙인다)."""
    for pp in cell.paragraphs[1:]: pp._p.getparent().remove(pp._p)
    return cell

def vmerge(cell, kind):
    tcPr = cell._tc.get_or_add_tcPr(); v = OxmlElement("w:vMerge")
    if kind == "restart": v.set(qn("w:val"), "restart")
    tcPr.append(v)

def add_table(d, rows, aligns, total_width):
    """마크다운 표 → docx 표.
    - 2단 머리행: 둘째 줄 첫 칸이 '^'이면 머리행 2행. 첫 줄에서 같은 글자가 이어지는 칸은 가로 병합, 둘째 줄의 '^'는 위 칸과 세로 병합.
      1단 머리행에서도 같은 글자가 이어지는 칸('내용 | 내용 | 내용')은 가로 병합한다.
    - 본문: 바로 위 칸과 같은 글자가 이어지면 세로 병합(왼쪽 열도 병합 중일 때만, 숫자·'-' 제외).
    - 열 너비: 기본 정보가 접히지 않게 배분. 9pt로 안 들어가면 8pt→7.5pt→7pt→6.5pt로 줄여 본다(서식지침 4절).
    - 정렬은 열 단위로 통일: 숫자 열 오른쪽, 긴 문장이 있는 열·접히는 열·여러 줄 셀이 있는 열은 왼쪽, 한 줄에 들어가는 짧은 문자 열만 가운데.
      가로 병합된 긴 글(연간보수총액 줄 등)은 왼쪽.
    - 본문 셀이 '<' 이면 왼쪽 셀과 가로 병합한다."""
    rows = drop_source_cols(rows)
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    # 셀이 ![캡션](경로)이면 그림을 셀 폭에 맞춰 넣는다(확인서 2장을 한 줄에 나란히. 사용자 지시 2026-09-22). 폭 계산에서는 빈 칸으로 본다
    imgs = {}
    for i, r in enumerate(rows):
        for j, c in enumerate(r):
            m = re.match(r"^!\[(.*?)\]\((.+?)\)$", c.strip())
            if m: imgs[(i, j)] = m.group(2); rows[i][j] = ""
    nhead = 2 if len(rows) > 1 and rows[1][0].strip() == "^" else 1
    body = rows[nhead:]
    # 폭 계산: 가로 병합에 걸린 셀('<'와 그 왼쪽 셀)은 빈 칸으로 본다(보수총액 줄 같은 긴 병합 글이 첫 열을 부풀리지 않도록)
    def hmerged(r, j):
        return r[j].strip() == "<" or (j + 1 < len(r) and r[j + 1].strip() == "<")
    wrows = [rows[0]] + [["" if hmerged(r, j) else c for j, c in enumerate(r)] for r in body]
    # 글자 크기(서식지침 4절): 9pt에서 시작해 한 단계 줄였을 때 '접힌 짧은 정보 수(W) + 끊긴 짧은 정보(b)×2'가 25% 이상(그리고 3 이상) 줄거나
    # 끊김(b)이 줄어들 때만 한 단계 더 줄인다. 6.5pt는 끊김이 남아 있을 때만 쓴다(열이 아주 많은 표).
    sizes = (9, 8, 7.5, 7, 6.5) if not os.environ.get("MD2DOCX_SIZE") else (float(os.environ["MD2DOCX_SIZE"]),)   # 시험용 강제 크기
    chosen = None
    for size in sizes:
        tws, ok, W, b = col_widths(wrows, total_width, size)
        score = W + 2 * b
        if DEBUG: print(f"  [add_table 표{len(d.tables) + 1}] {size}pt W={W} b={b} score={score}")
        if chosen is None: chosen = (size, tws, W, b, score); continue
        cs = chosen[4]
        if size < 7 and chosen[3] == 0: break
        if b < chosen[3] or (score <= 0.75 * cs and cs - score >= 3): chosen = (size, tws, W, b, score)
        else: break
    size, tws = chosen[0], chosen[1]
    if imgs: tws = [total_width // ncol] * ncol   # 그림 표는 열을 같은 폭으로
    # 열 정렬 결정
    col_align = []
    for j in range(ncol):
        vals = [re.sub(r"\*\*", "", r[j]).replace("　", "").strip() for r in wrows[1:]]
        vals = [v for v in vals if v and v != "^"]
        flat = [v.replace("<br>", "") for v in vals]
        real = [v for v in flat if v != "-"]          # '-'는 숫자·문자 어느 쪽도 아니므로 판단에서 뺀다
        nums = sum(1 for v in real if NUM.match(v))
        multi = any("<br>" in v and not NUM.match(v.replace("<br>", "")) for v in vals)
        wraps = any(est_lines(v.replace("<br>", "\n"), tws[j] - PAD, size) > v.count("<br>") + 1 for v in vals)
        if real and nums >= len(real) * 0.6 and j > 0: col_align.append("우측")
        elif any(text_width(v) > 20 for v in flat) or (j == 0 and any(text_width(v) > 16 for v in flat)) or wraps or multi: col_align.append("좌측")
        else: col_align.append("중앙")
    t = d.add_table(rows=len(rows), cols=ncol); t.style = d.styles["Table Grid"]; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = t._tbl.tblPr; mar = OxmlElement("w:tblCellMar")
    for side, v in (("left", 57), ("right", 57), ("top", 14), ("bottom", 14)):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
    tblPr.append(mar)
    for i, row in enumerate(rows):
        for j in range(ncol):
            txt = row[j]
            merged = i >= nhead and hmerged(row, j)
            if i >= nhead and col_align[j] != "우측" and "<br>" not in txt and not merged:
                txt = soft_break(txt, tws[j] - PAD, size)
            cell = t.cell(i, j); p = cell.paragraphs[0]
            if (i, j) in imgs:
                ip = Path(imgs[(i, j)]); ip = ip if ip.is_absolute() else ROOT / ip
                p.style = d.styles["본문_표(중앙)"]
                if ip.exists(): p.add_run().add_picture(str(ip), width=Cm(tws[j] / 567 - 0.4))
                else: add_runs(p, f"[확인 필요: 그림 파일 없음 {ip.name}]", size)
                cell.vertical_alignment = 1; continue
            if i < nhead:
                p.style = d.styles["본문_표(중앙)"]; shade(cell, "D9D9D9")
                if txt.strip() != "^": add_runs(p, "**" + re.sub(r"\*\*", "", txt) + "**", size)
            else:
                al = col_align[j]
                if merged and txt.strip() != "<" and text_width(txt) > 20: al = "좌측"   # 가로 병합된 긴 글은 왼쪽
                p.style = d.styles["본문_표(" + al + ")"]
                if txt.strip() != "^": add_runs(p, txt, size)   # '^'는 위 셀과 병합(글자 없음)
            cell.vertical_alignment = 1
    # 머리행 병합
    j = 0
    while j < ncol:
        k = j
        while k + 1 < ncol and rows[0][k + 1].strip() == rows[0][j].strip() and rows[0][j].strip() and (nhead == 1 or rows[1][k + 1].strip() != "^"): k += 1
        if k > j: keep_first(t.cell(0, j).merge(t.cell(0, k)))
        j = k + 1
    if nhead == 2:
        for j in range(ncol):
            if rows[1][j].strip() == "^": keep_first(t.cell(0, j).merge(t.cell(1, j)))
    # 본문 세로 병합: 같은 값이 이어지고 왼쪽 열도 모두 같은 값이면 합친다(숫자·'-'·빈칸 제외)
    for j in range(ncol):
        i = nhead
        while i < len(rows):
            v = rows[i][j].strip()
            k = i
            def left_merged(r):  # 왼쪽 열들이 모두 위와 같은 값인지
                return all(rows[r][x].strip() == rows[r - 1][x].strip() for x in range(j))
            while k + 1 < len(rows) and v and v != "-" and not NUM.match(v) and rows[k + 1][j].strip() == v and left_merged(k + 1): k += 1
            if k > i: keep_first(t.cell(i, j).merge(t.cell(k, j)))
            i = k + 1
    # 본문 명시 세로 병합: 셀 내용이 '^' 이면 위 셀과 병합(거래별 행으로 나눈 표에서 회사명·신청일 현재 주식수처럼 숫자가 섞인 셀을 묶을 때. 2026-09-21)
    for j in range(ncol):
        i = nhead
        while i < len(rows):
            k = i
            while k + 1 < len(rows) and rows[k + 1][j].strip() == "^": k += 1
            if k > i and rows[i][j].strip() != "^": keep_first(t.cell(i, j).merge(t.cell(k, j)))
            i = k + 1
    # 본문 가로 병합: 셀 내용이 '<' 이면 왼쪽 셀과 병합(양식의 가로 병합 행: 연간보수총액 줄, 최고경영자 표 등)
    for i in range(nhead, len(rows)):
        j = 0
        while j < ncol:
            if rows[i][j].strip() != "<":
                k = j
                while k + 1 < ncol and rows[i][k + 1].strip() == "<": k += 1
                if k > j: keep_first(t.cell(i, j).merge(t.cell(i, k)))
                j = k + 1
            else: j += 1
    set_widths(t, tws); wrap_check(wrows, tws, len(d.tables), size)
    if size < 9: SMALL_LOG.append((len(d.tables), size))
    return t

# docx에 남으면 안 되는 원천 표기(출처는 대조표 엑셀에서 본다. 사용자 지시 2026-09-04)
SOURCE_PAT = re.compile(r"(?<!매)출처|원본자료/|\.xlsx|\.pdf|\.docx|\.pptx|\bp\.\d|이사회 ?\d+회|주총 ?\d+회|의사록 현황|(?<!대차)대조표|\bA-\d{2,3}\b|폴더|\{[A-Z]+\}|시트")

def check_sources(d):
    """변환된 docx에서 원천 표기가 남았는지 검사한다. 남은 줄 목록을 돌려준다."""
    hits = []
    flag = re.compile(r"\[(?:확인 필요|작성 대기)[^\]]*\]")   # 작업용 표식 안의 문구는 확정 전에 없어지므로 검사에서 뺀다
    for p in d.paragraphs:
        if SOURCE_PAT.search(flag.sub("", p.text)): hits.append("본문: " + p.text[:80])
    for ti, t in enumerate(d.tables):
        for r in t.rows:
            for c in r.cells:
                if SOURCE_PAT.search(flag.sub("", c.text)): hits.append(f"표{ti + 1}: " + c.text[:80]); break
    return hits

ALIGN = {"제목_Ⅰ.": WD_ALIGN_PARAGRAPH.CENTER, "제목_1.": WD_ALIGN_PARAGRAPH.LEFT, "제목_가.": WD_ALIGN_PARAGRAPH.LEFT, "제목_(1)": WD_ALIGN_PARAGRAPH.LEFT, "제목_(가)": WD_ALIGN_PARAGRAPH.LEFT,
         "본문_표준": WD_ALIGN_PARAGRAPH.JUSTIFY, "본문_주석": WD_ALIGN_PARAGRAPH.JUSTIFY, "본문_단위": WD_ALIGN_PARAGRAPH.RIGHT, "본문_표제목": WD_ALIGN_PARAGRAPH.CENTER,
         "본문_표(중앙)": WD_ALIGN_PARAGRAPH.CENTER, "본문_표(우측)": WD_ALIGN_PARAGRAPH.RIGHT, "본문_표(좌측)": WD_ALIGN_PARAGRAPH.LEFT}
def fix_align(d):
    """스타일 상속에 기대지 않고 문단마다 정렬을 명시한다(뷰어에 따라 상속 정렬이 다르게 보이는 문제 방지)."""
    def apply(p):
        a = ALIGN.get(p.style.name)
        if a is not None: p.alignment = a
    for p in d.paragraphs: apply(p)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs: apply(p)

SRC_INLINE = re.compile(r"\s*\(출처:.*$")   # 줄·셀 끝까지의 출처 표기

def strip_sources(text):
    """docx는 산출물이므로 출처 표기를 넣지 않는다(출처는 대조표 엑셀에서 본다). 사용자 지시 2026-09-04."""
    return SRC_INLINE.sub("", text).rstrip()

def convert(md_path, out_path, with_sources=False):
    d = new_doc()
    sec = d.sections[0]; total_width = int((sec.page_width - sec.left_margin - sec.right_margin) / 635)
    lines = Path(md_path).read_text(encoding="utf-8").splitlines()
    if not with_sources:
        cleaned = []
        for ln in lines:
            if ln.startswith("(출처:"): continue
            if ln.startswith("|"):
                ln = "|".join(strip_sources(c) if "(출처:" in c else c for c in ln.split("|"))
            else:
                ln = strip_sources(ln) if "(출처:" in ln else ln
            cleaned.append(ln)
        lines = cleaned
    i = 0; gap = False; last = None   # gap: 마크다운 빈 줄을 만났음. 본문 문단 뒤에 제목·본문이 오면 빈 문단을 하나 넣어 문단 사이를 띄운다(사용자 지시 2026-09-22 「칸띄기」)
    def spacer():
        nonlocal gap, last
        if gap and last in ("body", "note"): d.add_paragraph(style="본문_표준")
        gap = False
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip() or ln.startswith("<!--"):
            if not ln.strip(): gap = True
            i += 1; continue
        if ln.strip() == "<<<쪽나눔>>>":   # 합본(00_전체합본.py)에서 장 사이 쪽 나눔
            d.add_page_break(); gap = False; last = None; i += 1; continue
        m = re.match(r"^(#{1,5}) (.*)", ln)
        if m:
            spacer(); lvl = len(m.group(1)); p = d.add_paragraph(style=HEAD_STYLE[lvl]); add_runs(p, m.group(2)); last = "head"; i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-+:?$", c) for c in cells if c): rows.append(cells)
                i += 1
            add_table(d, rows, None, total_width); last = "table"; gap = False
            k = i
            while k < len(lines) and not lines[k].strip(): k += 1
            if k < len(lines) and re.match(r"^(주\d*\)|※|\(출처:)", lines[k].strip()): i = k   # 주)는 표 바로 밑에
            else: d.add_paragraph(style="본문_표준")
            continue
        m_img = re.match(r"^!\[(.*?)\]\((.*?)\)$", ln)
        if m_img:   # 그림: ![캡션](경로) → 가운데 정렬 그림 + 아래 캡션(표제목 스타일). 폭은 본문 폭 안에서 원본 비율 유지(최대 16cm)
            cap, path = m_img.group(1), m_img.group(2)
            ip = Path(path) if Path(path).is_absolute() else ROOT / path
            if ip.exists():
                from PIL import Image as _Im
                w_px, h_px = _Im.open(ip).size
                width_cm = min(16.0, w_px / 96 * 2.54)   # 96dpi 기준 자연 크기, 본문 폭보다 크면 줄임
                if width_cm < 9 and w_px >= 500: width_cm = 12.0
                if width_cm * h_px / w_px > 14.0: width_cm = 14.0 * w_px / h_px   # 세로로 긴 그림은 높이 14cm까지
                if cap:   # 캡션은 표 제목처럼 그림 위에 둔다(사용자 지시 2026-09-22)
                    p = d.add_paragraph(style="본문_표제목"); add_runs(p, "[" + cap + "]")
                pic = d.add_paragraph(); pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
                pic.add_run().add_picture(str(ip), width=Cm(width_cm))
            else:
                p = d.add_paragraph(style="본문_표준"); add_runs(p, f"[확인 필요: 그림 파일 없음 {cap}]")
            i += 1; continue
        if re.match(r"^\[.*\]$", ln) and not ln.startswith("[확인 필요") and not ln.startswith("[작성 대기") and not ln.startswith("[그림") and text_width(ln) <= 60:
            p = d.add_paragraph(style="본문_표제목"); add_runs(p, ln); i += 1; continue
        if ln.startswith("[그림"):   # 그림 자리표시는 본문처럼 왼쪽 정렬(가운데 정렬된 긴 문장 방지. 사용자 지시 2026-09-06)
            p = d.add_paragraph(style="본문_표준"); add_runs(p, "[확인 필요: " + ln[1:]); i += 1; continue
        if re.match(r"^\(단위 ?:", ln):
            p = d.add_paragraph(style="본문_단위"); add_runs(p, ln); i += 1; continue
        if re.match(r"^(주\d*\)|※)", ln):
            # 제목형 주N)(뒤에 (단위)·표가 오는 세부표 제목)이 표 바로 뒤에 오면 빈 문단으로 띄운다(사용자 지시 2026-09-23 「표 나오고 주기 하고 표 띄워야」). 표에 붙는 주석은 그대로 붙인다
            nxt = next((x.strip() for x in lines[i + 1:i + 4] if x.strip()), "")
            if last == "table" and (nxt.startswith("|") or nxt.startswith("(단위")): d.add_paragraph(style="본문_표준")   # 표 처리에서 뒤 빈 줄을 먹으므로 gap은 보지 않는다
            p = d.add_paragraph(style="본문_주석"); add_runs(p, ln); p.paragraph_format.space_before = Pt(0); last = "note"; gap = False; i += 1
            while i < len(lines) and lines[i].strip().startswith("- "):   # 주N) 바로 아래 '- 일자 [매도인/매수인] …' 상세 줄은 주석 서식으로 들여 쓴다(과거 신청서 방식)
                p = d.add_paragraph(style="본문_주석"); add_runs(p, lines[i].strip()); p.paragraph_format.space_before = Pt(0); p.paragraph_format.left_indent = Cm(0.4); i += 1
            k = i
            while k < len(lines) and not lines[k].strip(): k += 1
            if k < len(lines) and re.match(r"^(주\d*\)|※)", lines[k].strip()): i = k   # 주1)·주2) 사이 빈 줄 제거
            elif k < len(lines) and k > i and not lines[k].strip().startswith(("(단위", "|")): d.add_paragraph(style="본문_표준"); i = k   # md에 빈 줄이 있을 때만   # 주석 뒤 본문과는 한 줄 띄움. 제목형 주N) 뒤의 (단위)·표는 붙인다(사용자 지시 2026-09-23)
            elif k < len(lines): i = k
            continue
        if ln.startswith("(출처:"):
            p = d.add_paragraph(style="본문_주석"); add_runs(p, ln, 8, "808080", italic=True); i += 1; continue
        if re.match(r"^\d\) \S", ln) and len(ln) <= 30:   # '1) 생산방식' 같은 소제목 줄은 굵게
            p = d.add_paragraph(style="본문_표준"); add_runs(p, "**" + ln + "**"); i += 1; continue
        spacer(); p = d.add_paragraph(style="본문_표준"); add_runs(p, ln); last = "body"; i += 1
    fix_align(d)
    if os.path.exists(out_path):   # 직전 docx를 검토/docx_이력/에 보관해 사용자가 Word에서 고친 뒤 비교할 수 있게 한다(사용자 요청 2026-09-22)
        import shutil, datetime, unicodedata
        hist = os.path.join(os.path.dirname(os.path.abspath(out_path)), "docx_이력"); os.makedirs(hist, exist_ok=True)
        stamp = datetime.datetime.fromtimestamp(os.path.getmtime(out_path)).strftime("%Y%m%d_%H%M")
        shutil.copy2(out_path, os.path.join(hist, unicodedata.normalize("NFC", os.path.splitext(os.path.basename(out_path))[0]) + f"_{stamp}.docx"))
    d.save(out_path)
    hits = [] if with_sources else check_sources(d)
    if hits:
        print(f"경고: docx에 원천 표기 {len(hits)}건 잔존 (마크다운의 표 열을 '출처'로 옮기거나 문장에서 빼야 한다)")
        for h in hits[:30]: print("   ", h)
    else:
        print("원천 표기 잔존 검사: 0건")
    basic = [w for w in WRAP_LOG if w[4] == "기본정보 접힘"]; longs = [w for w in WRAP_LOG if w[4] == "라인변경 필요"]
    print(f"표 가시성 검사: 표 {len(d.tables)}개, 기본 정보 접힘 {len(basic)}건, 라인변경 필요(5줄 이상) {len(longs)}건, 글자 줄인 표 {len(SMALL_LOG)}개 {[f'표{a}:{b}pt' for a, b in SMALL_LOG][:15]}")
    SMALL_LOG.clear()
    for w in (basic + longs)[:20]: print(f"    표{w[0]} [{w[1]}] {w[2]} → {w[3]}줄 ({w[4]})")
    WRAP_LOG.clear()
    return out_path

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = Path(args[0]); dst = Path(args[1]) if len(args) > 1 else src.with_suffix(".docx")
    print("저장:", convert(src, dst, with_sources="--with-sources" in sys.argv))
