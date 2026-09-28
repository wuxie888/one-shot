#!/usr/bin/env python3
"""生成品牌素材：favicon（svg/png/ico）、apple-touch-icon、分享预览图 og.jpg。

用本机 Chrome（Playwright）渲染，og 图会联网加载字体和封面。先跑 build_web.py。
"""
import asyncio, base64, io, json, os, re

from PIL import Image
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, 'web')

LOGO = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6e0a0"/><stop offset=".55" stop-color="#d4b064"/><stop offset="1" stop-color="#9a7534"/></linearGradient></defs>
<rect width="64" height="64" rx="14" fill="#0d0a08"/>
<path d="M11 23V11h12M41 11h12v12M53 41v12H41M23 53H11V41" fill="none" stroke="url(#g)" stroke-width="4.5"/>
<rect x="17" y="28.5" width="30" height="7" rx="3.5" fill="url(#g)"/>
<circle cx="21" cy="20.5" r="3.4" fill="#ff5b35"/>
</svg>
'''

# 模型版本存疑的作品（原帖只写 Claude，没写 Opus 5.5），不放进宣传图
DOUBTFUL = {'2103212539895017864'}

FONTS = ('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800&family=JetBrains+Mono:wght@500;600'
         '&family=Noto+Serif+SC:wght@600;900&display=swap')


def og_html(stats, thumbs):
    cells = ''.join(
        f'<div class="t"><img src="{t["im"].replace("name=small", "name=medium")}"><span class="c">{t["chip"]}</span>'
        f'<span class="d">{t["dur"]}</span></div>' for t in thumbs)
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">
<link rel="stylesheet" href="{FONTS}"><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;overflow:hidden;background:
 radial-gradient(ellipse 55% 75% at 30% 0%,rgba(246,224,160,.16),transparent 70%),
 radial-gradient(ellipse 70% 45% at 50% 115%,rgba(163,32,42,.55),transparent 70%),#0d0a08;color:#f3ead8;position:relative;font-family:"Noto Serif SC",serif}}
.val{{position:absolute;inset:0 0 auto 0;height:26px;background:linear-gradient(#2a0406,#6e0f14 60%,#a3202a);
 -webkit-mask:radial-gradient(circle 18px at 18px -3px,#000 98%,transparent) 0 0/36px 26px repeat-x,linear-gradient(#000,#000) 0 0/100% 9px no-repeat}}
.cur{{position:absolute;top:0;bottom:0;width:74px;background:repeating-linear-gradient(90deg,#2a0406 0,#6e0f14 9px,#a3202a 16px,#6e0f14 24px,#2a0406 33px);box-shadow:inset 0 -60px 60px rgba(0,0,0,.5)}}
.l{{left:0;clip-path:polygon(0 0,100% 0,90% 40%,60% 66%,54% 100%,0 100%)}}
.r{{right:0;clip-path:polygon(0 0,100% 0,100% 100%,46% 100%,40% 66%,10% 40%)}}
.left{{position:absolute;left:112px;top:92px;width:520px}}
.eb{{font:600 15px/1 Cinzel,serif;letter-spacing:.3em;color:#d4b064}}
.eb i{{color:#a3202a;font-style:normal;padding:0 .4em}}
h1{{margin-top:22px;font:800 118px/.9 Cinzel,serif;letter-spacing:.03em;background:linear-gradient(180deg,#f6e0a0 8%,#d4b064 55%,#7d5f28);-webkit-background-clip:text;color:transparent}}
h2{{margin-top:16px;font:900 64px/1 "Noto Serif SC",serif;letter-spacing:.2em;color:#f3ead8}}
.sl{{margin-top:26px;font:600 27px/1.3 "Noto Serif SC",serif;letter-spacing:.28em;color:#f3ead8}}
.rule{{margin-top:24px;width:420px;height:1px;background:linear-gradient(90deg,#d4b064,transparent)}}
.grid{{position:absolute;right:104px;top:84px;display:grid;grid-template-columns:repeat(2,232px);gap:14px;transform:rotate(-3deg)}}
.t{{position:relative;height:131px;border:2px solid #7d5f28;background:#1a130f;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.55)}}
.t img{{width:100%;height:100%;object-fit:cover;display:block}}
.c{{position:absolute;left:7px;top:7px;background:#D8742B;color:#2A1C13;font:700 12px/1 sans-serif;padding:4px 6px;border:1.5px solid #2A1C13}}
.d{{position:absolute;left:7px;bottom:7px;background:rgba(13,10,8,.85);color:#f3ead8;font:600 12px/1 "JetBrains Mono",monospace;padding:4px 6px}}
.d::before{{content:"";display:inline-block;margin-right:5px;border-left:7px solid #ff5b35;border-block:4.5px solid transparent;vertical-align:-1px}}
.stats{{position:absolute;left:112px;right:112px;bottom:40px;display:flex;justify-content:space-between;align-items:baseline;border-top:1px solid #3a2f26;padding-top:16px}}
.stats b{{font:600 26px/1 Cinzel,serif;color:#f6e0a0;margin-right:6px}}
.stats span{{font:600 16px/1 "Noto Serif SC",serif;color:#b9a98c;letter-spacing:.08em;margin-right:28px}}
.url{{font:500 15px/1 "JetBrains Mono",monospace;color:#d4b064;letter-spacing:.04em}}
</style></head><body>
<div class="val"></div><div class="cur l"></div><div class="cur r"></div>
<div class="left"><p class="eb">CLAUDE OPUS 5.5<i>◆</i>用例大全</p><h1>ONE SHOT</h1><h2>一镜</h2>
<div class="rule"></div><p class="sl">一句提示词 一镜到底</p></div>
<div class="grid">{cells}</div>
<div class="stats"><div><b>{stats["cases"]:,}</b><span>部作品</span><b>{stats["videos"]}</b><span>部可直接播放</span><b>{stats["prompts"]}</b><span>份提示词原文</span></div>
<div class="url">one-shot-peach.vercel.app</div></div>
</body></html>'''


def lively(url):
    """封面画面是否够丰富：排除纯白、纯黑这种第一帧还没开始的截图。"""
    import urllib.request
    from PIL import ImageStat
    try:
        req = urllib.request.Request(url.replace('name=small', 'name=360x360'), headers={'User-Agent': 'Mozilla/5.0'})
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read())).convert('L')
        st = ImageStat.Stat(im)
        return st.stddev[0] > 38 and 25 < st.mean[0] < 225
    except Exception:
        return False


async def main():
    open(os.path.join(WEB, 'favicon.svg'), 'w').write(LOGO)
    stats = json.load(open(os.path.join(WEB, '_stats.json')))
    data = json.load(open(os.path.join(WEB, 'data.json')))
    sub = {'launch': '产品发布', 'motion': '动效', 'explainer': '知识讲解', 'story': '叙事动画', 'music': '音乐视频',
           'history': '历史纪录', 'remix': '素材改编', 'self': 'AI 自述', 'other': '视频'}
    top = {'game': '游戏', 'scene': '3D 场景', 'web': '网页', 'agent': 'Agent', 'eval': '评测', 'resource': '资源'}
    pool = sorted((c for c in data['cases'] if c.get('c') != 0 and c.get('vh') and str(c.get('im', '')).startswith('https')),
                  key=lambda c: -(c.get('l') or 0))
    thumbs, seen = [], set()
    rival = re.compile(r'astra|gpt|gemini|对比|vs\b|comparison', re.I)
    pool = [c for c in pool if c['id'] not in DOUBTFUL and not rival.search(' '.join(str(c.get(k, '')) for k in ('t', 'te', 'ds')))]
    for c in pool:  # 前排作品里尽量覆盖不同分类
        chip = sub.get(c.get('s')) if c['k'] == 'video' else top.get(c['k'])
        if chip in seen and len(pool) > 20:
            continue
        if not lively(c['im']):
            continue
        seen.add(chip)
        d = c.get('du') or 0
        thumbs.append(dict(im=c['im'], chip=chip, dur=f'{d // 60}:{d % 60:02d}'))
        if len(thumbs) == 6:
            break

    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel='chrome')
        # 图标：透明底用于 favicon，实底用于 apple-touch-icon
        p = await b.new_page(viewport={'width': 512, 'height': 512})
        b64 = base64.b64encode(LOGO.encode()).decode()
        await p.set_content(f'<html><body style="margin:0;background:transparent">'
                            f'<img id="lg" src="data:image/svg+xml;base64,{b64}" '
                            f'style="width:512px;height:512px;display:block"></body></html>')
        await p.wait_for_function('document.getElementById("lg").complete')
        raw = await p.screenshot(omit_background=True)
        big = Image.open(io.BytesIO(raw)).convert('RGBA')
        for size, name in ((32, 'favicon-32.png'), (192, 'icon-192.png'), (512, 'icon-512.png')):
            big.resize((size, size), Image.LANCZOS).save(os.path.join(WEB, name))
        flat = Image.new('RGB', big.size, (13, 10, 8)); flat.paste(big, mask=big)
        flat.resize((180, 180), Image.LANCZOS).save(os.path.join(WEB, 'apple-touch-icon.png'))
        big.save(os.path.join(WEB, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])
        # 分享预览图
        og = await b.new_page(viewport={'width': 1200, 'height': 630}, device_scale_factor=1)
        await og.set_content(og_html(stats, thumbs), wait_until='networkidle')
        await og.evaluate('document.fonts.ready')
        await og.wait_for_timeout(1200)
        Image.open(io.BytesIO(await og.screenshot())).convert('RGB').save(
            os.path.join(WEB, 'og.jpg'), quality=90, optimize=True)
        await b.close()
    print('品牌素材已生成：favicon.svg/.ico/-32.png、apple-touch-icon.png、icon-192/512.png、og.jpg')


if __name__ == '__main__':
    asyncio.run(main())
