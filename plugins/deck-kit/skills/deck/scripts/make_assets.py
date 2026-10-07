# -*- coding: utf-8 -*-
"""덱에 쓰는 그림 자산을 만든다(Pillow만 사용).

python3 make_assets.py glow FF4438 [출력.png]  강조색 빛 번짐(기본 assets/glow.png). 핵심 장표 배경. 강조색을 바꾸면 덱마다 만들어 opts.glow로 넘긴다
python3 make_assets.py sample 출력폴더         예시 덱용 추상 그림(가로 16:9 1장, 3:2 3장, 정사각 9장)
python3 make_assets.py darken 사진.jpg 출력.jpg 전면 사진 장용: 16:9로 자르고 왼쪽을 어둡게(글자 자리)
"""
import os, sys, random
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def glow(color="FF4438", out=None):
    r, g, b = hex2rgb(color)
    a = Image.radial_gradient("L").resize((1200, 1200)).point(lambda v: int(max(0, 1 - v / 180) ** 2.2 * 140))
    im = Image.new("RGBA", (1200, 1200), (r, g, b, 0)); im.putalpha(a)
    out = out or os.path.join(ASSETS, "glow.png"); im.save(out); print("저장:", out)


def darken(src, out):
    im = Image.open(src).convert("RGB"); W, H = im.size; h = int(W * 9 / 16)
    if h <= H:
        top = int((H - h) * 0.5); im = im.crop((0, top, W, top + h))
    else:
        w = int(H * 16 / 9); left = int((W - w) / 2); im = im.crop((left, 0, left + w, H)); W, h = im.size
    lin = Image.linear_gradient("L").rotate(90, expand=True).resize((W, h)).point(lambda v: 255 - v)
    mask = lin.point(lambda v: int(min(242, max(38, (v / 255) * 330 - 70))))
    bot = Image.linear_gradient("L").resize((W, h)).point(lambda v: int(max(0, (v - 170) * 2.2)))
    mask = ImageChops.lighter(mask, bot)
    Image.composite(Image.new("RGB", (W, h), (10, 10, 10)), im, mask).save(out, quality=90); print("저장:", out)


def abstract(w, h, seed, base):
    rnd = random.Random(seed)
    im = Image.new("RGB", (w, h), base); d = ImageDraw.Draw(im)
    for _ in range(14):   # 겹친 빛 덩어리로 공간감
        cx, cy, rr = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(min(w, h) // 6, min(w, h) // 2)
        col = tuple(min(255, max(0, c + rnd.randint(-60, 90))) for c in base)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(radius=min(w, h) // 12))
    d = ImageDraw.Draw(im)
    for i in range(0, w, max(8, w // 40)):   # 바닥 격자로 전시 공간 느낌
        d.line((i, int(h * 0.72), w / 2 + (i - w / 2) * 2.2, h), fill=tuple(min(255, c + 25) for c in base), width=1)
    return im


def sample(outdir):
    os.makedirs(outdir, exist_ok=True)
    palette = [(28, 30, 48), (40, 24, 34), (22, 40, 44), (46, 38, 26), (30, 30, 30), (52, 26, 26), (24, 34, 52), (36, 44, 30), (44, 30, 50)]
    abstract(1920, 1080, 1, (26, 26, 34)).save(os.path.join(outdir, "hero.jpg"), quality=88)
    for i in range(3):
        abstract(1500, 1000, 10 + i, palette[i]).save(os.path.join(outdir, f"wide_{i + 1}.jpg"), quality=88)
    for i in range(9):
        abstract(600, 600, 20 + i, palette[i]).save(os.path.join(outdir, f"sq_{i + 1}.jpg"), quality=88)
    print("저장:", outdir)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "glow": glow(sys.argv[2] if len(sys.argv) > 2 else "FF4438", sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "sample": sample(sys.argv[2])
    elif cmd == "darken": darken(sys.argv[2], sys.argv[3])
    else: print(__doc__)
