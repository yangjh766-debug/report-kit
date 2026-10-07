// deck_lib.js: 결론 먼저 쓰는 IR, 전략 덱을 PowerPoint(pptx)로 만드는 디자인 엔진
// 글자, 표, 차트는 모두 PowerPoint 도형과 텍스트라 받은 사람이 그대로 고칠 수 있다.
// 사용:
//   const D = require('<스킬 경로>/scripts/deck_lib.js')({ accent: 'FF4438', brand: '회사명' });
//   D.cover({...}); const s = D.content({...}); D.trend(s, {...}); ... ; D.save('덱.pptx');
// 필요: 작업 폴더에서 `npm install pptxgenjs@3.12.0`, 글꼴 Pretendard 설치
const fs = require('fs');
const path = require('path');

module.exports = function createDeck(opts = {}) {
  const pptxgen = require(require.resolve('pptxgenjs', { paths: [process.cwd(), __dirname] }));
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';                      // 13.333 x 7.5 in
  const ASSETS = path.join(__dirname, '..', 'assets');

  // ---------- 디자인 토큰 ----------
  const accent = (opts.accent || 'FF4438').replace('#', '');
  const C = {
    ink: '141414', text: '2B2B2B', sub: '6B6B6B', mute: '9E9B96', hair: 'D9D6D1', paper: 'F4F2EE',
    stone: 'CFCBC4', red: accent, redSoft: opts.accentSoft || 'FFE4E0', redLine: opts.accentLine || 'F6B9B0',
    white: 'FFFFFF', night: '0B0B0B', nightSub: 'A9A6A1', gray6: '6B6B6B', ...(opts.colors || {}),
  };
  const F = opts.font || 'Pretendard', FX = opts.fontDisplay || 'Pretendard ExtraBold';
  const W = 13.333, M = 0.6, GUT = 0.2, COL = (W - 2 * M - 11 * GUT) / 12;
  const gx = (c) => M + c * (COL + GUT), span = (n) => n * COL + (n - 1) * GUT;
  const brand = opts.brand || '';
  let page = 0;
  const TRANS = {}, WARN = [];

  // ---------- 기본 도형 ----------
  const T = (s, text, o) => s.addText(text, { fontFace: F, color: C.text, margin: 0, valign: 'top', ...o });
  const line = (s, x, y, w, h, color = C.hair, width = 0.75, extra = {}) => s.addShape(pres.shapes.LINE, { x, y, w, h, line: { color, width, ...extra } });
  const hair = (s, x, y, w, color = C.hair, width = 0.75) => line(s, x, y, w, 0, color, width);
  const box = (s, x, y, w, h, fill, lc, lw = 0, extra = {}) => s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill, ...(extra.transparency != null ? { transparency: extra.transparency } : {}) }, line: { color: lc || fill, width: lw, ...(extra.dashType ? { dashType: extra.dashType } : {}) } });
  const dot = (s, x, y, d, fill, lc, lw = 1) => s.addShape(pres.shapes.OVAL, { x: x - d / 2, y: y - d / 2, w: d, h: d, fill: { color: fill }, line: { color: lc || fill, width: lw } });
  const arrow = (s, x, y, w, color = C.ink, width = 1, back = false) => line(s, x, y, w, 0, color, width, back ? { beginArrowType: 'triangle' } : { endArrowType: 'triangle' });
  const big = (s, n, unit, o, color = C.ink, size = 30, usize = 12) =>
    T(s, [{ text: String(n), options: { fontFace: FX, fontSize: size, color } }, { text: unit || '', options: { fontFace: F, bold: true, fontSize: usize, color } }], { valign: 'bottom', ...o });
  const label = (s, t, x, y, w = 4, unit) => {
    T(s, t, { x, y, w, h: 0.25, fontSize: 10.5, bold: true, color: C.ink });
    if (unit) T(s, unit, { x: x + 0.13 * [...t].length + 0.2, y: y + 0.03, w: 1, h: 0.22, fontSize: 8.5, color: C.mute });
  };
  const chip = (s, x, y, text, kind = 'talk', w = 1.15) => {
    const st = { done: [C.ink, C.ink, C.white], live: [C.red, C.red, C.white], deal: [C.white, C.red, C.red], talk: [C.white, C.stone, C.sub] }[kind];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.24, rectRadius: 0.12, fill: { color: st[0] }, line: { color: st[1], width: 0.75 } });
    T(s, text, { x, y, w, h: 0.24, fontSize: 7.5, bold: true, color: st[2], align: 'center', valign: 'middle' });
  };

  // ---------- 사진: 원본 비율 지키기 ----------
  function imageSize(p) {
    const b = fs.readFileSync(p);
    if (b.readUInt32BE(0) === 0x89504e47) return [b.readUInt32BE(16), b.readUInt32BE(20)];      // PNG
    let i = 2;                                                                                   // JPEG
    while (i < b.length) {
      if (b[i] !== 0xff) { i++; continue; }
      const mk = b[i + 1], len = b.readUInt16BE(i + 2);
      if (mk >= 0xc0 && mk <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(mk)) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)];
      i += 2 + len;
    }
    return null;
  }
  // 칸 비율과 원본 비율이 달라 20% 넘게 잘리면 경고한다. 로고는 contain(자르지 않음)
  const img = (s, p, x, y, w, h, contain = false) => {
    const sz = fs.existsSync(p) ? imageSize(p) : null;
    if (!sz) WARN.push(`${page}장 사진 없음 또는 크기 읽기 실패: ${p}`);
    else if (!contain) {
      const ri = sz[0] / sz[1], rf = w / h, crop = 1 - Math.min(ri / rf, rf / ri);
      if (crop > 0.2) WARN.push(`${page}장 ${path.basename(p)}: 원본 ${ri.toFixed(2)} vs 칸 ${rf.toFixed(2)}, ${Math.round(crop * 100)}% 잘림`);
    }
    s.addImage({ path: p, x, y, w, h, sizing: { type: contain ? 'contain' : 'cover', w, h } });
  };
  // 원본 비율대로 칸 높이(또는 폭)를 정해 준다
  const fitH = (p, w) => { const sz = imageSize(p); return sz ? w * sz[1] / sz[0] : w * 0.66; };
  const fitW = (p, h) => { const sz = imageSize(p); return sz ? h * sz[0] / sz[1] : h * 1.5; };

  // ---------- 장 만들기 ----------
  function newSlide(bg = C.white, trans) { const s = pres.addSlide(); s.background = { color: bg }; page++; if (trans) TRANS[page] = trans; return s; }
  // 내용 장: 섹션 표시, 결론 제목, 부제, 각주, 쪽번호
  function content({ no = '', label: lab = '', title = '', sub = '', source = '', transition } = {}) {
    const s = newSlide(C.white, transition);
    T(s, [{ text: no, options: { color: C.red, bold: true } }, { text: (no ? '   ' : '') + lab, options: { color: C.sub, bold: true } }], { x: gx(0), y: 0.42, w: span(6), h: 0.25, fontSize: 9.5, charSpacing: 1.5 });
    if (brand) T(s, brand, { x: gx(8), y: 0.42, w: span(4), h: 0.25, fontSize: 9.5, color: C.mute, align: 'right', bold: true });
    hair(s, M, 0.78, W - 2 * M, C.ink, 1);
    if (title) T(s, title, { x: gx(0), y: 0.98, w: span(12), h: 0.6, fontSize: 25, bold: true, color: C.ink });
    if (sub) T(s, sub, { x: gx(0), y: 1.6, w: span(12), h: 0.35, fontSize: 12.5, color: C.sub });
    hair(s, M, 7.0, W - 2 * M);
    if (source) T(s, source, { x: gx(0), y: 7.06, w: span(11), h: 0.34, fontSize: 7.5, color: C.mute, lineSpacingMultiple: 1.05 });
    T(s, String(page), { x: gx(11), y: 7.08, w: span(1), h: 0.25, fontSize: 8.5, color: C.mute, align: 'right', bold: true });
    return s;
  }
  const glow = (s, x, y, d) => { const g = opts.glow || path.join(ASSETS, 'glow.png'); if (fs.existsSync(g)) s.addImage({ path: g, x, y, w: d, h: d }); };

  // ---------- 핵심 장표 ----------
  function cover({ eyebrow = '', title = '', sub = '', note = '' }) {
    const s = newSlide(C.night);
    glow(s, 5.6, -1.4, 9.0);
    T(s, eyebrow, { x: 0.9, y: 2.0, w: 8, h: 0.4, fontSize: 14, bold: true, color: C.red, charSpacing: 2 });
    T(s, title, { x: 0.85, y: 2.45, w: 11, h: 1.4, fontFace: FX, fontSize: 80, color: C.white, valign: 'middle', charSpacing: -2 });
    T(s, sub, { x: 0.9, y: 4.05, w: 9, h: 0.9, fontSize: 20, color: C.nightSub, lineSpacingMultiple: 1.15 });
    if (note) T(s, note, { x: 0.9, y: 6.85, w: 8, h: 0.3, fontSize: 9, color: '6E6B66' });
    return s;
  }
  // 숫자 하나. morph에 이름을 주고 다음 장 차트의 같은 숫자에도 같은 이름을 주면 모핑으로 이어진다
  function heroNumber({ eyebrow = '', number = '', unit = '', sub = '', note = '', morph, transition = 'fade' }) {
    const s = newSlide(C.night, transition);
    glow(s, 4.6, -0.9, 8.4);
    T(s, eyebrow, { x: 0.9, y: 1.55, w: 8, h: 0.4, fontSize: 15, bold: true, color: C.red, charSpacing: 2 });
    const size = number.length > 6 ? 150 : 200;
    T(s, number, { x: 0.75, y: 1.95, w: 11, h: 3.1, fontFace: FX, fontSize: size, color: C.white, valign: 'middle', charSpacing: -4, ...(morph ? { objectName: '!!' + morph } : {}) });
    // 단위는 숫자 폭을 어림해 바로 뒤에 둔다(Pretendard ExtraBold 숫자 폭 약 0.56em)
    const numW = [...number].reduce((a, ch) => a + (/[0-9]/.test(ch) ? 0.6 : 0.3), 0) * size / 72;
    if (unit) T(s, unit, { x: Math.min(0.85 + numW + 0.15, 11), y: 3.85, w: 2.6, h: 0.9, fontFace: FX, fontSize: 44, color: C.white, valign: 'bottom' });
    T(s, sub, { x: 0.9, y: 5.3, w: 11, h: 0.5, fontSize: 20, color: C.nightSub });
    if (note) T(s, note, { x: 0.9, y: 6.85, w: 8, h: 0.3, fontSize: 9, color: '6E6B66' });
    return s;
  }
  // 전면 사진. 왼쪽을 어둡게 눌러 글자를 얹는다(사진 비율은 16:9에 가까운 가로 사진 권장)
  // darkened: make_assets.py darken으로 미리 어둡게 만든 사진이면 true(가장 깔끔). 아니면 반투명 띠를 겹쳐 왼쪽을 누른다
  function heroPhoto({ photo, eyebrow = '', headline = '', number, unit = '', sub = '', transition = 'fade', darkened = false }) {
    const s = newSlide(C.night, transition);
    img(s, photo, 0, 0, W, 7.5);
    if (!darkened) { const n = 16; for (let i = 0; i < n; i++) { const x0 = 3.6 + i * 0.4; box(s, i === 0 ? 0 : x0, 0, i === 0 ? x0 + 0.4 : 0.4, 7.5, '0A0A0A', '0A0A0A', 0, { transparency: Math.min(95, 12 + i * 5.5) }); } }
    T(s, eyebrow, { x: 0.9, y: 1.7, w: 8, h: 0.4, fontSize: 15, bold: true, color: C.red, charSpacing: 2 });
    T(s, headline, { x: 0.85, y: 2.15, w: 8, h: 2.6, fontFace: FX, fontSize: 72, color: C.white, lineSpacingMultiple: 0.95 });
    if (number) big(s, number, ' ' + unit, { x: 0.9, y: 4.95, w: 7, h: 0.9 }, C.white, 54, 22);
    T(s, sub, { x: 0.9, y: 5.9, w: 9, h: 0.5, fontSize: 14, color: 'C9C6C1' });
    return s;
  }
  function heroQuote({ eyebrow = '', quote = '', sub = '', transition = 'fade' }) {
    const s = newSlide(C.night, transition);
    glow(s, -2.5, 1.0, 8);
    T(s, eyebrow, { x: 0.9, y: 1.9, w: 8, h: 0.4, fontSize: 15, bold: true, color: C.red, charSpacing: 2 });
    T(s, quote, { x: 0.85, y: 2.4, w: 11.5, h: 2.3, fontFace: FX, fontSize: 58, color: C.white, lineSpacingMultiple: 1.0 });
    T(s, sub, { x: 0.9, y: 4.95, w: 11, h: 0.9, fontSize: 17, color: C.nightSub, lineSpacingMultiple: 1.25 });
    return s;
  }
  function closing({ line: ln = '', name = '', sub = '', transition = 'fade' }) {
    const s = newSlide(C.night, transition);
    glow(s, 5.6, -1.4, 9.0);
    T(s, ln, { x: 0.85, y: 2.2, w: 11, h: 2.4, fontFace: FX, fontSize: 58, color: C.white, lineSpacingMultiple: 1.02 });
    T(s, name, { x: 0.9, y: 4.95, w: 8, h: 0.5, fontFace: FX, fontSize: 22, color: C.red });
    T(s, sub, { x: 0.9, y: 5.45, w: 11, h: 0.4, fontSize: 14, color: C.nightSub });
    return s;
  }
  // 한 장 요약: 왼쪽 결론 문장, 오른쪽 핵심 숫자 3개
  function summary({ statement = '', tagline = '', rows = [], source = '' }) {
    const s = content({ no: '00', label: 'EXECUTIVE SUMMARY', source });
    T(s, statement, { x: gx(0), y: 1.3, w: span(5), h: 4.4, fontFace: FX, fontSize: 34, color: C.ink, lineSpacingMultiple: 1.08 });
    box(s, gx(0), 5.95, 0.5, 0.06, C.red);
    T(s, tagline, { x: gx(0), y: 6.15, w: span(5), h: 0.3, fontSize: 11, color: C.sub });
    const rx = gx(6), rw = span(6), gap = Math.min(1.82, 5.45 / Math.max(rows.length, 1));
    rows.forEach((r, i) => {
      const y = 1.3 + i * gap;
      hair(s, rx, y, rw, C.ink, 1);
      T(s, [{ text: String(i + 1).padStart(2, '0'), options: { color: C.red, bold: true } }, { text: '  ' + (r.tag || ''), options: { color: C.sub, bold: true } }], { x: rx, y: y + 0.14, w: 2.5, h: 0.22, fontSize: 9, charSpacing: 1 });
      big(s, r.n, r.u, { x: rx, y: y + 0.42, w: 2.1, h: 0.85 }, i === 0 ? C.red : C.ink, 44, 16);
      T(s, r.head, { x: rx + 2.25, y: y + 0.48, w: rw - 2.25, h: 0.32, fontSize: 14, bold: true, color: C.ink });
      T(s, r.body, { x: rx + 2.25, y: y + 0.88, w: rw - 2.25, h: 0.6, fontSize: 10, color: C.sub, lineSpacingMultiple: 1.15 });
    });
    return s;
  }

  // ---------- 차트 ----------
  // 추이 막대. kind: 'past'(회색) | 'base'(검정) | 'plan'(점선) | 'hero'(강조색)
  function trend(s, { x = gx(0), y = 2.15, w = span(6), h = 3.55, label: lab = '', unit = '', data = [], morph, row }) {
    const base = y + h, top = y + 0.6, maxv = Math.max(...data.map((d) => d.v)), slot = w / data.length, bw = slot * 0.52;
    if (lab) label(s, lab, x, y, w, unit);
    data.forEach((d, i) => {
      const hh = (base - top) * d.v / maxv, bx = x + i * slot + (slot - bw) / 2, by = base - hh, k = d.kind || 'past';
      const st = { past: [C.stone, C.stone, 0], base: [C.ink, C.ink, 0], plan: [C.redSoft, C.red, 1], hero: [C.red, C.red, 0] }[k];
      box(s, bx, by, bw, hh, st[0], st[1], st[2], k === 'plan' ? { dashType: 'dash' } : {});
      const strong = k !== 'past', last = i === data.length - 1;
      T(s, d.label || d.v.toLocaleString(), { x: bx - 0.3, y: by - (strong ? 0.38 : 0.28), w: bw + 0.6, h: strong ? 0.34 : 0.24, fontSize: strong ? (last ? 17 : 13) : 9.5,
        bold: true, align: 'center', valign: 'bottom', color: k === 'plan' || k === 'hero' ? C.red : strong ? C.ink : C.sub, ...(last && morph ? { objectName: '!!' + morph } : {}) });
      T(s, d.l, { x: bx - 0.3, y: base + 0.08, w: bw + 0.6, h: 0.22, fontSize: 9, bold: strong, align: 'center', color: strong ? C.ink : C.sub });
    });
    hair(s, x, base, w, C.ink, 1);
    if (row) {   // 아래 보조 지표 줄(예: 영업이익). row = { name, values: [[막대 순번, '값', 강조 여부]] }
      T(s, row.name, { x, y: base + 0.45, w: 1.4, h: 0.22, fontSize: 8.5, bold: true, color: C.sub });
      row.values.forEach(([i, v, hi]) => T(s, v, { x: x + i * slot, y: base + 0.42, w: slot, h: 0.26, fontSize: 10.5, bold: true, align: 'center', color: hi ? C.red : C.ink }));
      hair(s, x, base + 0.78, w);
    }
  }
  // 다리형 차트(증감 분해). steps: [{l, v, kind: 'base'|'up'|'down'|'hero'|'soft'|'total', sub}]
  function bridge(s, { x = gx(7), y = 2.15, w = span(5), h = 3.55, label: lab = '', unit = '', steps = [], max, plan, note }) {
    const base = y + h, top = y + 0.6; let run = 0; const pts = [];
    steps.forEach((st) => {
      if (st.kind === 'base' || st.kind === 'total') { pts.push([0, st.v]); run = st.v; }
      else if (st.kind === 'down') { pts.push([run - st.v, st.v]); run -= st.v; }
      else { pts.push([run, st.v]); run += st.v; }
    });
    const mx = max || Math.max(...pts.map(([f, v]) => f + v), plan ? plan.v : 0), sc = (base - top) / mx;
    const sl = w / steps.length, sw = sl * 0.58;
    if (lab) label(s, lab, x, y, w, unit);
    steps.forEach((st, i) => {
      const [from, v] = pts[i], bx = x + i * sl + (sl - sw) / 2, by = base - (from + v) * sc, hh = v * sc;
      const col = { base: C.ink, up: C.stone, down: C.mute, hero: C.red, soft: C.redLine, total: C.red }[st.kind || 'up'];
      box(s, bx, by, sw, hh, col);
      if (i < steps.length - 1) line(s, bx + sw, st.kind === 'down' ? by + hh : by, sl - sw, 0, C.mute, 0.5, { dashType: 'dash' });
      const lb = st.kind === 'base' || st.kind === 'total' ? st.v.toLocaleString() : (st.kind === 'down' ? '−' : '+') + st.v.toLocaleString();
      const em = st.kind === 'hero' || st.kind === 'total';
      T(s, lb, { x: bx - 0.3, y: by - 0.34, w: sw + 0.6, h: 0.3, fontSize: em ? 15 : 12, bold: true, align: 'center', valign: 'bottom', color: em ? C.red : C.ink });
      T(s, st.l, { x: bx - 0.35, y: base + 0.08, w: sw + 0.7, h: 0.22, fontSize: 9, bold: true, align: 'center', color: st.kind === 'hero' ? C.red : C.ink });
      if (st.sub) T(s, st.sub, { x: bx - 0.35, y: base + 0.3, w: sw + 0.7, h: 0.2, fontSize: 8, align: 'center', color: C.sub });
    });
    hair(s, x, base, w, C.ink, 1);
    if (plan) {
      const py = base - plan.v * sc;
      line(s, x, py, w, 0, C.ink, 0.75, { dashType: 'dash' });
      T(s, plan.label || '계획 ' + plan.v, { x, y: py - 0.24, w: 1.8, h: 0.2, fontSize: 8.5, bold: true, color: C.ink });
    }
    if (note) T(s, note, { x, y: base + 0.55, w, h: 0.26, fontSize: 10, color: C.sub });
  }
  // 가로 줄의 핵심 지표. items: [{n, u, head, desc}] 첫 칸 강조
  function kpis(s, { y = 2.15, items = [], x = M, w = W - 2 * M, size = 40 }) {
    const n = items.length, kw = (w - GUT * (n - 1)) / n;
    items.forEach((it, i) => {
      const kx = x + i * (kw + GUT);
      hair(s, kx, y, kw, i === 0 ? C.red : C.ink, i === 0 ? 2 : 1);
      big(s, it.n, it.u, { x: kx, y: y + 0.1, w: kw, h: 0.75 }, i === 0 ? C.red : C.ink, size, 16);
      T(s, it.head, { x: kx, y: y + 0.9, w: kw, h: 0.26, fontSize: 11, bold: true, color: C.ink });
      if (it.desc) T(s, it.desc, { x: kx, y: y + 1.18, w: kw, h: 0.45, fontSize: 9, color: C.sub, lineSpacingMultiple: 1.1 });
    });
  }
  // 계획 대비 구성 막대. rows: [{name, plan, parts:[{n, v, col}], total, gap}]
  function planRows(s, { x = gx(0), y = 2.15, w = span(8), label: lab = '', unit = '', max, rows = [] }) {
    const lw = 1.6, bx = x + lw, bw = w - lw, mx = max || Math.max(...rows.map((r) => Math.max(r.plan || 0, r.parts.reduce((a, p) => a + p.v, 0)))) * 1.12, sc = bw / mx;
    if (lab) label(s, lab, x, y, 4, unit);
    rows.forEach((r, i) => {
      const ry = y + 0.6 + i * 1.3, h = 0.55;
      hair(s, x, ry - 0.2, w, C.hair);
      T(s, r.name, { x, y: ry + 0.12, w: lw, h: 0.3, fontSize: 12, bold: true, color: i === 0 ? C.red : C.ink });
      let px = bx; const narrow = r.parts.some((p) => p.v * sc < 0.9);
      r.parts.forEach((p) => {
        const pw = p.v * sc, col = p.col || C.stone, dark = [C.ink, C.red, C.gray6].includes(col);
        box(s, px, ry, pw, h, col, C.white, 1.5);
        if (pw > 0.55) T(s, String(p.v), { x: px + 0.08, y: ry, w: pw - 0.1, h, fontSize: 12, bold: true, color: dark ? C.white : C.ink, valign: 'middle' });
        if (!narrow) T(s, p.n, { x: px, y: ry + h + 0.05, w: Math.max(pw, 0.9), h: 0.2, fontSize: 8, color: C.sub });
        px += pw;
      });
      if (narrow) T(s, r.parts.map((p) => p.n + ' ' + p.v).join(', '), { x: bx, y: ry + h + 0.05, w: bw * 0.8, h: 0.2, fontSize: 8, color: C.sub });
      if (r.plan) {
        const pl = bx + r.plan * sc;
        line(s, pl, ry - 0.1, 0, h + 0.2, C.ink, 1.25, { dashType: 'dash' });
        T(s, '계획 ' + r.plan, { x: pl - 0.6, y: ry - 0.32, w: 1.2, h: 0.2, fontSize: 8, bold: true, color: C.ink, align: 'center' });
      }
      if (r.total) T(s, String(r.total), { x: bx + bw - 0.8, y: ry + 0.02, w: 0.8, h: 0.4, fontFace: FX, fontSize: 18, color: i === 0 ? C.red : C.ink, align: 'right' });
      if (r.gap) T(s, r.gap, { x: bx + bw - 1.3, y: ry + 0.42, w: 1.3, h: 0.2, fontSize: 8.5, bold: true, color: i === 0 ? C.red : C.sub, align: 'right' });
    });
  }
  // 가로 막대 비교(예: 배수 비교). items: [{n, v, kind: 'mine'|'ref'|'other'}]
  function barsH(s, { x = gx(0), y = 2.15, w = span(7), label: lab = '', unit = '', items = [], fmt = (v) => v.toFixed(1) }) {
    const nameW = 1.9, bx = x + nameW, bw = w - nameW - 0.8, mx = Math.max(...items.map((i) => i.v)) * 1.05, sc = bw / mx;
    if (lab) label(s, lab, x, y, 5);
    items.forEach((it, i) => {
      const iy = y + 0.45 + i * 0.5, mine = it.kind === 'mine', ref = it.kind === 'ref';
      T(s, it.n, { x, y: iy + 0.04, w: nameW - 0.1, h: 0.3, fontSize: 10, bold: mine || ref, color: mine ? C.red : C.ink });
      box(s, bx, iy, it.v * sc, 0.34, mine ? C.red : ref ? C.ink : C.stone);
      T(s, fmt(it.v) + unit, { x: bx + it.v * sc + 0.08, y: iy + 0.02, w: 0.9, h: 0.3, fontSize: 10, bold: true, color: mine ? C.red : C.ink });
    });
  }
  // 100% 구성 막대(예: 지분율 전후). bars: [{name, parts:[{n, v(%), col}]}]
  function shareBars(s, { x = gx(5), y = 2.15, w = span(7), label: lab = '', bars = [] }) {
    if (lab) label(s, lab, x, y, w);
    const bx = x + 0.85, bw = w - 0.85;
    bars.forEach((b, i) => {
      const by = y + 0.45 + i * 0.95; let px = bx;
      T(s, b.name, { x, y: by + 0.08, w: 0.8, h: 0.3, fontSize: 10, bold: true, color: C.ink });
      b.parts.forEach((p) => {
        const pw = bw * p.v / 100, col = p.col || C.stone, dark = [C.ink, C.red].includes(col);
        box(s, px, by, pw, 0.45, col, C.white, 1.5);
        if (pw > 0.75) { T(s, p.v.toFixed(2) + '%', { x: px + 0.06, y: by, w: pw - 0.1, h: 0.45, fontSize: 9.5, bold: true, color: dark ? C.white : C.ink, valign: 'middle' }); T(s, p.n, { x: px, y: by + 0.5, w: pw, h: 0.2, fontSize: 8, color: C.sub }); }
        px += pw;
      });
    });
  }
  // 100% 가로 띠(예: 자금 사용). parts: [{v, col}] 합계 기준 비율
  function strip(s, { x = M, y = 2.2, w = W - 2 * M, h = 0.7, parts = [] }) {
    const tot = parts.reduce((a, p) => a + p.v, 0); let px = x;
    parts.forEach((p) => {
      const pw = w * p.v / tot, col = p.col || C.stone;
      box(s, px, y, pw, h, col, C.white, 2);
      T(s, String(p.label || p.v), { x: px + 0.15, y, w: pw - 0.2, h, fontFace: FX, fontSize: pw > 1 ? 22 : 14, color: col === C.stone ? C.ink : C.white, valign: 'middle' });
      px += pw;
    });
  }

  // ---------- 구조 ----------
  // 타임라인. events: [{t, d}] 마지막을 강조
  function timeline(s, { y = 2.45, events = [], x = M, w = W - 2 * M }) {
    const st = w / events.length;
    hair(s, x, y, w, C.ink, 1);
    events.forEach((e, i) => {
      const ex = x + i * st, last = i === events.length - 1;
      dot(s, ex + 0.09, y, 0.18, last ? C.red : C.white, last ? C.red : C.ink, 1.25);
      T(s, e.t, { x: ex, y: y + 0.22, w: st - 0.2, h: 0.4, fontFace: FX, fontSize: 20, color: last ? C.red : C.ink });
      T(s, e.d, { x: ex, y: y + 0.68, w: st - 0.25, h: 0.8, fontSize: 9.5, color: C.text, lineSpacingMultiple: 1.15 });
    });
  }
  // 가치사슬 화살 띠. steps: [{stage, title, desc}] highlight: 강조할 순번
  function chevrons(s, { y = 2.35, steps = [], highlight = -1, owners }) {
    const n = steps.length, cw = (W - 2 * M - GUT * (n - 1)) / n;
    steps.forEach((st, i) => {
      const x = M + i * (cw + GUT), hi = i === highlight || (owners && owners[i] === 'own');
      const fill = owners ? (owners[i] === 'own' ? C.red : owners[i] === 'both' ? C.redSoft : C.paper) : (hi ? C.red : C.ink);
      const tc = owners ? (owners[i] === 'own' ? C.white : C.ink) : C.white;
      s.addShape(pres.shapes.CHEVRON, { x, y, w: cw + (i < n - 1 ? 0.12 : 0), h: 0.5, fill: { color: fill }, line: { color: C.white, width: 0 } });
      T(s, st.stage, { x: x + 0.15, y, w: cw - 0.2, h: 0.5, fontSize: 11.5, bold: true, color: tc, align: 'center', valign: 'middle' });
      if (st.title) T(s, st.title, { x, y: y + 0.7, w: cw, h: 0.3, fontSize: 11.5, bold: true, color: C.ink, align: owners ? 'center' : 'left' });
      if (st.desc) T(s, st.desc, { x, y: y + (st.title ? 1.05 : 0.7), w: cw, h: 0.6, fontSize: 9, color: C.sub, lineSpacingMultiple: 1.15, align: owners ? 'center' : 'left' });
    });
  }
  // 번호 카드 격자(같은 크기). items: [{head, desc}] cols 기본 4. extra: 남는 칸에 넣을 강조 상자 {eyebrow, head, body}
  function cards(s, { y = 2.2, items = [], cols = 4, rowH = 2.3, extra }) {
    const cw = (W - 2 * M - GUT * (cols - 1)) / cols;
    items.forEach((it, i) => {
      const x = M + (i % cols) * (cw + GUT), cy = y + Math.floor(i / cols) * rowH;
      hair(s, x, cy, cw, i === 0 ? C.red : C.ink, i === 0 ? 2 : 1);
      T(s, String(i + 1).padStart(2, '0'), { x, y: cy + 0.15, w: 0.8, h: 0.45, fontFace: FX, fontSize: 24, color: i === 0 ? C.red : C.stone });
      T(s, it.head, { x, y: cy + 0.7, w: cw, h: 0.3, fontSize: 12.5, bold: true, color: C.ink });
      T(s, it.desc, { x, y: cy + 1.08, w: cw, h: 0.7, fontSize: 9.5, color: C.sub, lineSpacingMultiple: 1.15 });
    });
    if (extra) {
      const i = items.length, x = M + (i % cols) * (cw + GUT), cy = y + Math.floor(i / cols) * rowH + 0.05;
      callout(s, { x, y: cy, w: cw, h: rowH - 0.25, ...extra });
    }
  }
  // 강조 상자(회색 바탕 + 위 강조선)
  function callout(s, { x, y, w, h, eyebrow = '', head = '', body = '' }) {
    box(s, x, y, w, h, C.paper); box(s, x, y, w, 0.05, C.red);
    if (eyebrow) T(s, eyebrow, { x: x + 0.2, y: y + 0.22, w: w - 0.4, h: 0.22, fontSize: 9, bold: true, color: C.red, charSpacing: 1 });
    T(s, head, { x: x + 0.2, y: y + (eyebrow ? 0.52 : 0.25), w: w - 0.4, h: 0.7, fontSize: 13, bold: true, color: C.ink, lineSpacingMultiple: 1.1 });
    if (body) T(s, body, { x: x + 0.2, y: y + h - 0.85, w: w - 0.4, h: 0.7, fontSize: 9, color: C.sub, lineSpacingMultiple: 1.15 });
  }
  // 단계별 파이프라인. stages: [{name, kind, cards:[{name, sub, photo, key, logo}]}] callout: 첫 칸 빈자리에 넣을 상자
  function pipeline(s, { y = 2.25, stages = [], callout: co }) {
    const colW = span(3);
    stages.forEach((st, ci) => {
      const x = gx(ci * 3), dc = { done: C.ink, live: C.red, deal: C.white, talk: C.white }[st.kind];
      s.addShape(pres.shapes.OVAL, { x, y: y + 0.03, w: 0.18, h: 0.18, fill: { color: dc }, line: { color: st.kind === 'talk' ? C.stone : st.kind === 'done' ? C.ink : C.red, width: 1.25 } });
      T(s, st.name, { x: x + 0.28, y: y - 0.02, w: colW - 0.3, h: 0.28, fontSize: 11, bold: true, color: st.kind === 'live' ? C.red : C.ink, valign: 'middle' });
      st.cards.forEach((c, k) => {
        const cy = y + 0.5 + k * 1.38, hasImg = !!c.photo, tx = hasImg ? x + 1.08 : x;
        hair(s, x, cy, colW, st.kind === 'talk' ? C.stone : C.ink, 1);
        if (hasImg) img(s, c.photo, x, cy + 0.14, 0.95, 0.95, !!c.logo);
        T(s, c.name, { x: tx, y: cy + 0.14, w: colW - (tx - x), h: 0.26, fontSize: 10.5, bold: true, color: C.ink });
        T(s, c.sub || '', { x: tx, y: cy + 0.42, w: colW - (tx - x), h: 0.2, fontSize: 8, bold: true, color: C.mute });
        T(s, c.key || '', { x: tx, y: cy + 0.66, w: colW - (tx - x), h: 0.42, fontSize: 8.5, color: C.text, lineSpacingMultiple: 1.1 });
      });
    });
    if (co) callout(s, { x: gx(0), y: y + 0.5 + 1.38, w: colW, h: 2.55, ...co });
  }
  // 표(얇은 선). cols: [{h, w}] rows: [[...]] em: 강조색으로 쓸 열 번호
  function table(s, { y = 3.0, cols = [], rows = [], em = -1, rowH = 0.6, x = M }) {
    const tw = cols.reduce((a, c) => a + c.w, 0);
    let cx = x; cols.forEach((c) => { T(s, c.h, { x: cx, y, w: c.w, h: 0.25, fontSize: 9, bold: true, color: C.sub }); cx += c.w; });
    hair(s, x, y + 0.32, tw, C.ink, 1);
    let ry = y + 0.42;
    rows.forEach((r) => {
      let rx = x;
      r.forEach((v, ci) => {
        const hi = ci === em && v && v !== '-';
        T(s, v, { x: rx, y: ry + 0.08, w: cols[ci].w - 0.15, h: rowH - 0.1, fontSize: ci === 0 ? 11 : 9.5, bold: ci === 0 || hi, color: hi ? C.red : C.text, lineSpacingMultiple: 1.1 });
        rx += cols[ci].w;
      });
      ry += rowH; hair(s, x, ry, tw, C.hair);
    });
  }
  // 아이콘 줄. items: [{icon: 'infra'|'capital'|'venue'|'refs' 또는 png 경로, head, desc}]
  function iconRow(s, { y = 6.15, items = [], title }) {
    if (title) T(s, title, { x: gx(0), y: y - 0.3, w: 4, h: 0.25, fontSize: 9, bold: true, color: C.mute, charSpacing: 1 });
    const n = items.length, cw = (W - 2 * M - GUT * (n - 1)) / n;
    items.forEach((it, i) => {
      const x = M + i * (cw + GUT), ic = it.icon.endsWith('.png') ? it.icon : path.join(ASSETS, 'icons', it.icon + '.png');
      s.addImage({ path: ic, x, y, w: 0.42, h: 0.42 });
      T(s, it.head, { x: x + 0.55, y: y - 0.02, w: cw - 0.55, h: 0.22, fontSize: 10, bold: true, color: C.ink });
      T(s, it.desc, { x: x + 0.55, y: y + 0.22, w: cw - 0.55, h: 0.42, fontSize: 8.5, color: C.sub, lineSpacingMultiple: 1.1 });
    });
  }
  // 사진 카드 줄(원본 비율 유지). items: [{photo, t, title, desc}] ratio: 칸 비율(가로/세로)
  function photoRow(s, { y = 2.38, items = [], ratio = 1.8, label: lab, labelColor }) {
    const n = items.length, cw = (W - 2 * M - GUT * (n - 1)) / n, ph = cw / ratio;
    if (lab) T(s, lab, { x: M, y: y - 0.28, w: 4, h: 0.22, fontSize: 9, bold: true, color: labelColor || C.mute, charSpacing: 1 });
    items.forEach((it, i) => {
      const x = M + i * (cw + GUT);
      img(s, it.photo, x, y, cw, ph);
      T(s, it.t || '', { x, y: y + ph + 0.1, w: 1.0, h: 0.22, fontSize: 9, bold: true, color: C.mute });
      T(s, it.title, { x: x + 0.95, y: y + ph + 0.08, w: cw - 0.95, h: 0.25, fontSize: 11, bold: true, color: C.ink });
      T(s, it.desc || '', { x: x + 0.95, y: y + ph + 0.38, w: cw - 0.95, h: 0.45, fontSize: 8.5, color: C.sub, lineSpacingMultiple: 1.1 });
    });
    return y + ph + 0.85;
  }

  // ---------- 저장 ----------
  async function save(file) {
    const out = path.resolve(file);
    await pres.writeFile({ fileName: out });
    fs.writeFileSync(out.replace(/\.pptx$/, '.transitions.txt'), Object.entries(TRANS).map(([k, v]) => k + ':' + v).join(','));
    console.log('저장:', out);
    if (WARN.length) { console.log('사진 경고:\n' + WARN.join('\n')); process.exitCode = 2; } else console.log('사진 잘림 검사: 0건');
    return out;
  }

  return { pres, C, F, FX, W, M, GUT, gx, span, T, line, hair, box, dot, arrow, big, label, chip, img, fitH, fitW, imageSize,
    newSlide, content, cover, heroNumber, heroPhoto, heroQuote, closing, summary,
    trend, bridge, kpis, planRows, barsH, shareBars, strip, timeline, chevrons, cards, callout, pipeline, table, iconRow, photoRow, save,
    get page() { return page; } };
};
