#!/usr/bin/env python3
"""合并 12 个 Opus 5.5 用例仓库，按 X 帖子 ID 去重，输出总表。

用法：python3 scripts/build.py          （源仓库需已在 sources/ 下）
      python3 scripts/build.py --fetch  （先克隆/更新源仓库）
"""
import csv, datetime, glob, json, os, re, subprocess, sys
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')

REPOS = {
    'athemeroy': 'athemeroy/awesome-opus-5-5-videos',
    'opusvideo': 'opusvideo/awesome-claude-video',
    'zhuyansen': 'zhuyansen/awesome-claude-video-skills',
    'lemo': 'lemomo-ai/lemo-opuscar',
    'yihui': 'yihui-dev/awesome-opus5-5-videos',
    'lievan': 'Li-Evan/awesome-opus-5.5-video-prompts',
    'frontier': 'theolundqvist/frontier-games',
    'coolbat': 'coolbat/awesome-opus-5.5-usecase',
    'krillin': 'krillinai/awesome-opus-animation',
    'openvg': 'OpenVGLab/awesome-opus5.5-frontend-showcases',
    'joeseesun': 'joeseesun/opus-video-prompts',
    'riba': 'riba2534/claude-opus-5-5-demo',
}


def repo_dir(key):
    return os.path.join(SRC, REPOS[key].replace('/', '_'))


def fetch():
    for key, full in REPOS.items():
        d = repo_dir(key)
        if os.path.isdir(os.path.join(d, '.git')):
            subprocess.run(['git', '-C', d, 'pull', '-q', '--ff-only'])
        else:
            subprocess.run(['git', 'clone', '-q', '--depth', '1', f'https://github.com/{full}.git', d])


# ---------- 分类 ----------
TOPS = {
    'video': '视频与动画',
    'game': '游戏',
    'scene': '3D 场景与交互',
    'web': '网页、UI 与 SVG',
    'agent': 'Agent 与编程',
    'eval': '评测与模型对比',
    'resource': '官方、合集与资源',
}
TOP_FILES = {
    'video': '01-视频与动画.md', 'game': '02-游戏.md', 'scene': '03-3D场景与交互.md',
    'web': '04-网页UI与SVG.md', 'agent': '05-Agent与编程.md', 'eval': '06-评测与模型对比.md',
    'resource': '07-官方合集与资源.md',
}
VIDEO_SUBS = {
    'launch': '产品发布与广告', 'motion': '动效与作品集', 'explainer': '知识讲解',
    'story': '叙事与角色动画', 'music': '音乐视频', 'history': '历史与纪录',
    'remix': '素材改编与剪辑', 'self': 'AI 自我叙事', 'other': '其他',
}
TIE_ORDER = ['game', 'scene', 'web', 'agent', 'eval', 'resource', 'video']

SOURCE_NAMES = {
    'athemeroy': 'athemeroy（人工深读）', 'athemeroy_corpus': 'athemeroy（分类器语料）',
    'opusvideo': 'opusvideo', 'zhuyansen': 'zhuyansen', 'lemo': 'lemo-opuscar',
    'yihui': 'yihui-dev', 'lievan': 'Li-Evan', 'frontier': 'frontier-games',
    'coolbat': 'coolbat', 'krillin': 'krillinai', 'openvg': 'OpenVGLab', 'joeseesun': 'joeseesun',
}

# 提示词来源优先级（越小越优先）
PROMPT_RANK = {'lievan': 1, 'yihui': 2, 'joeseesun': 3, 'openvg': 4, 'opusvideo': 5, 'krillin': 6, 'athemeroy': 7}

OPUS55_RELEASE = datetime.date(2026, 9, 22)


def snowflake_date(sid):
    try:
        ms = (int(sid) >> 22) + 1288834974657
        return datetime.datetime.utcfromtimestamp(ms / 1000).date()
    except Exception:
        return None


STATUS_RE = re.compile(r'https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d{15,20})')


def key_for(url):
    """X 帖子用状态 ID 作键，其余用规范化 URL。"""
    m = STATUS_RE.search(url or '')
    if m:
        return m.group(2), f'https://x.com/{m.group(1)}/status/{m.group(2)}', m.group(1)
    u = (url or '').strip().rstrip('/')
    u = re.sub(r'^http://', 'https://', u)
    u = re.sub(r'\?.*$', '', u) if 'github.com' in u else u
    return u.lower(), u, None


class Store:
    def __init__(self):
        self.items = {}

    def add(self, src, url, *, top=None, sub=None, weight=1.0, title_zh=None, title_en=None,
            desc_zh=None, desc_en=None, author=None, prompt=None, prompt_zh=None, prompt_kind=None,
            tools=None, likes=None, views=None, demo=None, repo=None, date=None, note=None,
            curated=True, extra=None):
        if not url:
            return
        k, canon, handle = key_for(url)
        it = self.items.get(k)
        if it is None:
            it = self.items[k] = dict(key=k, url=canon, author=None, sources=[], votes=defaultdict(float),
                                      subvotes=defaultdict(float), titles_zh={}, titles_en={}, descs_zh={},
                                      descs_en={}, prompts=[], tools=set(), likes=None, views=None,
                                      demo=set(), repo=set(), date=None, notes=[], curated=False, extra={})
        if src not in it['sources']:
            it['sources'].append(src)
        it['curated'] |= curated
        it['author'] = it['author'] or (author or handle)
        if handle and not it['author']:
            it['author'] = handle
        if top:
            it['votes'][top] += weight
        if sub:
            it['subvotes'][sub] += weight
        for field, v in (('titles_zh', title_zh), ('titles_en', title_en), ('descs_zh', desc_zh), ('descs_en', desc_en)):
            if v and v.strip():
                it[field].setdefault(src, v.strip())
        if prompt and prompt.strip():
            it['prompts'].append(dict(src=src, text=prompt.strip(), zh=(prompt_zh or '').strip() or None,
                                      kind=prompt_kind or '原文'))
        if tools:
            it['tools'].update(t for t in tools if t)
        for f, v in (('likes', likes), ('views', views)):
            if isinstance(v, (int, float)) and v >= 0:
                it[f] = max(it[f] or 0, int(v))
        if demo:
            it['demo'].add(demo)
        if repo:
            it['repo'].add(repo)
        if date:
            it['date'] = it['date'] or str(date)[:10]
        if note:
            it['notes'].append(note)
        if extra:
            it['extra'].update(extra)


S = Store()


def num(v):
    try:
        return int(float(v))
    except Exception:
        return None


# ---------- 各仓库解析 ----------
def load_lievan():
    d = json.load(open(os.path.join(repo_dir('lievan'), 'site', 'data.json')))
    cmap = {'showreel': ('video', 'motion'), 'launch': ('video', 'launch'), 'story': ('video', 'story'),
            'explainer': ('video', 'explainer'), 'history': ('video', 'history'), 'music': ('video', 'music'),
            'remix': ('video', 'remix'), 'self': ('video', 'self'), 'worlds': ('scene', None)}
    for e in d['entries']:
        top, sub = cmap.get(e.get('category'), ('video', 'other'))
        m = e.get('metrics') or {}
        S.add('lievan', e['url'], top=top, sub=sub, title_zh=e.get('title_zh'), title_en=e.get('title'),
              desc_zh=e.get('description_zh'), desc_en=e.get('description'), author=e.get('author'),
              prompt=e.get('prompt'), prompt_zh=e.get('prompt_zh'), prompt_kind='原文',
              tools=e.get('tools'), likes=m.get('likes'), views=m.get('views'), date=e.get('date'))


def load_yihui():
    d = json.load(open(os.path.join(repo_dir('yihui'), 'data', 'videos.json')))
    cmap = {'motion': ('video', 'motion'), 'explainer': ('video', 'explainer'), '3d': ('scene', None),
            'interactive': ('scene', None)}
    for e in d:
        top, sub = cmap.get(e.get('category'), ('video', 'other'))
        pt = re.sub(r'\s+', ' ', e.get('prompt') or '').strip()
        auto = (pt[:60] + ('…' if len(pt) > 60 else '')) if pt else None
        S.add('yihui', e['post_url'], top=top, sub=sub, author=e.get('author'), prompt=e.get('prompt'),
              extra={'auto_title': auto},
              prompt_kind='部分原文' if e.get('prompt_partial') else '原文', tools=e.get('tech_tags'),
              weight=0.8)


def load_opusvideo():
    d = json.load(open(os.path.join(repo_dir('opusvideo'), 'cases.json')))
    cmap = {'product': ('video', 'launch'), 'motion': ('video', 'motion'), 'education': ('video', 'explainer'),
            'stories': ('video', 'story'), 'art': ('video', 'other'), 'production': ('video', 'other'),
            'comparisons': ('eval', None)}
    # 实现指南按中文锚点 case-<ID>-zh 解析
    guides = {}
    txt = open(os.path.join(repo_dir('opusvideo'), 'IMPLEMENTATION_GUIDES.md')).read()
    for m in re.finditer(r'<a id="case-(\d+)-zh"></a>\s*### [^\n]+\n(.*?)(?=\n<a id=|\Z)', txt, re.S):
        guides[m.group(1)] = m.group(2).strip()
    for c in d['cases']:
        top, sub = cmap.get(c['category'], ('video', 'other'))
        t = c.get('title') or {}
        ds = c.get('description') or {}
        g = guides.get(str(c['id']))
        S.add('opusvideo', c['original_post_url'], top=top, sub=sub, title_zh=t.get('zh-CN'), title_en=t.get('en'),
              desc_zh=ds.get('zh-CN'), desc_en=ds.get('en'), author=(c.get('creator') or {}).get('handle'),
              tools=c.get('tools_reported'), views=c.get('views'), repo=c.get('source_code_url'),
              extra={'guide': g} if g else None)


def load_frontier():
    d = yaml.safe_load(open(os.path.join(repo_dir('frontier'), 'data', 'games.yaml')))
    for e in d:
        if e.get('model') != 'claude-opus-5.5':
            continue  # 只收 Opus 5.5，GPT-6 Astra 的跳过
        desc = e.get('description') or ''
        extra = ' · '.join(x for x in [e.get('genre'), e.get('engine'), e.get('build')] if x)
        genre = (e.get('genre') or '').lower()
        if re.search(r'music video|musical', genre):
            top, sub = 'video', 'music'
        elif re.search(r'explainer|essay|documentary', genre):
            top, sub = 'video', 'explainer'
        elif re.search(r'short|film|animation|animated|poem|claymation|demoscene|cinematic|time-lapse|diorama', genre):
            top, sub = ('scene', None) if re.search(r'cinematic|time-lapse|diorama|demoscene', genre) else ('video', 'story')
        else:
            top, sub = 'game', None
        S.add('frontier', e.get('post_url') or e.get('repo_url') or e.get('play_url'), top=top, sub=sub, weight=1.5, title_en=e.get('title'),
              desc_en=f'{desc}（{extra}）' if extra else desc, author=e.get('creator_handle'),
              tools=[e.get('engine')], likes=e.get('post_likes'), demo=e.get('play_url'),
              repo=e.get('repo_url'), date=e.get('date'))


def load_coolbat():
    d = json.load(open(os.path.join(repo_dir('coolbat'), 'data', 'usecases.json')))
    cmap = {'videos': ('video', 'other'), 'games-3d': ('game', None), 'creative': ('scene', None),
            'agent': ('agent', None), 'benchmarks': ('eval', None), 'showcase': ('web', None),
            'collections': ('resource', None), 'official': ('resource', None)}
    for e in d:
        top, sub = cmap.get(e.get('category'), ('video', 'other'))
        S.add('coolbat', e['url'], top=top, sub=sub, weight=0.7, title_en=e.get('title'), desc_en=e.get('notes'),
              demo=e.get('demo_url'))


def parse_krillin_file(path):
    txt = open(path).read()
    for block in re.split(r'\n(?=### )', txt):
        m = re.match(r'### (.+)', block)
        if not m:
            continue
        fields = dict(re.findall(r'- \*\*(.+?)\*\*：(.+)', block))
        yield m.group(1).strip(), fields


def load_krillin():
    cmap = {'explainers': ('video', 'explainer'), 'narrative': ('video', 'story'), '3d-scenes': ('scene', None),
            'games': ('game', None), 'code-animation': ('video', 'motion'), 'hand-drawn-mv': ('video', 'music'),
            'motion-design': ('video', 'motion')}
    for path in glob.glob(os.path.join(repo_dir('krillin'), 'categories', '*.zh-CN.md')):
        slug = os.path.basename(path).replace('.zh-CN.md', '')
        top, sub = cmap.get(slug, ('video', 'other'))
        for title, f in parse_krillin_file(path):
            src_line = f.get('原帖') or f.get('样片') or ''
            m = STATUS_RE.search(src_line) or re.search(r'\((https?://[^)]+)\)', src_line)
            if not m:
                continue
            url = m.group(0) if m.re is STATUS_RE else m.group(1)
            p = f.get('提示词', '')
            has_prompt = p and not re.search(r'未公开|未提供|尚未核实到原文', p)
            demo = re.findall(r'\[在线体验\]\((https?://[^)]+)\)', f.get('样片', ''))
            desc = f.get('内容', '')
            if f.get('实现'):
                desc = f'{desc} 实现：{f["实现"]}'
            S.add('krillin', url, top=top, sub=sub, title_zh=title, desc_zh=desc,
                  prompt=re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', p) if has_prompt else None,
                  prompt_kind='摘录', demo=demo[0] if demo else None)


def load_openvg():
    path = os.path.join(repo_dir('openvg'), 'README.md')
    txt = open(path).read()
    smap = {'浏览器游戏': ('game', None), '鹈鹕骑自行车': ('eval', None), '更多骑行系列': ('eval', None),
            'SVG 动画与插画': ('web', None), 'Lottie 动画': ('web', None), '3D · Three.js · WebGL': ('scene', None),
            '代码逐帧动画与视频': ('video', 'motion'), '网页、UI 与应用': ('web', None), '评测与工具': ('eval', None)}
    base = 'https://github.com/OpenVGLab/awesome-opus5.5-frontend-showcases/blob/main/'
    for sec in re.split(r'\n(?=## )', txt):
        m = re.match(r'## \S+ (.+)', sec)
        if not m or m.group(1).strip() not in smap:
            continue
        top, sub = smap[m.group(1).strip()]
        # 本仓库原创：#### Case N: [标题](在线地址)
        for case in re.split(r'\n(?=#### Case )', sec):
            cm = re.match(r'#### Case \d+: \[(.+?)\]\((.+?)\)', case)
            if not cm:
                continue
            title, demo = cm.groups()
            fm = re.search(r'\*\*来源：\*\*.*?\[`([^`]+)`\]', case)
            url = base + fm.group(1) if fm else demo
            dm = re.search(r'\*\*发布：\*\*\s*(\S+)', case)
            paras = [p.strip() for p in case.split('\n\n') if p.strip() and not p.strip().startswith(('#', '**', '<', '```'))]
            pm = re.search(r'<summary>Prompt[^<]*</summary>\s*```\w*\n(.*?)```', case, re.S)
            S.add('openvg', url, top=top, sub=sub, title_zh=title, desc_zh=paras[0] if paras else None,
                  author='OpenVGLab', prompt=pm.group(1) if pm else None, demo=demo,
                  date=dm.group(1) if dm else None)
        # 社区作品表格
        for row in re.finditer(r'^\| \[(.+?)\]\((https?://[^)]+)\) \| (.+?) \| (\d{4}-\d\d-\d\d) \| (.+?) \|$', sec, re.M):
            title, url, _, date, desc = row.groups()
            S.add('openvg', url, top=top, sub=sub, title_zh=title, desc_zh=re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', desc),
                  date=date)


def load_joeseesun():
    d = repo_dir('joeseesun')
    cmap = {'科普讲解': ('video', 'explainer'), '产品广告': ('video', 'launch'), '叙事动画': ('video', 'story'),
            '艺术/3D': ('scene', None), '音乐 MV': ('video', 'music'), 'B 站合集': ('video', 'other'),
            '动态图形': ('video', 'motion'), '纪录/剪辑': ('video', 'remix')}
    for e in json.load(open(os.path.join(d, 'cases.json'))):
        top, sub = cmap.get(e['category'], ('video', 'other'))
        desc = '；'.join(x for x in [e.get('how'), e.get('cost')] if x)
        S.add('joeseesun', e['url'], top=top, sub=sub, weight=0.8, title_zh=e.get('title'), desc_zh=desc or None)
    for p in glob.glob(os.path.join(d, 'prompts', '*.md')):
        t = open(p).read()
        um = STATUS_RE.search(t)
        pm = re.search(r'## 提示词[^\n]*\n+```\w*\n(.*?)```', t, re.S)
        if um and pm:
            S.add('joeseesun', um.group(0), prompt=pm.group(1))


def load_athemeroy():
    d = repo_dir('athemeroy')
    pmap = {'procedural_2d': ('video', 'motion', 0.5), 'existing_source_transformation': ('video', 'remix', 1),
            'educational_explainer': ('video', 'explainer', 1), '3d_or_realtime_graphics': ('scene', None, 1),
            'app_or_game_capture': ('game', None, 1), 'mixed_or_not_established': ('video', 'other', 0.3),
            'external_video_model': ('video', 'other', 0.5)}
    eng = {}
    for r in csv.DictReader(open(os.path.join(d, 'data', 'case-engagement-refresh-2026-09-27.csv'))):
        eng[r['post_id']] = (num(r['likes']), num(r['views']))
    for r in csv.DictReader(open(os.path.join(d, 'data', 'cases.csv'))):
        top, sub, w = pmap.get(r['primary_path'], ('video', 'other', 0.3))
        sid = key_for(r['source_url'])[0]
        lk, vw = eng.get(sid, (None, None))
        label = re.sub(r'^@\S+\s*', '', r['label'])
        S.add('athemeroy', r['source_url'], top=top, sub=sub, weight=w, title_en=label,
              desc_en=re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', r['creator_disclosure']), likes=lk, views=vw,
              extra={'path': r['primary_path']})
    # 88 例提示词矩阵：提示词形状摘要
    pm = open(os.path.join(d, 'docs', 'prompt-matrix.zh-CN.md')).read()
    for row in re.finditer(r'^\| \[@?[^\]]+?[：:](.+?)\]\((https?://x\.com/[^)]+)\) \| (.+?) \| (.+?) \|', pm, re.M):
        title, url, shape, inputs = row.groups()
        S.add('athemeroy', url, title_zh=title, prompt=f'{shape}\n\n输入与工具：{inputs}'.replace('**', ''),
              prompt_kind='摘要')
    # 截点后新增 7 条
    nc = open(os.path.join(d, 'docs', 'new-cases-2026-09-27.zh-CN.md')).read()
    for block in re.split(r'\n(?=### )', nc):
        m = re.match(r'### (.+?) — @', block)
        um = STATUS_RE.search(block)
        if m and um:
            dm = re.search(r'\*\*作者披露：\*\*(.+)', block)
            S.add('athemeroy', um.group(0), top='video', sub='other', weight=0.3, title_zh=m.group(1),
                  desc_zh=re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', dm.group(1)).strip() if dm else None)
    # 1,401 个分类器语料：只作分类票和“待核实”候选
    dmap = {'product_ad': ('video', 'launch'), 'game_interactive': ('game', None),
            'education_science': ('video', 'explainer'), 'story_short': ('video', 'story'),
            'music_video': ('video', 'music'), 'history_culture': ('video', 'history'),
            'ai_self_meta': ('video', 'self'), 'humor_meme': ('video', 'other'), 'art_abstract': ('video', 'motion'),
            'data_viz': ('video', 'explainer'), 'other': ('video', 'other')}
    for r in csv.DictReader(open(os.path.join(d, 'data', 'domain-style.csv'))):
        if r['opus_made'] not in ('yes', 'likely'):
            continue
        top, sub = dmap.get(r['domain'], ('video', 'other'))
        if top == 'game' and r['style'] == 'motion_graphics_ui':
            top, sub = 'video', 'launch'
        S.add('athemeroy_corpus', r['post_url'], top=top, sub=sub, weight=0.4, title_en=r['topic_en'],
              curated=False, extra={'classifier': r['opus_made'], 'style': r['style']})


def load_lemo():
    d = repo_dir('lemo')
    base = 'https://github.com/lemomo-ai/lemo-opuscar/blob/main/styles/'
    for c in json.load(open(os.path.join(d, 'styleboard', 'catalog.json'))):
        url = f'{base}{c["slug"]}/STYLE.md'
        S.add('lemo', url, top='video', sub='story', author='lemomo-ai',
              title_zh=f'{c["cn"]}：{c["film"]}', title_en=f'{c["en"]}: {c["film"]}',
              desc_zh=f'{c.get("line_cn", "")}（{c.get("cat", "")}，{c.get("dur", "")} 秒，风格提示词见 STYLE.md）',
              desc_en=c.get('line'), prompt_kind=None, demo='https://lemomo-ai.github.io/lemo-opuscar/',
              tools=['Canvas', 'WebGL'])


# ---------- 工具与 Skill 仓库 ----------
def load_tools():
    tools = {}

    def add(full, src, desc=None, stars=None, kind=None, opus=False):
        full = full.strip().strip('/')
        if full.count('/') != 1:
            return
        t = tools.setdefault(full.lower(), dict(repo=full, desc=None, stars=None, kind=None, sources=[], opus=False))
        t['desc'] = t['desc'] or desc
        if isinstance(stars, int):
            t['stars'] = max(t['stars'] or 0, stars)
        t['kind'] = t['kind'] or kind
        t['opus'] |= opus
        if src not in t['sources']:
            t['sources'].append(src)

    z = json.load(open(os.path.join(repo_dir('zhuyansen'), 'data', 'skills.json')))
    kinds = {k['id']: k['zh'] for k in z['kinds']}
    opus_set = {'JohnHeibel/PDoomVideo', 'JohnHeibel/ClaudeAnimationBase', 'lemomo-ai/lemo-opuscar',
                'ledbetterljoshua/functional-emotions-video'}
    for s in z['skills']:
        add(s['repo_full_name'], 'zhuyansen', s.get('description'), s.get('stars'), kinds.get(s.get('kind')),
            s['repo_full_name'] in opus_set)
    gh = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)')
    for e in json.load(open(os.path.join(repo_dir('coolbat'), 'data', 'usecases.json'))):
        m = gh.match(e['url'] or '')
        if m:
            add(m.group(1), 'coolbat', e.get('notes') or e.get('title'), e.get('stars'), 'Opus 5.5 作品/工具', True)
    for e in yaml.safe_load(open(os.path.join(repo_dir('frontier'), 'data', 'games.yaml'))):
        m = gh.match(e.get('repo_url') or '')
        if m and e.get('model') == 'claude-opus-5.5':
            add(m.group(1), 'frontier', f'{e["title"]}：{e.get("description", "")}', None, '游戏源码', True)
    for key, name in (('athemeroy', 'athemeroy'), ('opusvideo', 'opusvideo'), ('krillin', 'krillinai'),
                      ('lievan', 'Li-Evan'), ('openvg', 'OpenVGLab')):
        for f in glob.glob(os.path.join(repo_dir(key), '**', '*.md'), recursive=True) + \
                glob.glob(os.path.join(repo_dir(key), '*.json')):
            for m in gh.finditer(open(f, errors='ignore').read()):
                full = re.sub(r'\.git$', '', m.group(1))
                if full.split('/')[0].lower() in ('user-attachments', 'orgs', 'settings', 'features', 'topics', 'apps'):
                    continue
                if full.lower() == REPOS[key].lower():
                    continue
                add(full, name, None, None, None, False)
    # 本次 GitHub 搜索找到、上面各仓库没收的单项作品/合集
    for full, desc in [
        ('riba2534/claude-opus-5-5-demo', 'Opus 5.5 演示合集：QQ 飞车、穿越火线运输船、鹈鹕骑车等'),
        ('dgreenheck/tidewater', '用 Opus 5.5 做的海边小镇'),
        ('diggerhq/shipvideo', '给网址或提示词，Opus 5.5 写 HTML 生成发布视频'),
        ('MiaAI-Lab/Claude-Opus-5.5-100-HTML-Files', '100 个 Opus 5.5 生成的单文件 HTML 页面'),
        ('OminousIndustries/OpusSkate', 'Opus 5.5 写的 C++ 滑板游戏'),
        ('bridge-mind/turbo-kart-rally', 'Three.js 卡丁车，单提示词五个子 agent 并行'),
        ('Barty-Bart/opus-55-10k-websites', 'Opus 5.5 + Higgsfield MCP 做无人机穿梭式品牌网站'),
        ('arimanyus/hophopnopenope', '《Hop Hop, Nope Nope》MV 源码（Opus 5.5 + Cursor）'),
        ('TripoGrowthLab/awesome-opus-5-5-prompts', 'Opus 5.5 3D 场景、游戏、动画提示词'),
        ('klsoen/opus-js-animations', 'Opus 5.5 用 JavaScript 导演和渲染短片的流程'),
        ('makevoid/motion-graphics-music-video-skill', '由音乐生成动态图形 MV 的 Opus 5.5 插件'),
        ('tuzhechen2005/opus-video-skills', 'Claude Code 里 Opus 5.5 做视频的 skill'),
        ('SilentFleetKK/qingming-bianjing', '同一提示词：Opus 5.5 与 GPT 6 Sol 各写《清明上河图》3D 网页'),
        ('iart-ai/javascript-animation-skills', 'Opus 5.5 式逐帧 JavaScript 动画 skill'),
        ('morganlinton/vulcanbench-opus55-traces', 'Opus 5.5 在 VulcanBench 上的 115 条 Claude Code 会话记录'),
        ('ismoshushi/awesome-opus-video-skills', '只收开源可安装的视频类 Agent Skill'),
        ('xiiyioozzz/opus55-3d-games', '一句话提示词生成的三个 3D 网页游戏'),
        ('Maoku/Opus55OpticalIllusion', 'Opus 5.5 xhigh 做的错觉美术馆'),
        ('Zp-Peter/gpt6-opus55-benchmark-showcase', 'GPT-6 与 Opus 5.5 五项实测作品'),
        ('kimi-cli/awesome-opus-5', 'Opus 5 系列发布、API、迁移资料合集'),
    ]:
        add(full, 'GitHub 搜索', desc, None, 'Opus 5.5 作品/工具', True)
    # 去掉被截断的链接（是另一个已收仓库名的前缀）和第三方依赖库
    names = [t['repo'].lower() for t in tools.values()]
    for k in list(tools):
        if k in NOT_TOOLS or any(n != k and n.startswith(k) and n.split('/')[0] == k.split('/')[0] for n in names):
            del tools[k]
    enrich_github(tools)
    return tools


NOT_TOOLS = {'google/draco', 'khronosgroup/gltf', 'binomialllc/basis_universal'}


def enrich_github(tools):
    """用 gh api 补星数和简介，结果缓存在 data/github_meta.json。"""
    cache_path = os.path.join(ROOT, 'data', 'github_meta.json')
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    for k, t in tools.items():
        if k not in cache:
            r = subprocess.run(['gh', 'api', f'repos/{t["repo"]}', '--jq',
                                '{stars: .stargazers_count, desc: .description, full: .full_name}'],
                               capture_output=True, text=True)
            cache[k] = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
        meta = cache[k]
        if meta:
            t['stars'] = meta['stars'] if meta.get('stars') is not None else t['stars']
            t['desc'] = t['desc'] or meta.get('desc')
            t['repo'] = meta.get('full') or t['repo']
        else:
            t['gone'] = True
    json.dump(cache, open(cache_path, 'w'), ensure_ascii=False, indent=1)


LISTS = [  # 合集类仓库本身
    ('athemeroy/awesome-opus-5-5-videos', '研究档案：1,401 个视频语料 + 168 条人工深读', 'athemeroy'),
    ('opusvideo/awesome-claude-video', '53 条高浏览量精选 + 实现指南', 'opusvideo'),
    ('zhuyansen/awesome-claude-video-skills', '180 个做视频的 skill/工具（非作品合集）', 'zhuyansen'),
    ('lemomo-ai/lemo-opuscar', '作者自制 39 种风格样片 + 风格提示词', 'lemo'),
    ('yihui-dev/awesome-opus5-5-videos', '282 条热门视频，带提示词', 'yihui'),
    ('Li-Evan/awesome-opus-5.5-video-prompts', '334 条逐字提示词', 'lievan'),
    ('theolundqvist/frontier-games', 'Opus 5.5 / GPT-6 Astra 游戏和影片（本表只取 Opus）', 'frontier'),
    ('coolbat/awesome-opus-5.5-usecase', '游戏、3D、影片、agent 综合用例', 'coolbat'),
    ('krillinai/awesome-opus-animation', '动画、3D 场景和可玩项目', 'krillin'),
    ('OpenVGLab/awesome-opus5.5-frontend-showcases', '前端作品：SVG、Lottie、Three.js、鹈鹕测试', 'openvg'),
    ('joeseesun/opus-video-prompts', '54 个案例的中文提示词', 'joeseesun'),
    ('riba2534/claude-opus-5-5-demo', '作者自制演示项目（无帖子链接，列入工具与仓库）', 'riba'),
]


# ---------- 汇总 ----------
def finalize(it):
    votes = it['votes'] or {'video': 1}
    best = max(votes.values())
    top = next(t for t in TIE_ORDER if votes.get(t) == best)
    sub = None
    if top == 'video':
        sv = {k: v for k, v in it['subvotes'].items() if k in VIDEO_SUBS}
        real = {k: v for k, v in sv.items() if k != 'other'}
        pool = real or sv
        sub = max(pool, key=lambda k: (pool[k], -list(VIDEO_SUBS).index(k))) if pool else 'other'

    def pick(d, order):
        for s in order:
            if s in d:
                return d[s]
        return next(iter(d.values()), None)

    zh_order = ['lievan', 'opusvideo', 'krillin', 'openvg', 'joeseesun', 'lemo', 'athemeroy']
    en_order = ['lievan', 'opusvideo', 'frontier', 'athemeroy', 'coolbat', 'lemo', 'athemeroy_corpus']
    prompts = sorted(it['prompts'], key=lambda p: (PROMPT_RANK.get(p['src'], 9), -len(p['text'])))
    p = prompts[0] if prompts else None
    date = it['date']
    sd = snowflake_date(it['key']) if it['key'].isdigit() else None
    if sd:
        date = str(sd)
    title_zh = pick(it['titles_zh'], zh_order)
    title_en = pick(it['titles_en'], en_order)
    return dict(
        id=it['key'], url=it['url'], top=top, top_zh=TOPS[top], sub=sub, sub_zh=VIDEO_SUBS.get(sub) if sub else None,
        title=title_zh or title_en or (f'（据提示词）{it["extra"]["auto_title"]}' if it['extra'].get('auto_title') else '（无标题）'), title_en=title_en, author=it['author'], date=date,
        desc=pick(it['descs_zh'], zh_order) or pick(it['descs_en'], en_order),
        likes=it['likes'], views=it['views'], tools=sorted({t.lower(): t for t in sorted(it['tools'])}.values(), key=str.lower),
        demo=sorted(it['demo']), repo=sorted(it['repo']),
        prompt=p['text'] if p else None, prompt_zh=p['zh'] if p else None,
        prompt_kind=p['kind'] if p else None, prompt_source=SOURCE_NAMES.get(p['src']) if p else None,
        sources=[SOURCE_NAMES.get(s, s) for s in it['sources']], source_count=len(it['sources']),
        curated=it['curated'], classifier=it['extra'].get('classifier'),
        before_release=bool(sd and sd < OPUS55_RELEASE - datetime.timedelta(days=1)),
        guide=it['extra'].get('guide'),
    )


def fmt_n(n):
    if n is None:
        return None
    return f'{n / 10000:.1f}万' if n >= 10000 else f'{n:,}'


def md_escape(s):
    return (s or '').replace('\n', ' ').replace('|', '\\|').strip()


def fence(text):
    t = text.strip()
    ticks = '````' if '```' in t else '```'
    return f'{ticks}text\n{t}\n{ticks}'


def render_entry(r):
    lines = [f'### {md_escape(r["title"])}', '']
    is_x = bool(STATUS_RE.match(r['url']))
    meta = [f'[原帖]({r["url"]})' if is_x else f'[链接]({r["url"]})']
    if r['author']:
        meta.append(f'@{r["author"]}' if is_x else r['author'])
    if r['date']:
        meta.append(r['date'])
    if r['likes']:
        meta.append(f'赞 {fmt_n(r["likes"])}')
    if r['views']:
        meta.append(f'浏览 {fmt_n(r["views"])}')
    lines.append(' · '.join(meta) + '  ')
    extra = []
    if r['demo']:
        extra.append('在线：' + ' '.join(f'[{i + 1}]({u})' for i, u in enumerate(r['demo'][:3])))
    if r['repo']:
        extra.append('源码：' + ' '.join(f'[{u.split("github.com/")[-1]}]({u})' for u in r['repo'][:3]))
    if r['tools']:
        extra.append('工具：' + '、'.join(r['tools'][:8]))
    if extra:
        lines.append(' · '.join(extra) + '  ')
    lines.append(f'收录于：{"、".join(r["sources"])}')
    if r['title_en'] and r['title_en'] != r['title']:
        lines += ['', f'*{md_escape(r["title_en"])}*']
    if r['before_release']:
        lines += ['', '> 注意：发帖日期早于 Opus 5.5 发布日（2026-09-22），模型归属存疑。']
    if r['desc']:
        lines += ['', md_escape(r['desc'])]
    if r['prompt']:
        lines += ['', f'<details><summary>提示词（{r["prompt_kind"]}，来自 {r["prompt_source"]}，{len(r["prompt"])} 字符）</summary>',
                  '', fence(r['prompt'])]
        if r['prompt_zh'] and r['prompt_zh'] != r['prompt']:
            lines += ['', '中文译文：', '', fence(r['prompt_zh'])]
        lines += ['', '</details>']
    if r.get('guide'):
        lines += ['', '<details><summary>实现步骤（来自 opusvideo 实现指南）</summary>', '', r['guide'], '', '</details>']
    lines.append('')
    return '\n'.join(lines)


def sort_key(r):
    return (-(r['likes'] or 0), -(r['views'] or 0), r['date'] or '')


def write_outputs(rows, tools):
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'cases'), exist_ok=True)
    for f in glob.glob(os.path.join(ROOT, 'cases', '*.md')):
        os.remove(f)
    main = [r for r in rows if r['curated']]
    cand = [r for r in rows if not r['curated'] and not r['before_release']]

    json.dump(rows, open(os.path.join(ROOT, 'data', 'cases.json'), 'w'), ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, 'data', 'cases.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['id', '分类', '子类', '标题', '英文标题', '作者', '日期', '赞', '浏览', '原帖/链接', '在线体验', '源码',
                    '工具', '提示词类型', '提示词', '收录来源', '来源数', '人工整理', '分类器标签'])
        for r in sorted(rows, key=lambda r: (list(TOPS).index(r['top']), sort_key(r))):
            w.writerow([r['id'], r['top_zh'], r['sub_zh'] or '', r['title'], r['title_en'] or '', r['author'] or '',
                        r['date'] or '', r['likes'] or '', r['views'] or '', r['url'], ' '.join(r['demo']),
                        ' '.join(r['repo']), '、'.join(r['tools']), r['prompt_kind'] or '', r['prompt'] or '',
                        '、'.join(r['sources']), r['source_count'], '是' if r['curated'] else '否', r['classifier'] or ''])

    by_top = defaultdict(list)
    for r in main:
        by_top[r['top']].append(r)
    for top, fname in TOP_FILES.items():
        rs = by_top.get(top, [])
        out = [f'# {TOPS[top]}（{len(rs)} 条）', '', '[← 返回总览](../README.md)', '',
               '按点赞数排序，没有互动数据的排在后面。“收录于”列出这条出现在哪些源仓库。', '']
        if top == 'video':
            groups = defaultdict(list)
            for r in rs:
                groups[r['sub']].append(r)
            out.append('视频条目较多，按子类拆成单独文件：')
            out.append('')
            for i, s in enumerate(VIDEO_SUBS, 1):
                if not groups.get(s):
                    continue
                sub_file = f'01-{i}-视频-{VIDEO_SUBS[s].replace(" ", "")}.md'
                out.append(f'- [{VIDEO_SUBS[s]}（{len(groups[s])}）]({sub_file})')
                sub_out = [f'# 视频与动画 · {VIDEO_SUBS[s]}（{len(groups[s])} 条）', '',
                           f'[← 视频与动画](01-视频与动画.md) · [总览](../README.md)', '',
                           '按点赞数排序，没有互动数据的排在后面。', '']
                sub_out += [render_entry(r) for r in sorted(groups[s], key=sort_key)]
                open(os.path.join(ROOT, 'cases', sub_file), 'w').write('\n'.join(sub_out))
        else:
            out += [render_entry(r) for r in sorted(rs, key=sort_key)]
        open(os.path.join(ROOT, 'cases', fname), 'w').write('\n'.join(out))

    # 待核实候选：只出现在 athemeroy 分类器语料里
    out = ['# 待核实候选（仅来自 athemeroy 分类器语料）', '', '[← 返回总览](../README.md)', '',
           f'共 {len(cand)} 条。athemeroy 在 X 上检索到这些带视频的帖子，视觉模型根据九帧截图判断与 Opus 5.5 有关'
           '（yes / likely），但没有人工细读，其他 11 个仓库也都没收。标题是分类器写的英文主题概括。已剔除发帖早于 Opus 5.5 发布的帖子。', '',
           '| 分类 | 主题（分类器概括） | 原帖 | 日期 | 分类器 |', '|---|---|---|---|---|']
    for r in sorted(cand, key=lambda r: (list(TOPS).index(r['top']), r['sub'] or '', r['date'] or '')):
        cat = r['top_zh'] + (f' / {r["sub_zh"]}' if r['sub_zh'] else '')
        out.append(f'| {cat} | {md_escape(r["title"])} | [@{r["author"]}]({r["url"]}) | {r["date"] or ""} | {r["classifier"]} |')
    open(os.path.join(ROOT, 'cases', '08-待核实候选.md'), 'w').write('\n'.join(out) + '\n')

    # 工具与仓库
    tl = sorted(tools.values(), key=lambda t: (not t['opus'], -(t['stars'] or 0), t['repo'].lower()))
    out = ['# 开源工具、Skill 与作品源码仓库', '', '[← 返回总览](../README.md)', '',
           f'共 {len(tl)} 个仓库。前半部分是明确跟 Opus 5.5 有关的（作品源码、专用 skill），后半部分是各合集里提到的通用视频工具。'
           f'星数为 {datetime.date.today()} 从 GitHub API 取得。', '',
           '| 仓库 | 星数 | 类型 | 说明 | 出现在 |', '|---|---:|---|---|---|']
    for t in tl:
        gone = '（已删除或私有）' if t.get('gone') else ''
        out.append(f'| [{t["repo"]}](https://github.com/{t["repo"]}){gone} | {t["stars"] if t["stars"] is not None else ""} | {t["kind"] or ""} | '
                   f'{md_escape((t["desc"] or "")[:160])} | {"、".join(t["sources"])} |')
    open(os.path.join(ROOT, 'cases', '09-开源工具与仓库.md'), 'w').write('\n'.join(out) + '\n')
    return main, cand, tl


def write_readme(rows, main, cand, tools):
    per_src = defaultdict(int)
    only_src = defaultdict(int)
    for r in main:
        for s in r['sources']:
            per_src[s] += 1
        cur = [s for s in r['sources'] if s != SOURCE_NAMES['athemeroy_corpus']]
        if len(cur) == 1:
            only_src[cur[0]] += 1
    top_count = defaultdict(int)
    for r in main:
        top_count[r['top']] += 1
    with_prompt = sum(1 for r in main if r['prompt'])
    verbatim = sum(1 for r in main if r['prompt'] and r['prompt_kind'] in ('原文', '部分原文'))
    multi = sum(1 for r in main if len([s for s in r['sources'] if s != SOURCE_NAMES['athemeroy_corpus']]) >= 2)
    today = datetime.date.today()

    out = ['# ONE SHOT 一镜', '',
           '**一句提示词 一镜到底**', '',
           'Claude Opus 5.5 用例大全。把 GitHub 上 12 个 Opus 5.5 合集仓库合并去重，每部作品附原帖、视频和能找到的提示词。', '',
           '- 在线看：**https://one-shot-peach.vercel.app** 可按分类筛选、搜索、看视频、复制提示词',
           '- 本地看：打开 [`web/index.html`](web/index.html)',
           '- 关注我们：[@sciencedegens](https://x.com/sciencedegens)', '',
           f'整理日期 {today}，源仓库数据截至 2026-09-27。', '',
           '## 总数', '',
           f'- **人工整理过的用例 {len(main)} 条**：至少被一个仓库人工收录。按 X 帖子 ID 去重，同一条帖子在几个仓库出现只算一次。',
           f'  - 其中 {multi} 条被两个及以上仓库同时收录',
           f'  - {with_prompt} 条带提示词，其中 {verbatim} 条是原文（其余是摘要、摘录或实现指南）',
           f'- **待核实候选 {len(cand)} 条**：只出现在 athemeroy 的分类器语料里，没人细看过，单独放在 [待核实候选](cases/08-待核实候选.md)。',
           f'- **开源仓库 {len(tools)} 个**：作品源码、skill、工具，见 [开源工具与仓库](cases/09-开源工具与仓库.md)。', '',
           '## 分类', '', '| 分类 | 条数 | 文件 |', '|---|---:|---|']
    for top, fname in TOP_FILES.items():
        out.append(f'| {TOPS[top]} | {top_count.get(top, 0)} | [cases/{fname}](cases/{fname}) |')
    out += [f'| 待核实候选 | {len(cand)} | [cases/08-待核实候选.md](cases/08-待核实候选.md) |',
            f'| 开源工具与仓库 | {len(tools)} | [cases/09-开源工具与仓库.md](cases/09-开源工具与仓库.md) |', '']
    vs = defaultdict(int)
    for r in main:
        if r['top'] == 'video':
            vs[r['sub']] += 1
    out += ['视频与动画的子类：' + ' · '.join(f'{VIDEO_SUBS[s]} {vs[s]}' for s in VIDEO_SUBS if vs.get(s)), '',
            '## 来源仓库', '',
            '“贡献”是这个仓库收录、且进了人工整理表的条数；“独有”是只有它收了的条数。', '',
            '| 仓库 | 内容 | 贡献 | 独有 |', '|---|---|---:|---:|']
    for full, desc, key in LISTS:
        name = SOURCE_NAMES.get(key, key)
        out.append(f'| [{full}](https://github.com/{full}) | {desc} | {per_src.get(name, "—")} | {only_src.get(name, "—")} |')
    out += ['', '## 怎么合并的', '',
            '- **去重**：X 帖子统一成 `https://x.com/作者/status/ID`，按 ID 合并；不是 X 帖子的（GitHub、B 站、网站）按链接合并。',
            '- **分类**：每个仓库原有的分类映射到统一分类后投票，票数相同时按 游戏 > 3D 场景 > 网页 > Agent > 评测 > 视频 的顺序定。'
            'athemeroy 分类器的票权重较低。',
            '- **提示词**：同一条有多个来源时，优先取逐字原文（Li-Evan > yihui-dev > joeseesun > OpenVGLab），'
            '其次是 opusvideo 实现指南、krillinai 摘录、athemeroy 摘要。',
            '- **日期**：X 帖子的日期从帖子 ID 里直接算出（UTC）。',
            '- **互动数**：取各仓库记录里最大的一个。各仓库抓取时间不同（9 月 25–27 日），只能大致参考。',
            '- **只收 Opus 5.5**：frontier-games 里 GPT-6 Astra 的作品没收；athemeroy 语料里分类器判为“与 Opus 无关”的 282 个没收。', '',
            '## 已知缺口', '',
            '- 源仓库都只更新到 9 月 26–27 日，之后的新帖没有。',
            '- 模型是否真是 Opus 5.5 基本靠作者自述，没有逐条复核。',
            '- 视频和游戏收得多；Agent、编程、长任务这类用例几乎没人整理，这里也很少。',
            '- 标题、简介保留源仓库原文，部分只有英文。', '',
            '## 文件', '',
            '- `cases/*.md`：按分类阅读',
            '- `data/cases.csv`：全部条目（含待核实），Excel 可直接打开',
            '- `data/cases.json`：完整数据，含全部提示词',
            '- `scripts/build.py`：合并脚本。`python3 scripts/build.py --fetch` 会拉取源仓库最新版本再重新生成',
            '- `sources/`：12 个源仓库的本地克隆', '']
    open(os.path.join(ROOT, 'README.md'), 'w').write('\n'.join(out))


def main():
    if '--fetch' in sys.argv:
        fetch()
    for fn in (load_lievan, load_yihui, load_opusvideo, load_frontier, load_coolbat, load_krillin, load_openvg,
               load_joeseesun, load_athemeroy, load_lemo):
        before = len(S.items)
        fn()
        print(f'{fn.__name__:16s} 新增 {len(S.items) - before:5d}  累计 {len(S.items)}')
    rows = [finalize(it) for it in S.items.values()]
    tools = load_tools()
    main_rows, cand, tl = write_outputs(rows, tools)
    write_readme(rows, main_rows, cand, tl)
    print(f'人工整理 {len(main_rows)}，待核实 {len(cand)}，工具仓库 {len(tl)}')


if __name__ == '__main__':
    main()
