# -*- coding: utf-8 -*-
"""pptxgenjs로 만든 덱을 마무리한다.
1) 모든 문단에 어절 단위 줄바꿈(eaLnBrk="0")을 켠다. PowerPoint의 '한글 단어 잘림 허용'을 끈 것과 같다.
2) 슬라이드 전환을 넣는다. 사용: python3 finalize.py 덱.pptx "2:morph,3:fade,4:fade"
"""
import re, shutil, sys, zipfile
MORPH = ('<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
         '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">'
         '<p:transition spd="slow" p14:dur="1600" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main">'
         '<p159:morph option="byObject"/></p:transition></mc:Choice><mc:Fallback><p:transition spd="slow"><p:fade/></p:transition>'
         '</mc:Fallback></mc:AlternateContent>')
FADE = '<p:transition spd="slow"><p:fade/></p:transition>'


def word_wrap(x):
    x = re.sub(r"<a:pPr(?![^>]*eaLnBrk)", '<a:pPr eaLnBrk="0"', x)          # pPr 있는 문단
    return re.sub(r"<a:p>(?!<a:pPr)", '<a:p><a:pPr eaLnBrk="0"/>', x)       # pPr 없는 문단


def main(src, plan_s=""):
    plan = {int(k): (MORPH if v == "morph" else FADE) for k, v in (p.split(":") for p in plan_s.split(",") if p)}
    tmp = src + ".tmp"
    zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for it in zin.infolist():
        data = zin.read(it.filename)
        m = re.match(r"ppt/slides/slide(\d+)\.xml$", it.filename)
        if m:
            x = word_wrap(data.decode("utf-8"))
            t = plan.get(int(m.group(1)))
            if t and "<p:transition" not in x:
                x = x.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + t, 1) if "</p:clrMapOvr>" in x else x.replace("</p:sld>", t + "</p:sld>")
            data = x.encode("utf-8")
        zout.writestr(it, data)
    zout.close(); shutil.move(tmp, src); print("마무리:", src)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
