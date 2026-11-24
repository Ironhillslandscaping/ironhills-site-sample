#!/usr/bin/env python3
"""Crawl the static sample from a local server and report broken internal links/assets.

Usage:
  python3 -m http.server 8000            # from the repo root, in another terminal
  python3 tools/linkcheck.py http://localhost:8000/

Checks every <a href>, <img src>, <video src/poster>, <iframe src>, <link href>, <script src>
and CSS url(...) that points inside the site. External links (Calendly, Google, social,
tel:, mailto:) are listed but not fetched. Exits 1 if any internal reference fails.
"""
import sys, re, urllib.request, urllib.error
from urllib.parse import urljoin, urlparse, urldefrag
from html.parser import HTMLParser

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000/'
host = urlparse(BASE).netloc

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ('href', 'src', 'poster'):
            if a.get(k) and not (tag == 'link' and a.get('rel') in ('preconnect',)):
                self.refs.append((tag, k, a[k]))
        if a.get('style'):
            for u in re.findall(r"url\(['\"]?([^'\")]+)", a['style']): self.refs.append((tag, 'style', u))

status = {}
def fetch(u):
    if u in status: return status[u]
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method='GET'), timeout=30)
        body = r.read() if 'html' in r.headers.get('Content-Type', '') or u.endswith('.css') else b''
        status[u] = (r.status, body, r.headers.get('Content-Type', ''))
    except urllib.error.HTTPError as e:
        status[u] = (e.code, b'', '')
    except Exception as e:
        status[u] = (0, b'', str(e))
    return status[u]

queue = [BASE]
# also seed every page in the repo so pages not linked from the menu are checked too
import os, glob
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in glob.glob(os.path.join(root, '**', 'index.html'), recursive=True):
    rel = os.path.relpath(os.path.dirname(f), root).replace(os.sep, '/')
    if rel.startswith(('assets', 'tools')): continue
    queue.append(urljoin(BASE, '' if rel == '.' else rel + '/'))
seen = set(); broken = []; external = set(); pages = 0; checked = 0
while queue:
    page = queue.pop()
    if page in seen: continue
    seen.add(page)
    code, body, ctype = fetch(page)
    if code != 200: continue
    if 'html' not in ctype:
        if page.endswith('.css'):
            for u in re.findall(rb"url\(['\"]?([^'\")]+)", body):
                t = urljoin(page, u.decode())
                if urlparse(t).netloc == host:
                    checked += 1
                    if fetch(t)[0] != 200: broken.append((page, t, fetch(t)[0]))
        continue
    pages += 1
    p = P(); p.feed(body.decode('utf-8', 'ignore'))
    for tag, attr, ref in p.refs:
        if ref.startswith(('tel:', 'mailto:', 'sms:', 'javascript:', 'data:')): external.add(ref.split('?')[0]); continue
        t, _ = urldefrag(urljoin(page, ref))
        if urlparse(t).netloc != host:
            external.add(t); continue
        checked += 1
        c = fetch(t)[0]
        if c != 200: broken.append((page, t, c)); continue
        if tag == 'a' or (tag == 'link' and t.endswith('.css')) or (tag == 'iframe'):
            if t not in seen: queue.append(t)

print(f'pages crawled: {pages}')
print(f'internal references checked: {checked} (unique URLs fetched: {len(status)})')
print(f'external links (not fetched): {len(external)}')
if broken:
    print(f'BROKEN: {len(broken)}')
    for b in broken: print('  ', b[2], b[1], '<- on', b[0])
    sys.exit(1)
print('OK: no broken internal links or assets')
