#!/usr/bin/env python3
"""通过 fxtwitter 公开接口取每条 X 帖子的视频地址、封面和最新互动数。

结果缓存在 data/fx/<帖子ID>.json，已有缓存的跳过；加 --refresh 全部重取。
汇总写到 data/media.json，供 build_web.py 使用。
"""
import concurrent.futures as cf
import json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'data', 'fx')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/140 Safari/537.36'}


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {'code': 404}
            time.sleep(2 + i * 3)
        except Exception:
            time.sleep(2 + i * 3)
    return None


def fetch(item):
    sid, handle = item
    path = os.path.join(CACHE, f'{sid}.json')
    if os.path.exists(path) and '--refresh' not in sys.argv:
        return sid, json.load(open(path))
    d = get(f'https://api.fxtwitter.com/{handle}/status/{sid}')
    if d is not None:
        json.dump(d, open(path, 'w'), ensure_ascii=False)
    return sid, d


def pick(tweet):
    """从帖子（或它引用的帖子）里挑视频和封面。"""
    for t in (tweet, tweet.get('quote') or {}):
        m = t.get('media') or {}
        vids = m.get('videos') or []
        if vids:
            v = vids[0]
            mp4 = sorted((f for f in v.get('formats', []) if (f.get('url') or '').split('?')[0].endswith('.mp4')),
                         key=lambda f: f.get('bitrate') or 0)
            by_h = {}
            for f in mp4:
                mm = re.search(r'/(\d+)x(\d+)/', f['url'])
                if mm:
                    by_h[min(int(mm.group(1)), int(mm.group(2)))] = f['url']
            small = next((by_h[h] for h in sorted(by_h) if h >= 270), None) or (mp4[0]['url'] if mp4 else v.get('url'))
            hd = next((by_h[h] for h in sorted(by_h) if h >= 720), None) or v.get('url')
            return dict(thumb=v.get('thumbnail_url'), vs=small, vh=hd, dur=v.get('duration'),
                        w=v.get('width'), h=v.get('height'), quoted=t is not tweet)
        photos = m.get('photos') or []
        if photos:
            return dict(thumb=photos[0].get('url'), quoted=t is not tweet)
    return None


def main():
    os.makedirs(CACHE, exist_ok=True)
    rows = json.load(open(os.path.join(ROOT, 'data', 'cases.json')))
    items = []
    for r in rows:
        m = re.match(r'https://x\.com/([^/]+)/status/(\d+)', r['url'])
        if m and r['curated']:
            items.append((m.group(2), m.group(1)))
    print('X 帖子', len(items))
    out, fail = {}, 0
    with cf.ThreadPoolExecutor(6) as ex:
        for n, (sid, d) in enumerate(ex.map(fetch, items), 1):
            if not d or d.get('code') != 200:
                fail += 1
                continue
            t = d['tweet']
            e = dict(likes=t.get('likes'), views=t.get('views'), text=t.get('text'))
            e.update(pick(t) or {})
            out[sid] = e
            if n % 100 == 0:
                print(' ', n)
    json.dump(dict(fetched=time.strftime('%Y-%m-%d'), items=out), open(os.path.join(ROOT, 'data', 'media.json'), 'w'),
              ensure_ascii=False)
    vids = sum(1 for e in out.values() if e.get('vh'))
    imgs = sum(1 for e in out.values() if e.get('thumb'))
    print(f'成功 {len(out)}，失败 {fail}，有视频 {vids}，有封面 {imgs}')


if __name__ == '__main__':
    main()
