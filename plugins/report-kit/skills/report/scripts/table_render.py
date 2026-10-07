# -*- coding: utf-8 -*-
"""docx의 표를 실제 열 너비·글자 크기(맑은 고딕)로 그려 PNG로 만든다(가시성 검토용. Word 렌더링 근사).
사용: python3 검토/scripts/00_표렌더.py 초안/01_Ⅰ.회사의개황.docx [출력폴더]
출력: 출력폴더/NN_sheet_K.png (표 여러 개를 세로로 이어 붙인 장), NN_요약.txt (표별 열 너비·접힘 통계)"""
import re, sys
from pathlib import Path
import docx
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts")
DPI = 150
PX = DPI / 1440          # twips → px
CELL_MAR = 57            # 좌우 셀 여백(twips)
SHEET_H = 2600

_fonts = {}
def font(pt, bold=False):
    key = (round(pt * 2) / 2, bold)
    if key not in _fonts:
        size = int(round(pt * DPI / 72))
        f = FONT_DIR / ("malgunbd.ttf" if bold else "malgun.ttf")
        if f.exists():
            _fonts[key] = ImageFont.truetype(str(f), size)
        else:   # Word가 없으면 맥 기본 한글 글꼴로 대신 그린다(폭은 근사)
            _fonts[key] = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", size, index=6 if bold else 0)
    return _fonts[key]

def wrap(text, f, width_px, draw):
    """Word식 줄바꿈 근사: 한글·한자는 글자 단위, 영문·숫자 덩어리는 단어 단위로 접는다."""
    out = []
    for para in text.split("\n"):
        toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9.,%()\-/:]*|\s+|.", para)
        line = ""
        for tk in toks:
            cand = line + tk
            if draw.textlength(cand.rstrip(), font=f) <= width_px or not line.strip():
                line = cand
            else:
                out.append(line.rstrip()); line = tk.lstrip() if tk.isspace() else tk
                # 단어 하나가 폭보다 길면 글자 단위로 쪼갠다
                while draw.textlength(line, font=f) > width_px and len(line) > 1:
                    k = len(line)
                    while k > 1 and draw.textlength(line[:k], font=f) > width_px: k -= 1
                    out.append(line[:k]); line = line[k:]
        out.append(line.rstrip())
    return out or [""]

def cell_info(tc, style_size):
    tcPr = tc.tcPr
    span = 1; vm = None; fill = None
    if tcPr is not None:
        gs = tcPr.find(qn("w:gridSpan")); span = int(gs.get(qn("w:val"))) if gs is not None else 1
        v = tcPr.find(qn("w:vMerge")); vm = (v.get(qn("w:val")) or "continue") if v is not None else None
        sh = tcPr.find(qn("w:shd")); fill = sh.get(qn("w:fill")) if sh is not None else None
    paras = []
    size = style_size; bold = False; align = "left"; flag = False
    for p in tc.findall(qn("w:p")):
        pPr = p.find(qn("w:pPr"))
        st = pPr.find(qn("w:pStyle")).get(qn("w:val")) if pPr is not None and pPr.find(qn("w:pStyle")) is not None else ""
        jc = pPr.find(qn("w:jc")) if pPr is not None else None
        if jc is not None: align = {"center": "center", "right": "right", "both": "left"}.get(jc.get(qn("w:val")), "left")
        elif "중앙" in st: align = "center"
        elif "우측" in st: align = "right"
        txt = ""
        for r in p.findall(qn("w:r")):
            rPr = r.find(qn("w:rPr"))
            if rPr is not None:
                sz = rPr.find(qn("w:sz"))
                if sz is not None: size = int(sz.get(qn("w:val"))) / 2
                if rPr.find(qn("w:b")) is not None: bold = True
                if rPr.find(qn("w:highlight")) is not None: flag = True
            for ch in r:
                if ch.tag == qn("w:t"): txt += ch.text or ""
                elif ch.tag == qn("w:br"): txt += "\n"
                elif ch.tag == qn("w:tab"): txt += "  "
        paras.append(txt)
    return dict(span=span, vm=vm, fill=fill, text="\n".join(paras), size=size, bold=bold, align=align, flag=flag)

def render_table(t, tid, style_size=9.0):
    tbl = t._tbl
    grid = [int(g.get(qn("w:w"))) for g in tbl.tblGrid.findall(qn("w:gridCol"))]
    rows = tbl.findall(qn("w:tr"))
    # 셀 격자 구성
    cells = []   # 행별 [(col0, span, info)]
    for tr in rows:
        c0 = 0; row = []
        for tc in tr.findall(qn("w:tc")):
            inf = cell_info(tc, style_size); row.append((c0, inf["span"], inf)); c0 += inf["span"]
        cells.append(row)
    tmp = Image.new("RGB", (10, 10)); dr = ImageDraw.Draw(tmp)
    # 줄 수·행 높이
    heights = []; wrapped = []
    stats = dict(short_wrap=0, max_lines=0, cells=0)
    for row in cells:
        h = 0; wr = []
        for c0, span, inf in row:
            w_tw = sum(grid[c0:c0 + span]) - 2 * CELL_MAR
            f = font(inf["size"], inf["bold"])
            lines = wrap(inf["text"], f, w_tw * PX - 2, dr) if inf["vm"] != "continue" else [""]
            wr.append(lines)
            lh = f.size * 1.35
            if inf["vm"] != "continue":
                h = max(h, len(lines) * lh + 6)
                if inf["text"].strip():
                    stats["cells"] += 1
                    plain = re.sub(r"\[확인 필요[^\]]*\]", "확인필요", inf["text"])
                    if "\n" not in plain and len(plain) <= 14 and len(lines) > 1: stats["short_wrap"] += 1
                    stats["max_lines"] = max(stats["max_lines"], max(len(l) for l in [lines]))
            else:
                h = max(h, 8)
        heights.append(int(h)); wrapped.append(wr)
    # vMerge continue 행 높이는 restart 셀 글에 맞게 늘리지 않는다(Word도 마찬가지)
    W = int(sum(grid) * PX) + 2; H = sum(heights) + 26
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    d.text((2, 2), f"표{tid}  {stats['cells']}셀  글자 {cells[0][0][2]['size']}pt", font=font(8), fill="gray")
    y = 24
    for i, row in enumerate(cells):
        for (c0, span, inf), lines in zip(row, wrapped[i]):
            x0 = int(sum(grid[:c0]) * PX); x1 = int(sum(grid[:c0 + span]) * PX)
            y0 = y; y1 = y + heights[i]
            if inf["vm"] == "continue":
                # 위 셀과 이어짐: 좌우 테두리만
                d.line([(x0, y0), (x0, y1)], fill="black"); d.line([(x1, y0), (x1, y1)], fill="black")
                continue
            # 병합 높이 계산(restart 이후 continue 행 포함)
            yy = y1; k = i + 1
            while k < len(cells):
                nxt = [inf2 for (cc, ss, inf2) in cells[k] if cc == c0 and inf2["vm"] == "continue"]
                if not nxt: break
                yy += heights[k]; k += 1
            if inf["fill"] and inf["fill"] != "auto": d.rectangle([x0, y0, x1, yy], fill="#" + inf["fill"])
            d.rectangle([x0, y0, x1, yy], outline="black")
            f = font(inf["size"], inf["bold"]); lh = f.size * 1.35
            total_h = len(lines) * lh
            ty = y0 + (yy - y0 - total_h) / 2
            for ln in lines:
                tw = d.textlength(ln, font=f)
                if inf["align"] == "center": tx = x0 + (x1 - x0 - tw) / 2
                elif inf["align"] == "right": tx = x1 - CELL_MAR * PX - tw
                else: tx = x0 + CELL_MAR * PX
                if inf["flag"]: d.rectangle([tx, ty, tx + tw, ty + lh], fill="#FFFF99")
                d.text((tx, ty), ln, font=f, fill="black"); ty += lh
        y += heights[i]
    return img, stats, grid

def main(path, outdir):
    dd = docx.Document(path); outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    tag = Path(path).name[:2]
    for old in outdir.glob(f"{tag}_sheet_*.png"): old.unlink()
    imgs = []; lines = []
    for i, t in enumerate(dd.tables, 1):
        img, st, grid = render_table(t, i)
        imgs.append(img)
        cm = " ".join(f"{g / 567:.1f}" for g in grid)
        lines.append(f"표{i}: 열{len(grid)} 폭(cm) [{cm}] 최대줄 {st['max_lines']} 짧은셀접힘 {st['short_wrap']}")
    # 장 만들기
    sheets = []; cur = []; h = 0; ids = []; cur_ids = []
    for k, img in enumerate(imgs, 1):
        if cur and h + img.height + 20 > SHEET_H: sheets.append(cur); ids.append(cur_ids); cur = []; cur_ids = []; h = 0
        cur.append(img); cur_ids.append(k); h += img.height + 20
    if cur: sheets.append(cur); ids.append(cur_ids)
    lines.append("시트: " + ", ".join(f"{k + 1}=표{v[0]}~{v[-1]}" for k, v in enumerate(ids)))
    W = max(i.width for i in imgs) if imgs else 100
    for k, sh in enumerate(sheets, 1):
        H = sum(i.height + 20 for i in sh)
        canvas = Image.new("RGB", (W + 10, H), "#DDDDDD"); y = 0
        for i in sh: canvas.paste(i, (5, y)); y += i.height + 20
        canvas.save(outdir / f"{tag}_sheet_{k:02d}.png")
    (outdir / f"{tag}_요약.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{Path(path).name}: 표 {len(imgs)}개 → 장 {len(sheets)}개, 요약 {tag}_요약.txt")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "검토/_추출/표렌더")
