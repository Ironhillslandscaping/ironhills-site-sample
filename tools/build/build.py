#!/usr/bin/env python3
"""Build a static GitHub Pages copy of ironhillslandscaping.com from captured Wix page data (pages/*.json)."""
import json, glob, re, os, hashlib, html, sys, shutil, io, concurrent.futures as cf, urllib.request
from urllib.parse import urlparse, quote, unquote
from PIL import Image

CAP = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/workspace/ironhills-ghpages'
LIVE = 'https://www.ironhillslandscaping.com'
HOSTS = ('www.ironhillslandscaping.com', 'ironhillslandscaping.com')

pages = {}
for f in sorted(glob.glob(os.path.join(CAP, 'pages', '*.json'))):
    d = json.load(open(f))
    p = urlparse(d['url']).path.strip('/')
    pages[p] = d
PATHS = set(pages)
REDIRECTS = {'coming-soon-03': 'landscaping-design', 'coming-soon-03-3': 'hardscaping', 'general-3': 'gallery'}

# ---------------------------------------------------------------- assets
assets = {}        # key -> local relative path (from site root)
jobs = {}          # local path -> remote url
report = {'unmapped_internal': set(), 'external': set(), 'iframes': [], 'forms': [], 'videos': [], 'notes': []}

def wix_scaled(url, w=None, h=None, maxside=1600, factor=2.0):
    """Return a Wix image URL scaled for crisp display, without avif encoding."""
    u = url
    if u.startswith('//'): u = 'https:' + u
    m = re.search(r'static\.wixstatic\.com/media/([^/?#]+)', u)
    if not m: return u
    mid = m.group(1)
    if '/v1/' in u:
        def rep(mm):
            W, H = int(mm.group(2)), int(mm.group(3))
            f = min(factor, maxside / max(W, H)) if max(W, H) else 1
            f = max(f, 1.0) if max(W, H) * f <= maxside else f
            return f'/{mm.group(1)}/w_{max(1,round(W*f))},h_{max(1,round(H*f))}'
        u = re.sub(r'/(fill|fit)/w_(\d+),h_(\d+)', rep, u, count=1)
        u = re.sub(r',(enc_avif|enc_auto|quality_auto|blur_\d+|lg_1)', '', u)
        u = re.sub(r',q_\d+', ',q_85', u)
    else:
        u = f'https://static.wixstatic.com/media/{mid}/v1/fit/w_{maxside},h_{maxside},q_85/{mid}'
    return u

def asset(url, kind='img', **kw):
    if not url or url.startswith('data:'): return None
    if url.startswith('//'): url = 'https:' + url
    if kind == 'img':
        src = wix_scaled(url, **kw) if 'wixstatic.com/media' in url else url
        mid = re.search(r'static\.wixstatic\.com/media/([^/?#]+)', src)
        base = mid.group(1) if mid else os.path.basename(urlparse(src).path)
        ext = os.path.splitext(base.split('~')[0] + '.' + base.split('.')[-1])[1].lower() or '.jpg'
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'): ext = '.jpg'
        name = re.sub(r'[^a-z0-9]+', '-', unquote(base).lower().rsplit('.', 1)[0])[:40].strip('-')
        local = f'assets/img/{name}-{hashlib.sha1(src.encode()).hexdigest()[:8]}{ext}'
    elif kind == 'video':
        src = url.replace('/1080p/', '/720p/')
        mid = re.search(r'/video/([^/]+)/', src)
        local = f'assets/video/{mid.group(1) if mid else hashlib.sha1(src.encode()).hexdigest()[:12]}.mp4'
    else:
        src = url; local = f'assets/{kind}/{os.path.basename(urlparse(url).path)}'
    jobs[local] = src
    return local

def download_all():
    def fetch(item):
        local, src = item
        dst = os.path.join(OUT, local)
        if os.path.exists(dst) and os.path.getsize(dst) > 0: return local, 'cached'
        if local.endswith('.png') and os.path.exists(dst[:-4] + '.jpg'):
            remap[local] = local[:-4] + '.jpg'; return local, 'cached-jpg'
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        for attempt in range(3):
            try:
                req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/jpeg,image/png,image/*;q=0.8,video/mp4,*/*;q=0.5'})
                data = urllib.request.urlopen(req, timeout=120).read()
                if local.startswith('assets/video/') and len(data) < 1000 and '/720p/' in src:
                    src = src.replace('/720p/', '/480p/'); continue
                open(dst, 'wb').write(data); return local, len(data)
            except Exception as e:
                err = e
                if local.startswith('assets/video/') and '/720p/' in src: src = src.replace('/720p/', '/480p/')
        return local, f'ERR {err}'
    res = list(cf.ThreadPoolExecutor(16).map(fetch, sorted(jobs.items())))
    bad = [r for r in res if isinstance(r[1], str) and r[1].startswith('ERR')]
    return res, bad

def optimize_images():
    """Recompress oversized PNG photos (no transparency) to JPEG-quality PNG->JPG is avoided to keep paths stable; just quantize big ones."""
    saved = 0
    for local in list(jobs):
        p = os.path.join(OUT, local)
        if not os.path.exists(p) or not local.endswith('.png'): continue
        if os.path.getsize(p) < 400_000: continue
        try:
            im = Image.open(p)
            hasalpha = im.mode in ('RGBA', 'LA') and im.getchannel('A').getextrema()[0] < 250
            if hasalpha: continue
            buf = io.BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=84, optimize=True, progressive=True)
            if buf.tell() < os.path.getsize(p) * 0.7:
                newlocal = local[:-4] + '.jpg'
                open(os.path.join(OUT, newlocal), 'wb').write(buf.getvalue()); saved += os.path.getsize(p) - buf.tell(); os.remove(p)
                remap[local] = newlocal
        except Exception as e:
            print('opt fail', local, e)
    return saved
remap = {}

# ---------------------------------------------------------------- styles
HELV = "'Helvetica Neue',Helvetica,Arial,sans-serif"
AVEN = "'Nunito Sans',Avenir,'Helvetica Neue',Arial,sans-serif"
FONTMAP = {
    'helvetica-w01-light': (HELV, 300, None), 'helvetica-w01-roman': (HELV, 400, None), 'helvetica-w01-bold': (HELV, 700, None),
    'helveticaneuew01-45ligh': (HELV, 300, None),
    'avenir-lt-w01_35-light1475496': (AVEN, 300, None), 'avenir-lt-w01_85-heavy1475544': (AVEN, 800, None),
    'wfont_d23f19_ef8b03dc12d647a4be1ba06fc40b277d': (AVEN, 900, None),
    'corben': ("Corben,Georgia,serif", None, None),
    'cormorantgaramond-semibold': ("'Cormorant Garamond',Georgia,serif", 600, None), 'cormorantgaramond-light': ("'Cormorant Garamond',Georgia,serif", 300, None),
    'cormorantgaramond': ("'Cormorant Garamond',Georgia,serif", None, None), 'cormorant garamond': ("'Cormorant Garamond',Georgia,serif", None, None),
    'barlow-medium': ("Barlow,sans-serif", 500, None), 'barlow': ("Barlow,sans-serif", None, None),
    'bree-w01-thin-oblique': ("'Bree Serif',Georgia,serif", 400, 'italic'),
    'poppins-semibold': ("Poppins,sans-serif", 600, None), 'playfair display': ("'Playfair Display',Georgia,serif", None, None),
    'georgia': ("Georgia,serif", None, None), 'arial': ("Arial,Helvetica,sans-serif", None, None),
    'eb garamond': ("'EB Garamond',Georgia,serif", None, None), 'futura-lt-w01-book': ("Jost,sans-serif", 400, None),
    'proxima-n-w01-reg': ("Montserrat,sans-serif", 400, None), 'din-next-w01-light': ("Barlow,sans-serif", 300, None),
}
def fix_style(st, block=False):
    if not st: return ''
    props = []
    for part in st.split(';'):
        if ':' not in part: continue
        k, v = part.split(':', 1); k = k.strip().lower(); v = v.strip()
        if not k or not v: continue
        props.append([k, v])
    d = dict(props)
    out = {}
    for k, v in props: out[k] = v
    if 'font-family' in out:
        fam = out['font-family'].split(',')[0].strip().strip("'\"").lower()
        if fam in FONTMAP:
            css, wt, sty = FONTMAP[fam]
            out['font-family'] = css
            declared = out.get('font-weight')
            if wt and (declared in (None, '400', 'normal') or (wt > 400 and declared and int(declared) < wt if declared.isdigit() else False)):
                out['font-weight'] = str(wt)
            if sty: out['font-style'] = sty
        else:
            out['font-family'] = f"'{out['font-family']}',{HELV}"
    fs = out.get('font-size', '')
    m = re.match(r'([\d.]+)px$', fs)
    if m:
        x = float(m.group(1))
        lh = out.get('line-height', '')
        ml = re.match(r'([\d.]+)px$', lh)
        if ml and x: out['line-height'] = f'{float(ml.group(1))/x:.3f}'.rstrip('0').rstrip('.')
        if x > 22: out['font-size'] = f'clamp({max(20, round(x*0.6))}px,{x/12.8:.2f}vw,{x:g}px)'
    out.pop('text-decoration', None) if out.get('text-decoration') == 'none' else None
    return ';'.join(f'{k}:{v}' for k, v in out.items())

def rel_prefix(path):
    depth = len([x for x in path.split('/') if x])
    return '../' * depth if depth else './'

def map_href(href, path):
    if not href: return href
    href = html.unescape(href).strip()
    if href.startswith(('tel:', 'mailto:', 'sms:', 'javascript:')): return href
    if href.startswith('#'): return href
    pu = urlparse(href)
    if pu.netloc in HOSTS or (not pu.netloc and not pu.scheme):
        p = unquote(pu.path).strip('/')
        p = REDIRECTS.get(p, p)  # live Wix 301s for retired URLs
        frag = ('#' + pu.fragment) if pu.fragment else ''
        if p in PATHS:
            pre = rel_prefix(path)
            return (pre + (p + '/' if p else '')) + frag if (pre + p) else './'
        report['unmapped_internal'].add(href)
        return LIVE + '/' + p + (('?' + pu.query) if pu.query else '') + frag
    report['external'].add(href.split('?')[0][:120])
    return href

def esc(s): return html.escape(s or '', quote=True)

def rewrite_html(fragment, path):
    pre = rel_prefix(path)
    def a_rep(m):
        href = html.unescape(m.group(1))
        new = map_href(href, path)
        ext = new.startswith('http') and not urlparse(new).netloc in HOSTS
        return f'href="{esc(new)}"'
    fragment = re.sub(r'href="([^"]*)"', a_rep, fragment)
    def img_rep(m):
        src = html.unescape(m.group(1)); w = int(m.group(2) or 0); h = int(m.group(3) or 0)
        loc = asset(src)
        return f'src="{pre}{loc}" data-w="{w}" data-h="{h}"' if loc else m.group(0)
    fragment = re.sub(r'src="([^"]*)" alt="[^"]*" data-w="(\d+)" data-h="(\d+)"', lambda m: img_rep(m) + f' alt=""', fragment)
    fragment = re.sub(r'style="([^"]*)"', lambda m: f'style="{esc(fix_style(m.group(1).replace(chr(39), chr(34))) )}"', fragment)
    fragment = fragment.replace('target="_self"', '')
    return fragment

# ---------------------------------------------------------------- layout
def group_rows(blocks):
    bs = sorted(blocks, key=lambda b: (b['y'], b['x']))
    rows = []
    for b in bs:
        if rows and b['y'] < rows[-1]['bottom'] - 3:
            rows[-1]['blocks'].append(b); rows[-1]['bottom'] = max(rows[-1]['bottom'], b['y'] + b['h'])
        else:
            rows.append({'top': b['y'], 'bottom': b['y'] + b['h'], 'blocks': [b]})
    return rows

def group_cols(blocks):
    bs = sorted(blocks, key=lambda b: b['x'])
    cols = []
    for b in bs:
        hit = None
        for c in cols:
            ov = min(c['x1'], b['x'] + b['w']) - max(c['x0'], b['x'])
            if ov > max(6, 0.25 * min(b['w'], c['x1'] - c['x0'])): hit = c; break
        if hit:
            hit['blocks'].append(b); hit['x0'] = min(hit['x0'], b['x']); hit['x1'] = max(hit['x1'], b['x'] + b['w'])
        else:
            cols.append({'x0': b['x'], 'x1': b['x'] + b['w'], 'blocks': [b]})
    # merge columns that overlap after growth
    merged = True
    while merged:
        merged = False
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                a, c = cols[i], cols[j]
                ov = min(a['x1'], c['x1']) - max(a['x0'], c['x0'])
                if ov > max(6, 0.25 * min(a['x1'] - a['x0'], c['x1'] - c['x0'])):
                    a['blocks'] += c['blocks']; a['x0'] = min(a['x0'], c['x0']); a['x1'] = max(a['x1'], c['x1']); cols.pop(j); merged = True; break
            if merged: break
    return sorted(cols, key=lambda c: c['x0'])

def pct(a, b): return f'{max(0.0, min(100.0, 100.0 * a / b)):.3f}%' if b else '0%'

class Ctx:
    def __init__(self, path, page): self.path = path; self.pre = rel_prefix(path); self.page = page

def render_group(blocks, x0, W, y0, ctx, depth=0):
    if not blocks: return ''
    rows = group_rows(blocks)
    out = []; prev = y0
    for row in rows:
        mt = max(0, min(row['top'] - prev, 200))
        cols = group_cols(row['blocks'])
        if len(row['blocks']) == 1:
            b = row['blocks'][0]
            out.append(wrap_block(b, x0, W, mt, ctx))
        elif len(cols) == 1:
            c = cols[0]
            if len(group_rows(c['blocks'])) == 1 or depth > 12:
                # overlapping blocks (e.g. text over image): stack in y order
                p2 = row['top']; inner = []
                for b in sorted(c['blocks'], key=lambda b: (b['y'], b['x'])):
                    inner.append(wrap_block(b, x0, W, max(0, min(b['y'] - p2, 200)), ctx)); p2 = max(p2, b['y'] + b['h'])
                out.append(f'<div class="stack" style="margin-top:{mt}px">' + ''.join(inner) + '</div>')
            else:
                out.append(f'<div class="grp" style="margin-top:{mt}px">' + render_group(c['blocks'], x0, W, row['top'], ctx, depth + 1) + '</div>')
        else:
            parts = []; left = x0
            for c in cols:
                cx0 = max(c['x0'], left, x0); cx1 = min(c['x1'], x0 + W)
                cw = max(1, cx1 - cx0)
                parts.append(f'<div class="col" style="margin-left:{pct(cx0-left, W)};width:{pct(cw, W)}">' + render_group(c['blocks'], cx0, cw, row['top'], ctx, depth + 1) + '</div>')
                left = cx1
            out.append(f'<div class="row" style="margin-top:{mt}px">' + ''.join(parts) + '</div>')
        prev = row['bottom']
    return ''.join(out)

def wrap_block(b, x0, W, mt, ctx):
    bx = max(b['x'], x0); width = min(b['w'] - (bx - b['x']), x0 + W - bx)
    if b['type'] == 'text':  # allow a little slack for font substitution
        width = min(width * 1.06 + 6, x0 + W - bx)
    cls = 'blk blk-' + b['type']
    return f'<div class="{cls}" style="margin-top:{mt}px;margin-left:{pct(bx-x0, W)};width:{pct(width, W)}">' + render_block(b, ctx) + '</div>'

YT = re.compile(r'youtube\.com/embed/([A-Za-z0-9_-]{6,})')
EMBED_FILES = {}

def render_block(b, ctx):
    t = b['type']; pre = ctx.pre
    if t == 'text':
        h = rewrite_html(b['html'], ctx.path)
        if b.get('clampLines'):
            h = f'<div class="clamp" style="-webkit-line-clamp:{b["clampLines"]};line-clamp:{b["clampLines"]}">{h}</div>'
        return h
    if t == 'img':
        loc = asset(b['src'])
        alt = b.get('alt') or ''
        if re.search(r'\.(png|jpe?g|webp)$', alt, re.I) or re.match(r'^(IMG|DSC|6E3A)', alt): alt = alt  # keep Wix alt verbatim
        st = f'aspect-ratio:{b["w"]}/{b["h"]};object-fit:{b.get("fit") or "cover"}'
        if b.get('radius') and b['radius'] != '0px': st += f';border-radius:{b["radius"]}'
        img = f'<img src="{pre}{loc}" alt="{esc(alt)}" loading="lazy" style="{st}">'
        if b.get('href'):
            href = map_href(b['href'], ctx.path)
            tgt = ' target="_blank" rel="noopener"' if b.get('target') == '_blank' else ''
            return f'<a href="{esc(href)}"{tgt}>{img}</a>'
        return img
    if t == 'button':
        href = map_href(b.get('href'), ctx.path) if b.get('href') else None
        bg = b.get('bg') or 'transparent'
        st = f'background:{bg};color:{b.get("color")};border:{b.get("border") if not b.get("border","").startswith("0px") else "none"};border-radius:{b.get("radius") or 0};min-height:{b["h"]}px'
        st2 = fix_style(f'font-family:{b.get("font")};font-size:{b.get("size")};font-weight:{b.get("weight")};letter-spacing:{b.get("ls")};text-transform:{b.get("tt")}')
        tgt = ' target="_blank" rel="noopener"' if b.get('target') == '_blank' else ''
        label = esc(b.get('text') or '')
        if href:
            return f'<a class="btn" href="{esc(href)}"{tgt} style="{esc(st)};{esc(st2)}">{label}</a>'
        return f'<span class="btn" style="{esc(st)};{esc(st2)}">{label}</span>'
    if t == 'iframe':
        src = b['src']; m = YT.search(src)
        if m:
            q = 'autoplay=1&mute=1&loop=1&playlist=' + m.group(1) if 'autoplay=1' in src else ''
            report['iframes'].append((ctx.path or 'home', 'YouTube video ' + m.group(1), 'kept (YouTube embed)'))
            return f'<div class="embed" style="aspect-ratio:{b["w"]}/{b["h"]}"><iframe src="https://www.youtube.com/embed/{m.group(1)}{"?" + q if q else ""}" title="{esc(b.get("title"))}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>'
        if 'filesusr.com/html/' in src:
            fn = src.split('/html/')[1].split('?')[0]
            body = open(os.path.join(CAP, 'embeds', fn)).read() if os.path.exists(os.path.join(CAP, 'embeds', fn)) else ''
            mm = re.search(r'<iframe src="(https://www\.google\.com/maps/embed[^"]+)"', body)
            if mm:
                report['iframes'].append((ctx.path or 'home', 'Google Map (Wix HTML embed)', 'kept (Google Maps iframe inlined)'))
                return f'<div class="embed map" style="height:{b["h"]}px"><iframe src="{mm.group(1)}" title="Map" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>'
            if 'jobtread' in body:
                EMBED_FILES[fn] = body
                report['iframes'].append((ctx.path or 'home', f'JobTread web form ({fn})', 'kept: same JobTread embed HTML copied to assets/embeds/ and loaded in an iframe'))
                return (f'<!-- JobTread web form: identical HTML to the live Wix HTML embed; it loads app.jobtread.com/web-form.js and submits to JobTread directly. -->'
                        f'<div class="embed jt" style="height:{b["h"]}px"><iframe src="{pre}assets/embeds/{fn}" title="Request form" loading="lazy"></iframe></div>')
            EMBED_FILES[fn] = body
            return f'<div class="embed" style="height:{b["h"]}px"><iframe src="{pre}assets/embeds/{fn}" loading="lazy"></iframe></div>'
        report['iframes'].append((ctx.path or 'home', src[:80], 'kept as-is'))
        return f'<div class="embed" style="height:{b["h"]}px"><iframe src="{esc(src)}" loading="lazy"></iframe></div>'
    if t == 'video':
        loc = asset(b['src'], 'video'); report['videos'].append((ctx.path or 'home', loc))
        poster = asset(b['poster']) if b.get('poster') else None
        return f'<video src="{pre}{loc}" controls playsinline preload="metadata" style="aspect-ratio:{b["w"]}/{b["h"]}"' + (f' poster="{pre}{poster}"' if poster else '') + '></video>'
    if t == 'form':
        fhtml = rewrite_html(b.get('html') or '', ctx.path)
        fhtml = re.sub(r'<button type="submit" class="form-submit">(.*?)</button>', '', fhtml)
        btn = (b.get('buttons') or ['Submit'])[0]
        contact = map_href(LIVE + '/contact', ctx.path)
        emailonly = len(b.get('fields') or []) <= 2
        kind = 'Wix newsletter signup' if emailonly else 'Wix Forms contact form'
        report['forms'].append((ctx.path or 'home', kind, f'non-functional on static hosting; button re-pointed to the Contact page (live JobTread request form)'))
        st = b.get('style') or {}
        bst = ';'.join(x for x in [f'background:{st["bg"]}' if st.get('bg') else '', f'border:{st["border"]}' if st.get('border') else ''] if x)
        return (f'<!-- STATIC SAMPLE NOTE: the live page uses a {kind} that posts to Wix servers, which cannot run on GitHub Pages. '
                f'Fields are rebuilt for layout only; the button sends visitors to the Contact page, whose JobTread form is the working lead form. -->'
                f'<form class="wixform" style="{esc(bst)}" onsubmit="return false" aria-label="{esc(kind)} (static sample)">{fhtml}'
                f'<a class="btn form-submit" href="{esc(contact)}">{esc(btn)}</a></form>')
    if t == 'box':
        st = b.get('style') or {}
        css = []
        if st.get('bg'): css.append(f'background-color:{st["bg"]}')
        layer = ''
        if st.get('image'):
            loc = asset(st['image'])
            layer = f'<div class="bgimg" style="background-image:url(\'{pre}{loc}\');opacity:{st.get("opacity", 1)}"></div>'
            css.append('position:relative')
        if st.get('border'): css.append(f'border:{st["border"]}')
        if st.get('radius'): css.append(f'border-radius:{st["radius"]}')
        if st.get('shadow'): css.append(f'box-shadow:{st["shadow"]}')
        kids = b['blocks']
        last = max((k['y'] + k['h'] for k in kids), default=b['y'])
        pb = max(0, min(b['y'] + b['h'] - last, 120))
        css.append(f'--mh:{b["h"]}px;padding-bottom:{pb}px')
        inner = render_group(kids, b['x'], b['w'], b['y'], ctx)
        if layer: inner = layer + f'<div style="position:relative;z-index:1">{inner}</div>'
        return f'<div class="box" style="{";".join(css)}">' + inner + '</div>'
    if t == 'shape':
        return ''
    if t == 'carousel':
        per = b['per']; parts = []
        for k, it in b['items']:
            if b['kind'] == 'iframe':
                report['iframes'].append((ctx.path or 'home', 'YouTube video ' + k, 'kept (YouTube embed; Wix slideshow rebuilt as a scroll strip)'))
                inner = f'<div class="embed" style="aspect-ratio:{b["iw"]}/{b["ih"]}"><iframe src="https://www.youtube.com/embed/{k}" title="YouTube video" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>'
            else:
                inner = render_block(it, ctx)
            parts.append(f'<div class="slide" style="flex:0 0 calc({100/per:.3f}% - {12*(per-1)/per:.1f}px)">{inner}</div>')
        return f'<div class="carousel" aria-label="Slideshow (scroll sideways for more)">{"".join(parts)}</div>'
    return ''


def carouselize(blocks, sec):
    """Wix slideshows/sliders leave off-screen slides in the DOM. Keep visible blocks; rebuild sliding
    YouTube embeds and image sliders as one horizontally scrollable strip; drop other off-screen items."""
    x0, x1 = sec['x'], sec['x'] + (sec['w'] or 1280)
    def vis_frac(b):
        return max(0, min(b['x'] + b['w'], x1) - max(b['x'], x0)) / max(1, b['w'])
    def slidable(b):
        return (b['type'] == 'iframe' and YT.search(b['src'] or '')) or b['type'] == 'img'
    groups = {}
    for b in blocks:
        if slidable(b): groups.setdefault((b['type'], round(b['w'] / 10), round(b['h'] / 10), round(b['y'] / 20)), []).append(b)
    out = []; used = set()
    for key, g in groups.items():
        if not any(vis_frac(b) < 0.9 for b in g) or len(g) < 2: continue
        visible = [b for b in g if vis_frac(b) >= 0.9]
        for b in g: used.add(id(b))
        if not visible:
            report['notes'].append(f"{sec.get('id')}: hidden slider of {len(g)} {key[0]} item(s) not shown on desktop; dropped"); continue
        items = []
        for b in sorted(g, key=lambda b: b['x']):
            k = YT.search(b['src']).group(1) if b['type'] == 'iframe' else b['src']
            if k not in [i[0] for i in items]: items.append((k, b))
        bx0 = min(b['x'] for b in visible); bx1 = max(b['x'] + b['w'] for b in visible)
        out.append({'type': 'carousel', 'kind': key[0], 'items': items, 'per': len(visible), 'iw': g[0]['w'], 'ih': g[0]['h'],
                    'x': bx0, 'y': min(b['y'] for b in visible), 'w': bx1 - bx0, 'h': max(b['y'] + b['h'] for b in visible) - min(b['y'] for b in visible)})
    ytcar = [c for c in out if c['type'] == 'carousel' and c['kind'] == 'iframe']
    for b in blocks:
        if id(b) in used: continue
        if vis_frac(b) >= 0.3 or b['type'] == 'box': out.append(b)
        elif b['type'] == 'iframe' and YT.search(b['src'] or '') and ytcar:
            k = YT.search(b['src']).group(1)
            if k not in [i[0] for i in ytcar[0]['items']]: ytcar[0]['items'].append((k, b))
        else: report['notes'].append(f"{sec.get('id')}: dropped off-screen {b['type']}")
    return out

def flatten_shapes(blocks):
    """Turn free-floating shapes that sit behind other blocks into boxes containing them."""
    shapes = [b for b in blocks if b['type'] == 'shape']
    rest = [b for b in blocks if b['type'] != 'shape']
    for s in sorted(shapes, key=lambda s: s['w'] * s['h']):
        inside = [b for b in rest if b['x'] >= s['x'] - 4 and b['y'] >= s['y'] - 4 and b['x'] + b['w'] <= s['x'] + s['w'] + 4 and b['y'] + b['h'] <= s['y'] + s['h'] + 4]
        if inside:
            rest = [b for b in rest if b not in inside]
            rest.append({'type': 'box', 'style': s['style'], 'blocks': inside, 'x': s['x'], 'y': s['y'], 'w': s['w'], 'h': s['h']})
    for b in rest:
        if b['type'] == 'box': b['blocks'] = flatten_shapes(b['blocks'])
    return rest

def render_section(sec, ctx, cls='sec'):
    bg = sec.get('bg') or {}
    css = []; media = ''
    if bg.get('color'): css.append(f'background-color:{bg["color"]}')
    if bg.get('image') and not bg.get('video'):
        loc = asset(bg['image'], w=None)
        op = bg.get('opacity', 1)
        media += f'<div class="bgimg" style="background-image:url(\'{ctx.pre}{loc}\');opacity:{op}"></div>'
    if bg.get('video'):
        vloc = asset(bg['video'], 'video'); report['videos'].append((ctx.path or 'home', vloc + ' (section background)'))
        ploc = asset(bg['image']) if bg.get('image') else ''
        media += f'<video class="bgvideo" style="opacity:{bg.get("opacity", 1)}" autoplay muted loop playsinline preload="metadata" src="{ctx.pre}{vloc}"' + (f' poster="{ctx.pre}{ploc}"' if ploc else '') + '></video>'
    if bg.get('overlay') and (bg.get('image') or bg.get('video')):
        media += f'<div class="overlay" style="background:{bg["overlay"]}"></div>'
    blocks = carouselize(sec['blocks'], sec)
    blocks = flatten_shapes(blocks)
    W = sec['w'] or 1280
    inner = render_group(blocks, sec['x'], W, sec['y'], ctx)
    last = max((b['y'] + b['h'] for b in blocks), default=sec['y'])
    pb = max(0, min(sec['y'] + sec['h'] - last, 160))
    css.append(f'--mh:{sec["h"]}px')
    if bg.get('image') or bg.get('video'): cls += ' has-media'
    return f'<section class="{cls}" style="{";".join(css)}">{media}<div class="wrap" style="padding-bottom:{pb}px">{inner}</div></section>'

# ---------------------------------------------------------------- page shell
home = pages['']
HEADER_BG = '#2f2e2e'

def header_html(ctx, page):
    hdr = page['header'] or home['header']
    logo = asset(home['header']['logo'])
    pre = ctx.pre
    socials = []
    for b in home['header']['blocks']:
        if b['type'] == 'text':
            for m in re.finditer(r'<a href="([^"]+)"[^>]*>\s*<img src="([^"]+)" alt="([^"]*)"', b['html']):
                socials.append((html.unescape(m.group(1)), asset(html.unescape(m.group(2))), html.unescape(m.group(3))))
    phones = hdr.get('phone') or home['header']['phone']
    nav = []
    for it in home['nav']:
        if it['text'].lower() == 'more' or not it.get('href'): continue
        href = map_href(it['href'], ctx.path)
        if it['sub']:
            sub = ''.join(f'<li><a href="{esc(map_href(s["href"], ctx.path))}">{esc(s["text"])}</a></li>' for s in it['sub'])
            nav.append(f'<li class="has-sub"><a href="{esc(href)}">{esc(it["text"])}</a><button class="sub-toggle" aria-label="Show {esc(it["text"].title())} menu">&#9662;</button><ul class="sub">{sub}</ul></li>')
        else:
            nav.append(f'<li><a href="{esc(href)}">{esc(it["text"])}</a></li>')
    soc = ''.join(f'<a href="{esc(h)}" target="_blank" rel="noopener" aria-label="{esc(a)}"><img src="{pre}{l}" alt="{esc(a)}" width="25" height="25"></a>' for h, l, a in socials)
    ph = ''.join(f'<a class="phone" href="{esc(p["href"].replace(" ", ""))}">{esc(p["text"])}</a>' for p in phones)
    return f'''<header class="site-header">
  <div class="hdr-inner">
    <a class="logo" href="{pre}"><img src="{pre}{logo}" alt="Ironhills Landscaping" width="154" height="84"></a>
    <button class="nav-toggle" aria-label="Open menu" aria-expanded="false"><span></span><span></span><span></span></button>
    <nav class="site-nav" aria-label="Site"><ul>{"".join(nav)}</ul></nav>
    <div class="hdr-right"><div class="social">{soc}</div>{ph}</div>
  </div>
</header>'''

FONTS = 'https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;700&family=Bree+Serif&family=Corben:wght@400;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;0,700;1,400&family=EB+Garamond&family=Jost:wght@400&family=Montserrat:wght@400;600&family=Nunito+Sans:wght@300;400;700;800;900&family=Playfair+Display&family=Poppins:wght@400;600&display=swap'

def page_html(path, page):
    ctx = Ctx(path, page)
    body = ''.join(render_section(s, ctx) for s in page['sections'])
    foot = render_section(page['footer'], ctx, 'sec site-footer') if page.get('footer') else ''
    title = page['title'] or 'Ironhills Landscaping'
    desc = page.get('description') or ''
    og = asset(page['ogImage']) if page.get('ogImage') else None
    return f'''<!DOCTYPE html>
<html lang="{page.get('lang') or 'en'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{f'<meta name="description" content="{esc(desc)}">' if desc else ''}
<meta name="robots" content="noindex,nofollow">
<!-- Static sample of {LIVE}/{path} (not the live site). Built from the live Wix page on 2026-11-24. -->
<meta property="og:title" content="{esc(page.get('ogTitle') or title)}">
{f'<meta property="og:image" content="{ctx.pre}{og}">' if og else ''}
<link rel="icon" href="{ctx.pre}assets/img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{ctx.pre}assets/css/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{header_html(ctx, page)}
<main id="main">
{body}
</main>
<footer>{foot}</footer>
<script src="{ctx.pre}assets/js/site.js" defer></script>
</body>
</html>
'''

def main():
    os.makedirs(OUT, exist_ok=True)
    outputs = {}
    for path, page in pages.items():
        outputs[path] = page_html(path, page)
    # favicon
    jobs['assets/img/favicon.png'] = 'https://static.wixstatic.com/media/adf499_d0fd102760ea44bdadf0c43ba4b60098~mv2.png/v1/fit/w_192,h_192,q_90/favicon.png'
    res, bad = download_all()
    print('downloaded', len(res), 'bad', len(bad))
    for b in bad: print('  ', b, jobs[b[0]])
    saved = optimize_images()
    print('png->jpg saved bytes', saved, 'remapped', len(remap))
    for path, h in outputs.items():
        for a, bnew in remap.items(): h = h.replace(a, bnew)
        d = os.path.join(OUT, path)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w').write(h)
    os.makedirs(os.path.join(OUT, 'assets/embeds'), exist_ok=True)
    for fn, body in EMBED_FILES.items():
        open(os.path.join(OUT, 'assets/embeds', fn), 'w').write('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="margin:0">' + body + '</body></html>')
    # 404 page (GitHub Pages serves /404.html for missing paths)
    open(os.path.join(OUT, '404.html'), 'w').write(f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found | Ironhills Landscaping (static sample)</title><meta name="robots" content="noindex,nofollow">
<style>body{{font-family:Helvetica,Arial,sans-serif;margin:0;background:#2f2e2e;color:#fff;display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center}}a{{color:#fdebc9}}</style></head>
<body><main><h1>Page not found</h1><p>This is a static sample of ironhillslandscaping.com.</p><p><a href="{LIVE}/">Go to the live site</a></p></main></body></html>''')
    # remove assets no longer referenced by any page (keeps the repo lean between rebuilds)
    refs = ''.join(open(os.path.join(OUT, p, 'index.html')).read() for p in outputs) + open(os.path.join(OUT, 'assets/css/site.css')).read()
    removed = 0
    for sub in ('assets/img', 'assets/video', 'assets/embeds'):
        for fn in os.listdir(os.path.join(OUT, sub)):
            if fn not in refs and fn != 'favicon.png':
                os.remove(os.path.join(OUT, sub, fn)); removed += 1
    print('removed unreferenced assets', removed)
    rep = {k: (sorted(v) if isinstance(v, set) else v) for k, v in report.items()}
    rep['pages'] = sorted(outputs); rep['assets'] = len(jobs)
    json.dump(rep, open(os.path.join(CAP, 'build-report.json'), 'w'), indent=1)
    print('pages', len(outputs), 'unmapped internal', len(report['unmapped_internal']))

if __name__ == '__main__':
    main()
