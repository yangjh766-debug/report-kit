// 예시 덱: 가상의 회사 'MediNote'(병원용 진료 기록 AI 구독 서비스)와 가상의 숫자
// 실행(이 examples 폴더에서): npm install pptxgenjs@3.12.0 && node sample_deck.js
//   && python3 ../scripts/finalize.py 예시_디자인덱.pptx "$(cat 예시_디자인덱.transitions.txt)" && python3 ../scripts/check_text.py 예시_디자인덱.pptx
// 숫자 관계(모두 가상): ARR '25 85 → '27P 260 = 85 + 신규 95 + 확장 55 + 해외 25
//   고객 1곳 연 2,400만원 × 매출총이익률 82% ÷ 12 = 월 164만원, CAC 1,800만원 ÷ 164 = 약 11개월, LTV(5년) 9,840만원 / CAC = 약 5.5배
const path = require('path');
const I = (f) => path.join(__dirname, 'images', f);
const D = require('../scripts/deck_lib.js')({ accent: '0E8C7F', accentSoft: 'DDF1EE', accentLine: 'A8D8D1', brand: 'MediNote', glow: I('glow_teal.png') });
const { C, gx, span, M, W, T, hair, box, line, big, label } = D;

D.cover({ eyebrow: '회사소개 및 IR   |   2026', title: 'MediNote', sub: '진료 기록을 대신 쓰는\n병원용 의료 AI 구독 서비스', note: '예시 덱. 회사와 숫자는 모두 가상입니다   |   단위: 억원' });

D.summary({
  statement: '진료 기록 AI를\n병원 전체로 넓혀\n2027년 ARR\n260억원을 만듭니다',
  tagline: '진료 기록을 대신 쓰는 병원용 의료 AI 구독 서비스',
  source: "ARR은 연간 반복 매출. '27P는 사업계획 기준(가상). 증가분 175억원은 신규 고객 +95, 기존 고객 확장 +55, 해외 +25의 합",
  rows: [
    { tag: '성장', n: '3.1', u: '배', head: '2년 만에 ARR이 세 배가 됩니다', body: "'25 85억원에서 '27P 260억원으로 늘어나고,\n증가분 175억원 중 55억원은 기존 고객 확장입니다" },
    { tag: '고객 확장', n: '128', u: '%', head: '기존 고객 매출이 해마다 28% 늘어납니다', body: '진료과를 넓혀 쓸수록 계약 금액이 커지는 구조\n도입 3년 뒤 고객 매출은 약 2.1배' },
    { tag: '효율', n: '11', u: '개월', head: '고객 확보 비용을 11개월 만에 회수합니다', body: '고객 생애 가치는 확보 비용의 약 5.5배\n이탈률은 연 3%' },
  ],
});

D.heroNumber({ eyebrow: '2027 ARR 계획', number: '260', unit: '억원', sub: '2025년의 약 3.1배. 기존 고객의 확장이 성장을 받칩니다', note: "'27P는 사업계획 기준(가상)", morph: 'n260' });

{
  const s = D.content({ no: '01', label: 'GROWTH', title: '2027년까지 늘어날 ARR 175억원 중 절반 이상을 신규 고객이 만듭니다', sub: "'25 85억원에서 '26E 150억원, '27P 260억원으로. 영업이익은 '26년에 흑자로 돌아섭니다",
    source: "'23~'25 실적, '26E 전망, '27P 사업계획(가상). 영업이익 단위 억원", transition: 'morph' });
  D.trend(s, { label: 'ARR 추이', unit: '억원', data: [{ l: "'23", v: 18 }, { l: "'24", v: 42 }, { l: "'25", v: 85, kind: 'base' }, { l: "'26E", v: 150, kind: 'plan' }, { l: "'27P", v: 260, kind: 'hero' }], morph: 'n260',
    row: { name: '영업이익', values: [[2, '−12'], [3, '5', true], [4, '38', true]] } });
  D.bridge(s, { label: "'25에서 '27P까지 늘어나는 ARR", unit: '억원', steps: [{ l: "'25", v: 85, kind: 'base' }, { l: '신규 고객', v: 95, kind: 'hero' }, { l: '기존 고객 확장', v: 55 }, { l: '해외', v: 25 }, { l: "'27P", v: 260, kind: 'total' }],
    note: '신규 고객 95 / 175억원, 증가분의 54%' });
}

{
  const s = D.content({ no: '01', label: 'FINANCIAL HIGHLIGHTS', title: 'ARR은 연 75%씩 늘고, 2027년 영업이익률은 14.6%가 됩니다', sub: '구독 매출이라 다음 해 매출의 대부분이 연초에 이미 확보되어 있습니다',
    source: "연평균 성장률 = (260 / 85)^(1/2) − 1. 영업이익률 '27P 38/260. NRR은 1년 전 고객의 올해 매출 / 그 고객의 작년 매출(가상)" });
  D.kpis(s, { items: [{ n: '75', u: '%', head: 'ARR 연평균 성장률', desc: "'25 85억원에서 '27P 260억원" }, { n: '128', u: '%', head: '기존 고객 매출 유지율(NRR)', desc: '진료과 확대로 계약 금액 증가' }, { n: '14.6', u: '%', head: "'27P 영업이익률", desc: "'25 −14%에서 흑자 전환" }, { n: '3', u: '%', head: '연간 고객 이탈률', desc: '도입 후 해지가 드문 구조' }] });
  D.planRows(s, { y: 4.1, w: span(8), label: "'27P 고객군별 ARR", unit: '억원', rows: [
    { name: '국내 의원', plan: 120, parts: [{ n: '기존 고객', v: 70, col: C.ink }, { n: '신규 고객', v: 50, col: C.red }], total: 120, gap: '계획 충족' },
    { name: '국내 병원', plan: 115, parts: [{ n: '기존 고객', v: 60, col: C.ink }, { n: '신규 고객', v: 55, col: C.red }], total: 115, gap: '계획 충족' },
  ] });
  D.callout(s, { x: gx(9), y: 4.1, w: span(3), h: 2.6, eyebrow: '투자자가 볼 점', head: '성장의 절반이\n이미 쓰는 고객에게서 나옵니다', body: '한 진료과에서 시작해 병원 전체로\n넓히는 동안 영업비가 거의 들지 않습니다' });
}

D.heroPhoto({ photo: I('hero_dark.jpg'), darkened: true, eyebrow: '기존 고객 매출 유지율', headline: '도입 3년 뒤\n매출 2.1배', number: '128', unit: '% NRR', sub: '고객이 진료과를 넓혀 쓸수록 계약 금액이 커집니다. 128%를 3년 이어 가면 약 2.1배입니다' });

{
  const s = D.content({ no: '02', label: 'CUSTOMERS', title: '의원 한 곳에서 시작해 대학병원 전 병동까지 넓혔습니다', sub: '작은 의원에서 검증한 제품을 진료과가 많은 병원으로 넓혀 왔습니다', source: '예시 이미지와 가상 사례' });
  const yEnd = D.photoRow(s, { label: '도입 사례', items: [
    { photo: I('wide_1.jpg'), t: '2023', title: '의원 A  첫 유료 고객', desc: '내과 의원 1곳, 원장 2명\n기록 시간 절반으로 단축' },
    { photo: I('wide_2.jpg'), t: '2024', title: '병원 B  5개 진료과', desc: '내과로 시작해 6개월 만에\n5개 진료과로 확대' },
    { photo: I('wide_3.jpg'), t: '2025', title: '대학병원 C  전 병동', desc: '외래와 입원 기록 전체 적용\n의료진 1,200명 사용' },
  ] });
  D.kpis(s, { y: yEnd + 0.25, size: 30, items: [{ n: '420', u: '곳', head: '고객 의료기관', desc: "'25말 기준(가상)" }, { n: '180', u: '만 건', head: '월 기록 건수', desc: '외래와 입원 합계' }, { n: '40', u: '종', head: '연동 전자의무기록', desc: '국내 주요 EMR 대부분' }] });
}

{
  const s = D.content({ no: '02', label: 'UNIT ECONOMICS', title: '고객 한 곳을 얻는 데 쓴 비용은 11개월이면 돌아옵니다', sub: '고객 1곳 연 2,400만원, 매출총이익률 82%. 확보 비용 1,800만원을 월 164만원씩 회수합니다',
    source: '고객 1곳 평균(가상). 월 매출총이익 = 2,400만원 × 82% ÷ 12. 고객 생애 가치(5년) = 2,400만원 × 82% × 5 = 9,840만원' });
  const lx = gx(0), base = 5.2, top = 2.75, sc = (base - top) / 2400;
  label(s, '고객 1곳 연 매출', lx, 2.15, 3, '만원');
  [['매출총이익', 1968, C.red, C.white], ['원가', 432, C.stone, C.ink]].reduce((yb, [n, v, col, tc]) => {
    const h = v * sc, y = yb - h; box(s, lx, y, 1.05, h, col, C.white, 1.5);
    T(s, v.toLocaleString(), { x: lx, y, w: 1.05, h, fontSize: 12, bold: true, color: tc, align: 'center', valign: 'middle' });
    T(s, n, { x: lx + 1.17, y: y + h / 2 - 0.12, w: 1.4, h: 0.24, fontSize: 9, color: C.sub, valign: 'middle' }); return y;
  }, base);
  hair(s, lx, base, span(3), C.ink, 1);
  big(s, '82', '% 매출총이익률', { x: lx, y: base + 0.1, w: span(3), h: 0.4 }, C.red, 20, 9.5);
  const rx = gx(4) + 0.2, rw = gx(12) - 0.2 - rx, n = 18, gap = 0.06, cw = (rw - gap * (n - 1)) / n, mx = 164 * n, sc2 = (base - top) / mx;
  label(s, '누적 매출총이익', rx, 2.15, 3, '만원');
  for (let m = 1; m <= n; m++) {
    const v = 164 * m, h = v * sc2, x = rx + (m - 1) * (cw + gap), paid = v >= 1800;
    box(s, x, base - h, cw, h, paid ? C.red : C.redSoft, paid ? C.red : C.redLine, 0.75);
    if (m % 3 === 0 || m === 11) T(s, m + '개월', { x: x - 0.2, y: base + 0.08, w: cw + 0.4, h: 0.2, fontSize: 7.5, color: m === 11 ? C.red : C.mute, bold: m === 11, align: 'center' });
  }
  const cy = base - 1800 * sc2;
  line(s, rx, cy, rw, 0, C.ink, 1, { dashType: 'dash' });
  T(s, '고객 확보 비용 1,800만원', { x: rx, y: cy - 0.26, w: 3, h: 0.22, fontSize: 9, bold: true, color: C.ink });
  T(s, [{ text: '11', options: { fontFace: D.FX, fontSize: 28, color: C.red } }, { text: ' 개월에 회수,  고객 생애 가치는 확보 비용의 ', options: { fontSize: 11, bold: true, color: C.ink } }, { text: '5.5', options: { fontFace: D.FX, fontSize: 22, color: C.red } }, { text: ' 배', options: { fontSize: 11, bold: true, color: C.ink } }],
    { x: rx, y: 2.2, w: rw, h: 0.45, align: 'right', valign: 'bottom' });
  hair(s, rx, base, rw, C.ink, 1);
  D.iconRow(s, { y: 6.15, title: '확장이 쉬운 이유', items: [{ icon: 'infra', head: 'EMR 40종 연동', desc: '설치 없이 기존 진료 화면에서\n바로 사용' }, { icon: 'capital', head: '진료과 단위 과금', desc: '쓰는 진료과만큼만 내고\n넓힐 때 자동 증액' }, { icon: 'venue', head: '병원 단위 계약', desc: '첫 진료과 성과로\n병원 전체 계약 전환' }, { icon: 'refs', head: '의료진 추천', desc: '신규 고객의 41%가\n기존 고객 소개' }] });
}

D.heroQuote({ eyebrow: '도입 병원 인터뷰(가상)', quote: '기록하던 시간에\n환자를 한 명 더 봅니다', sub: '진료 1건당 기록 시간이 6분에서 3분으로 줄었습니다.\n하루 40명을 보는 의원이면 2시간이 남습니다' });

{
  const s = D.content({ no: '03', label: 'SALES PIPELINE', title: '대형 병원 9곳 중 1곳은 전면 도입, 8곳은 도입과 계약이 진행 중입니다', sub: '계약 단계별 대형 병원 영업 현황. 한 진료과로 시작해 병원 전체로 넓히는 방식입니다', source: '가상의 고객과 계약 단계' });
  D.pipeline(s, { stages: [
    { name: '전면 도입', kind: 'done', cards: [{ name: '대학병원 C', sub: '서울, 1,800병상', photo: I('sq_1.jpg'), key: '외래와 입원 전체\nARR 9억원' }] },
    { name: '도입 중', kind: 'live', cards: [{ name: '종합병원 D', sub: '경기, 700병상', photo: I('sq_2.jpg'), key: '3개 진료과 운영\n전체 확대 협의' }, { name: '종합병원 E', sub: '부산, 600병상', photo: I('sq_3.jpg'), key: '응급의학과 시범\n2분기 확대' }, { name: '병원 그룹 F', sub: '전국 8개 병원', photo: I('sq_4.jpg'), key: '1개 병원 운영\n그룹 계약 검토' }] },
    { name: '계약 협상', kind: 'deal', cards: [{ name: '대학병원 G', sub: '대구, 1,100병상', photo: I('sq_5.jpg'), key: '전 병동 계약\n가격 협상 단계' }, { name: '해외 병원 H', sub: '일본, 400병상', photo: I('sq_6.jpg'), key: '일본어 모델 검증\n하반기 계약 목표' }] },
    { name: '검토 중', kind: 'talk', cards: [{ name: '대학병원 I', sub: '서울', photo: I('sq_7.jpg'), key: '보안 심사 중' }, { name: '종합병원 J', sub: '광주', photo: I('sq_8.jpg'), key: '시범 계약 검토' }, { name: '해외 병원 K', sub: '대만', photo: I('sq_9.jpg'), key: '현지 파트너 협의' }] },
  ], callout: { head: '한 진료과에서 시작해\n병원 전체로 넓힙니다', body: '대학병원 C는 내과 시범 후\n14개월 만에 전 병동 계약' } });
}

{
  const s = D.content({ no: '04', label: 'VALUATION', title: "Post-money 1,300억원은 '27P ARR의 5.0배입니다", sub: "'26E ARR 기준으로는 8.7배. 해외 의료 SaaS 비교 기업보다 낮은 배수에서 들어오는 구조입니다",
    source: '가상의 비교 기업 EV/ARR. 공모 희석과 할인 미반영' });
  D.barsH(s, { label: 'EV/ARR 비교', unit: '배', items: [{ n: '해외 비교 기업 A', v: 14.0 }, { n: '해외 비교 기업 B', v: 11.2 }, { n: '국내 비교 기업 C', v: 9.0 }, { n: "이번 라운드('26E)", v: 8.7, kind: 'ref' }, { n: "이번 라운드('27P)", v: 5.0, kind: 'mine' }] });
  const rx = gx(8), rw = span(4);
  box(s, rx, 2.15, rw, 4.55, C.paper);
  [['Post-money', '약 1,300억원'], ["'26E ARR", '150억원'], ["'27P ARR", '260억원'], ["'26E 기준 배수", '약 8.7배'], ["'27P 기준 배수", '약 5.0배']].forEach(([k, v], i) => {
    const y = 2.4 + i * 0.82;
    if (i) hair(s, rx + 0.25, y - 0.1, rw - 0.5, C.stone);
    T(s, k, { x: rx + 0.25, y, w: rw / 2, h: 0.24, fontSize: 9.5, bold: true, color: C.sub });
    T(s, v, { x: rx + 0.25, y: y + 0.26, w: rw - 0.5, h: 0.4, fontFace: D.FX, fontSize: i === 4 ? 24 : 18, color: i === 4 ? C.red : C.ink });
  });
}

{
  const s = D.content({ no: '04', label: 'USE OF PROCEEDS', title: '신주 150억원의 40%를 대형 병원 영업에 씁니다', sub: '대형 병원 한 곳의 ARR은 의원 수십 곳과 같습니다. 영업 인력이 계약 수를 정합니다', source: '가상의 자금 사용 계획' });
  D.strip(s, { parts: [{ v: 60, col: C.red }, { v: 50, col: C.ink }, { v: 25, col: C.gray6 }, { v: 15, col: C.stone }] });
  D.table(s, { y: 3.3, cols: [{ h: '금액', w: 1.6 }, { h: '용도', w: 3.4 }, { h: '내용', w: W - 2 * M - 5.0 }], em: 0, rows: [
    ['60억원', '대형 병원 영업', '병원 전담 영업과 도입 지원 인력 확충'],
    ['50억원', '제품 개발', '입원 기록, 수술 기록 모델 고도화'],
    ['25억원', '해외 진출', '일본, 대만 현지화와 파트너 구축'],
    ['15억원', '보안과 인증', '의료 데이터 보안 인증 갱신과 감사'],
  ] });
}

D.closing({ line: '의사는 환자를 보고,\n기록은 MediNote가', name: 'MediNote', sub: '진료 기록을 대신 쓰는 병원용 의료 AI 구독 서비스' });

D.save(path.join(__dirname, '예시_디자인덱.pptx'));
