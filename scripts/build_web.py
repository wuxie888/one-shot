#!/usr/bin/env python3
"""从 data/cases.json 和 data/media.json 生成网页：web/index.html（数据内嵌）+ web/img/（本地封面）。

顺序：scripts/build.py → scripts/fetch_media.py → 本脚本。本地封面缓存在 web/_thumbs800/。
"""
import concurrent.futures as cf
import glob, io, json, os, re, urllib.request

import yaml
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
WEB = os.path.join(ROOT, 'web')
CACHE = os.path.join(WEB, '_thumbs800')
IMG = os.path.join(WEB, 'img')
SITE = 'https://one-shot-peach.vercel.app'
TW, TH = 800, 450          # 本地封面尺寸（16:9）
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/140 Safari/537.36'}


def sid(url):
    m = re.search(r'status/(\d+)', url or '')
    return m.group(1) if m else None


def thumb_sources():
    """每条用例的封面来源：本地文件路径或远程 URL，按优先级。"""
    th = {}

    def put(k, v):
        if k and v and k not in th:
            th[k] = v
    for f in glob.glob(os.path.join(SRC, 'athemeroy_awesome-opus-5-5-videos', 'assets', '*thumbnails', '*.webp')):
        put(os.path.basename(f)[:-5], f)
    d = json.load(open(os.path.join(SRC, 'Li-Evan_awesome-opus-5.5-video-prompts', 'site', 'data.json')))
    for e in d['entries']:
        put(sid(e['url']), (e.get('media') or {}).get('thumb'))
    for c in json.load(open(os.path.join(SRC, 'opusvideo_awesome-claude-video', 'cases.json')))['cases']:
        put(str(c['id']), c.get('thumbnail_url'))
    for f in glob.glob(os.path.join(SRC, 'krillinai_awesome-opus-animation', 'categories', '*.md')):
        for m in re.finditer(r'status/(\d+)"><img src="(https://pbs[^"]+)"', open(f).read()):
            put(m.group(1), m.group(2))
    for e in json.load(open(os.path.join(SRC, 'yihui-dev_awesome-opus5-5-videos', 'data', 'videos.json'))):
        put(sid(e['post_url']), e.get('poster_url'))
    lemo = os.path.join(SRC, 'lemomo-ai_lemo-opuscar', 'styles')
    for d in glob.glob(os.path.join(lemo, '*', 'poster.jpg')):
        slug = os.path.basename(os.path.dirname(d))
        put(f'https://github.com/lemomo-ai/lemo-opuscar/blob/main/styles/{slug}/style.md', d)
    return th


def fetch_thumb(key, src):
    out = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9_-]', '_', key)[-80:] + '.jpg')
    if os.path.exists(out):
        return key, out
    try:
        if src.startswith('http'):
            req = urllib.request.Request(src, headers=UA)
            raw = urllib.request.urlopen(req, timeout=25).read()
            im = Image.open(io.BytesIO(raw))
        else:
            im = Image.open(src)
        im = im.convert('RGB')
        # 居中裁成 16:9
        w, h = im.size
        if w / h > TW / TH:
            nw = int(h * TW / TH); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w * TH / TW); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        im.resize((TW, TH), Image.LANCZOS).save(out, quality=88)
        return key, out
    except Exception as e:
        print('  封面失败', key, str(e)[:80])
        return key, None


def main():
    os.makedirs(CACHE, exist_ok=True)
    rows = json.load(open(os.path.join(ROOT, 'data', 'cases.json')))
    mp = os.path.join(ROOT, 'data', 'media.json')
    media = json.load(open(mp))['items'] if os.path.exists(mp) else {}
    # 有 X 封面的直接用 pbs 图床（680 宽）；没有的才用本地来源做 800×450 的图
    need = {}
    srcs = thumb_sources()
    for r in rows:
        if r['curated'] and not (media.get(r['id']) or {}).get('thumb') and r['id'] in srcs:
            need[r['id']] = srcs[r['id']]
    with cf.ThreadPoolExecutor(16) as ex:
        got = dict(ex.map(lambda kv: fetch_thumb(*kv), need.items()))
    os.makedirs(IMG, exist_ok=True)
    local = {}
    for k, path in got.items():
        if path:
            name = re.sub(r'[^A-Za-z0-9_-]', '_', k)[-60:] + '.jpg'
            if not os.path.exists(os.path.join(IMG, name)):
                Image.open(path).save(os.path.join(IMG, name), quality=84)
            local[k] = 'img/' + name
    print('本地封面', len(local), ' X 封面', sum(1 for e in media.values() if e.get('thumb')))

    code = {'视频与动画': 'video', '游戏': 'game', '3D 场景与交互': 'scene', '网页、UI 与 SVG': 'web',
            'Agent 与编程': 'agent', '评测与模型对比': 'eval', '官方、合集与资源': 'resource'}
    out = []
    for r in rows:
        if not r['curated'] and r['before_release']:
            continue
        e = dict(id=r['id'], u=r['url'], t=r['title'], a=r['author'], d=r['date'], k=code[r['top_zh']],
                 s=r['sub'], l=r['likes'], v=r['views'], src=r['sources'])
        if r['title_en'] and r['title_en'] != r['title']:
            e['te'] = r['title_en']
        for k, f in (('ds', 'desc'), ('p', 'prompt'), ('pz', 'prompt_zh'), ('pk', 'prompt_kind'),
                     ('ps', 'prompt_source'), ('g', 'guide')):
            if r.get(f):
                e[k] = r[f]
        for k, f in (('tl', 'tools'), ('dm', 'demo'), ('rp', 'repo')):
            if r.get(f):
                e[k] = r[f]
        if not r['curated']:
            e['c'] = 0
            e['cl'] = r['classifier']
        if r['before_release']:
            e['br'] = 1
        m = media.get(r['id']) or {}
        if m.get('thumb'):
            e['im'] = m['thumb'].split('?')[0] + '?format=jpg&name=small'
        elif r['id'] in local:
            e['im'] = local[r['id']]
        if m.get('vh'):
            e['vs'], e['vh'] = m.get('vs') or m['vh'], m['vh']
            if m.get('dur'):
                e['du'] = round(m['dur'])
        # fxtwitter 的互动数是最新的
        if m.get('likes') is not None:
            e['l'] = max(m['likes'], r['likes'] or 0)
        if m.get('views'):
            e['v'] = max(m['views'], r['views'] or 0)
        out.append({k: v for k, v in e.items() if v not in (None, [], '')} | ({'c': 0} if not r['curated'] else {}))

    # 工具与源码仓库：从 09 号 Markdown 表之外单独取，保持与 build.py 一致
    tools = []
    md = open(os.path.join(ROOT, 'cases', '09-开源工具与仓库.md')).read()
    for m in re.finditer(r'^\| \[([^\]]+)\]\(https://github\.com/[^)]+\)(（已删除或私有）)? \| (\d*) \| ([^|]*) \| (.*?) \| ([^|]*) \|$', md, re.M):
        repo, gone, stars, kind, desc, where = m.groups()
        if gone:
            continue
        tools.append(dict(r=repo, st=int(stars) if stars else None, kd=kind.strip(), ds=desc.replace('\\|', '|').strip(),
                          w=where.strip()))
    meta = dict(updated='2026-09-28', data_until='2026-09-27')
    json.dump(dict(meta=meta, cases=out, tools=tools), open(os.path.join(WEB, 'data.json'), 'w'),
              ensure_ascii=False, separators=(',', ':'))
    print('data.json', len(out), '条用例', len(tools), '个仓库', os.path.getsize(os.path.join(WEB, 'data.json')) // 1024, 'KB')
    # 把数据嵌进页面，打开即完整
    tpl = open(os.path.join(WEB, 'template.html')).read()
    blob = open(os.path.join(WEB, 'data.json')).read().replace('<', '\\u003c')
    cur = [c for c in out if c.get('c') != 0]
    n_v = sum(1 for c in cur if c.get('vh'))
    n_p = sum(1 for c in cur if c.get('p') and c.get('pk') in ('原文', '部分原文'))
    desc = f'一句提示词 一镜到底 收录 {len(cur):,} 部 Claude Opus 5.5 作品 {n_v} 部可直接播放 {n_p} 份提示词原文一键复制'
    html = tpl.replace('__SITE__', SITE).replace('__DESC__', desc).replace('/*DATA*/', blob)
    open(os.path.join(WEB, 'index.html'), 'w').write(html)
    json.dump(dict(cases=len(cur), videos=n_v, prompts=n_p, tools=len(tools), desc=desc),
              open(os.path.join(WEB, '_stats.json'), 'w'), ensure_ascii=False)
    print(desc)
    print('index.html', os.path.getsize(os.path.join(WEB, 'index.html')) // 1024, 'KB')


if __name__ == '__main__':
    main()
