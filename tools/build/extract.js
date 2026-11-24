() => {
  const ORIGIN = location.origin;
  const shown = el => { try { return el.checkVisibility({visibilityProperty:true}); } catch(e){ return true; } };
  const vis = el => { const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
    try { return el.checkVisibility({visibilityProperty:true}); } catch(e){ return true; } };
  const sy = window.scrollY;
  const R = el => { const r = el.getBoundingClientRect(); return {x:Math.round(r.left), y:Math.round(r.top+sy), w:Math.round(r.width), h:Math.round(r.height)}; };
  const cs = el => getComputedStyle(el);
  const absUrl = u => { try { return new URL(u, location.href).href; } catch(e){ return u; } };
  const KEEP = new Set(['H1','H2','H3','H4','H5','H6','P','UL','OL','LI','A','STRONG','B','EM','I','U','BR','SPAN','BLOCKQUOTE','TABLE','TR','TD','TH','TBODY','THEAD','FIGURE','FIGCAPTION','CODE','PRE','HR']);
  const BLOCKS = new Set(['H1','H2','H3','H4','H5','H6','P','LI','BLOCKQUOTE','FIGCAPTION','TD','TH']);
  function styleOf(el, parentCs) {
    const s = cs(el); const o = [];
    if (BLOCKS.has(el.tagName)) {
      o.push('font-size:'+s.fontSize, 'line-height:'+s.lineHeight, 'font-family:'+s.fontFamily.split(',')[0].replace(/["']/g,'').trim(), 'font-weight:'+s.fontWeight, 'color:'+s.color);
      if (s.textAlign!=='start' && s.textAlign!=='left') o.push('text-align:'+s.textAlign);
      if (s.letterSpacing!=='normal') o.push('letter-spacing:'+s.letterSpacing);
      if (s.fontStyle==='italic') o.push('font-style:italic');
      if (parseFloat(s.marginTop)) o.push('margin-top:'+s.marginTop);
      if (parseFloat(s.marginBottom)) o.push('margin-bottom:'+s.marginBottom);
      if (s.textTransform!=='none') o.push('text-transform:'+s.textTransform);
      if (s.textDecorationLine && s.textDecorationLine!=='none') o.push('text-decoration:'+s.textDecorationLine);
    } else if (parentCs) {
      if (s.color!==parentCs.color) o.push('color:'+s.color);
      if (s.fontWeight!==parentCs.fontWeight) o.push('font-weight:'+s.fontWeight);
      if (s.fontStyle!==parentCs.fontStyle) o.push('font-style:'+s.fontStyle);
      if (s.fontSize!==parentCs.fontSize) o.push('font-size:'+s.fontSize);
      const ff = s.fontFamily.split(',')[0].replace(/["']/g,'').trim(); if (ff!==parentCs.fontFamily.split(',')[0].replace(/["']/g,'').trim()) o.push('font-family:'+ff);
      if (s.textDecorationLine!==parentCs.textDecorationLine && s.textDecorationLine!=='none') o.push('text-decoration:'+s.textDecorationLine);
      if (s.backgroundColor && s.backgroundColor!=='rgba(0, 0, 0, 0)') o.push('background-color:'+s.backgroundColor);
    }
    return o.join(';');
  }
  function clean(el, parentCs) {
    let out = '';
    for (const n of el.childNodes) {
      if (n.nodeType === 3) { out += n.textContent.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); continue; }
      if (n.nodeType !== 1) continue;
      const t = n.tagName;
      if (['SCRIPT','STYLE','SVG','svg','BUTTON','NOSCRIPT'].includes(t)) continue;
      if (t === 'IMG') { const src = n.currentSrc || n.src; if (src && !src.startsWith('data:')) out += `<img src="${absUrl(src)}" alt="${(n.alt||'').replace(/"/g,'&quot;')}" data-w="${Math.round(n.getBoundingClientRect().width)}" data-h="${Math.round(n.getBoundingClientRect().height)}">`; continue; }
      if (!shown(n) && t!=='BR') continue;
      const inner = clean(n, cs(n));
      if (KEEP.has(t)) {
        const tag = t.toLowerCase(); let attrs = '';
        if (t==='A') { const href = n.getAttribute('href'); if (href) attrs += ` href="${absUrl(href).replace(/"/g,'&quot;')}"`; if (n.target) attrs += ` target="${n.target}"`; }
        const st = styleOf(n, parentCs); if (st) attrs += ` style="${st.replace(/"/g,"'")}"`;
        if (t==='BR' || t==='HR') { out += `<${tag}>`; continue; }
        if (t==='SPAN' && !st) { out += inner; continue; }
        out += `<${tag}${attrs}>${inner}</${tag}>`;
      } else {
        const d = cs(n).display; const blocky = d==='block' || d==='flex' || d==='grid';
        out += inner; if (blocky && inner.trim() && !/<\/(p|h\d|li|ul|ol|div)>\s*$/.test(inner)) out += '<br>';
      }
    }
    return out;
  }

  function formClone(el) {
    let out = '';
    for (const n of el.childNodes) {
      if (n.nodeType === 3) { const t = n.textContent; if (t.trim()) out += t.replace(/&/g,'&amp;').replace(/</g,'&lt;'); continue; }
      if (n.nodeType !== 1) continue;
      const t = n.tagName;
      if (['SCRIPT','STYLE','SVG','svg','NOSCRIPT'].includes(t)) continue;
      if (t==='INPUT') { if (n.type==='hidden') continue; const lab = (n.type==='radio'||n.type==='checkbox') ? '' : '';
        out += `<input type="${n.type}"${n.name?` name="${n.name.replace(/"/g,'&quot;')}"`:''}${n.placeholder&&n.placeholder.trim()?` placeholder="${n.placeholder.replace(/"/g,'&quot;')}"`:''}${n.required?' required':''}${n.value&&(n.type==='radio'||n.type==='checkbox')?` value="${n.value.replace(/"/g,'&quot;')}"`:''}>`; continue; }
      if (t==='TEXTAREA') { out += `<textarea${n.name?` name="${n.name}"`:''}${n.placeholder?` placeholder="${n.placeholder.replace(/"/g,'&quot;')}"`:''}${n.required?' required':''}></textarea>`; continue; }
      if (t==='SELECT') { out += `<select${n.required?' required':''}>` + [...n.options].map(o=>`<option>${o.text}</option>`).join('') + '</select>'; continue; }
      if (t==='BUTTON') { out += `<button type="submit" class="form-submit">${n.innerText.trim()}</button>`; continue; }
      if (!shown(n)) continue;
      const inner = formClone(n);
      if (!inner.trim()) continue;
      if (t==='LABEL') out += `<label>${inner}</label>`;
      else if (t==='LEGEND') out += `<legend>${inner}</legend>`;
      else if (t==='FIELDSET') out += `<fieldset>${inner}</fieldset>`;
      else if (/^H[1-6]$/.test(t)||t==='P') out += `<${t.toLowerCase()}>${inner}</${t.toLowerCase()}>`;
      else if (t==='A') out += `<a href="${absUrl(n.getAttribute('href')||'')}">${inner}</a>`;
      else { const d = cs(n).display; out += (d==='inline'||d==='inline-block'||d==='inline-flex') ? inner : `<div>${inner}</div>`; }
    }
    return out;
  }
  function boxStyle(el) {
    const cands = [el, ...el.querySelectorAll(':scope > [data-testid="container-bg"], :scope > [data-testid="columnBackground"]')];
    let st = null;
    for (const c of cands) { const s = cs(c); const bg = s.backgroundColor; const hasBg = bg !== 'rgba(0, 0, 0, 0)' && !/, 0\)$/.test(bg); const bw = parseFloat(s.borderTopWidth)||0; const sh = s.boxShadow !== 'none';
      if (hasBg || bw>0 || sh) { st = st || {}; if (hasBg && !st.bg) st.bg = bg; if (bw>0 && !st.border) st.border = `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}`; if (sh && !st.shadow) st.shadow = s.boxShadow; if (s.borderRadius!=='0px' && !st.radius) st.radius = s.borderRadius; } }
    const bl = el.querySelector(':scope > [id^="bgLayers_"], :scope > [data-testid="bgLayers"]');
    if (bl) { const b = bgOf(el); if (b.color && !/, 0\)$/.test(b.color) || b.image) { st = st || {}; if (b.color && !st.bg) st.bg = b.color; if (b.image) { st.image = b.image; st.opacity = b.opacity; } if (b.video) st.video = b.video; } }
    return st;
  }
  function bgOf(sec) {
    const res = {color:null, image:null, video:null};
    const layers = sec.querySelector(':scope [data-testid="bgLayers"], :scope [id^="bgLayers_"]');
    const scope = layers || sec;
    const s = cs(sec); if (s.backgroundColor!=='rgba(0, 0, 0, 0)') res.color = s.backgroundColor;
    if (s.backgroundImage && s.backgroundImage!=='none' && s.backgroundImage.includes('url(')) res.image = s.backgroundImage.match(/url\("?([^")]+)/)[1];
    if (layers) {
      for (const e of layers.querySelectorAll('*')) { const c = cs(e); if (c.backgroundColor!=='rgba(0, 0, 0, 0)' && !res.color) res.color = c.backgroundColor;
        if (c.backgroundImage.includes('url(') && !res.image) res.image = c.backgroundImage.match(/url\("?([^")]+)/)[1]; }
      const im = layers.querySelector('img'); if (im) res.image = im.currentSrc || im.src;
      const v = layers.querySelector('video'); if (v) { res.video = v.currentSrc || v.src; res.poster = v.poster; }
      const media = v || im; if (media) { let op = 1, e = media; while (e && e !== layers) { op *= parseFloat(cs(e).opacity); e = e.parentElement; } res.opacity = Math.round(op*100)/100; }
      const ov = [...layers.querySelectorAll('[data-testid="colorUnderlay"], [data-testid="bgOverlay"], div')].map(e=>cs(e)).filter(c=>c.backgroundColor.startsWith('rgba') && !c.backgroundColor.endsWith(', 0)') ).map(c=>c.backgroundColor);
      if (ov.length) res.overlay = ov[ov.length-1];
    }
    return res;
  }
  function blocksIn(root, skip) {
    const blocks = [];
    const walk = (el, out) => {
      if (skip && skip(el)) return;
      if (el.matches('[data-testid="bgLayers"], [id^="bgLayers_"], script, style, noscript, svg, nav[aria-label="Site"]')) return;
      if (!shown(el)) return;
      const t = el.tagName;
      const leafOk = vis(el);
      if (el !== root && !el.matches('form, a, button, [data-testid="richTextElement"], img, iframe, video')) { const r0 = el.getBoundingClientRect();
        const rr = root.getBoundingClientRect(); if (r0.width >= 60 && r0.height >= 40 && (!(r0.width >= rr.width - 40 && r0.height >= rr.height - 40) || el.querySelector(':scope > [id^="bgLayers_"]'))) { const bs = boxStyle(el);
          if (bs && (el.querySelector('img, [data-testid="richTextElement"], p, h1, h2, h3, h4, a') || el.innerText.trim())) { const kids = []; for (const c of el.children) walk(c, kids);
            if (kids.length === 1 && kids[0].type==='img' && !bs.border) { out.push(kids[0]); return; }
            if (kids.length) { out.push({type:'box', style: bs, blocks: kids, ...R(el)}); return; } }
          else if (bs && !el.querySelector('img, video, iframe') && !el.innerText.trim()) { out.push({type:'shape', style: bs, ...R(el)}); return; } } }

      if (el.matches('[data-testid="richTextElement"]')) { if(!leafOk) return; let html = clean(el, cs(el)); { const pa = el.closest('a[href]'); if (pa && !/<a /.test(html)) html = `<a href="${absUrl(pa.getAttribute('href'))}">${html}</a>`; } if (html.replace(/<[^>]+>/g,'').trim() || html.includes('<img')) out.push({type:'text', html, ...R(el)}); return; }
      if (t==='FORM' || el.matches('[data-testid="form-root"], [data-hook="form-container"]')) {
        const fields = [...el.querySelectorAll('input, textarea, select')].filter(f=>f.type!=='hidden').map(f=>{ let label = '';
          if (f.id) { const l = el.querySelector(`label[for="${CSS.escape(f.id)}"]`); if (l) label = l.innerText.trim(); }
          if (!label) { const l = f.closest('label'); if (l) label = l.innerText.trim(); }
          if (!label) { const p = f.closest('[data-testid], div'); const l = p && p.parentElement && p.parentElement.querySelector('label'); if (l) label = l.innerText.trim(); }
          return {tag:f.tagName.toLowerCase(), type:f.type, name:f.name, placeholder:f.placeholder, label, required:f.required, options: f.tagName==='SELECT' ? [...f.options].map(o=>o.text) : undefined}; });
        const btns = [...el.querySelectorAll('button, input[type=submit]')].map(b=>b.innerText||b.value).filter(Boolean);
        out.push({type:'form', style: boxStyle(el) || (el.parentElement && boxStyle(el.parentElement)), html: formClone(el), fields, buttons:btns, action: el.action||null, text: el.innerText.slice(0,2000), ...R(el)}); return; }
      if (t==='IFRAME') { if(!leafOk) return; out.push({type:'iframe', src: el.src, title: el.title, ...R(el)}); return; }
      if (t==='VIDEO') { if(!leafOk) return; out.push({type:'video', src: el.currentSrc||el.src, poster: el.poster, ...R(el)}); return; }
      if (t==='IMG') { if(!leafOk) return; const src = el.currentSrc || el.src; if (!src || src.startsWith('data:')) return; const r = R(el); if (r.w<16) return;
        const a = el.closest('a'); const s = cs(el);
        out.push({type:'img', src: absUrl(src), alt: el.alt||'', href: a? absUrl(a.getAttribute('href')||''):null, target: a? a.target:null, fit: s.objectFit, radius: s.borderRadius, ...r}); return; }
      const lab = el.matches('a, button, [role=button]') ? el : null;
      if (lab && (el.querySelector('[data-testid="stylablebutton-label"], [data-testid="buttonContent"], .wixui-button__label') || el.matches('[data-testid="linkElement"]') && el.closest('.wixui-button, [data-semantic-classname="button"]') || el.matches('.wixui-button, [data-testid="buttonElement"]'))) {
        const txt = el.innerText.trim(); const s = cs(el); const lbl = el.querySelector('[data-testid="stylablebutton-label"]') || el.querySelector('.wixui-button__label') || el.querySelector('span') || el; const ls = cs(lbl);
        let bg = s.backgroundColor, bc = s.borderColor, bw = s.borderWidth, br = s.borderRadius;
        // wix often paints the button on a child
        for (const c of el.querySelectorAll('*')) { const cc = cs(c); if (bg==='rgba(0, 0, 0, 0)' && cc.backgroundColor!=='rgba(0, 0, 0, 0)') bg = cc.backgroundColor; if (bw==='0px' && cc.borderWidth!=='0px') { bw=cc.borderWidth; bc=cc.borderColor; } if (br==='0px' && cc.borderRadius!=='0px') br=cc.borderRadius; }
        const host = el.closest('[data-semantic-classname="button"], .wixui-button') || el; const hs = cs(host);
        if (bg==='rgba(0, 0, 0, 0)' && hs.backgroundColor!=='rgba(0, 0, 0, 0)') bg = hs.backgroundColor; if (bw==='0px' && hs.borderWidth!=='0px') { bw=hs.borderWidth; bc=hs.borderColor; } if (br==='0px') br = hs.borderRadius;
        const href = el.getAttribute('href');
        if (txt || el.querySelector('img')) { out.push({type:'button', text: txt, href: href? absUrl(href): null, target: el.target||null, bg, color: ls.color, border: bw+' solid '+bc, radius: br, font: ls.fontFamily.split(',')[0].replace(/["']/g,''), size: ls.fontSize, weight: ls.fontWeight, ls: ls.letterSpacing, tt: ls.textTransform, ...R(host.getBoundingClientRect().width? host: el)}); return; }
      }
      if (/^H[1-6]$|^P$|^UL$|^OL$|^BLOCKQUOTE$|^TABLE$/.test(t)) { if(!leafOk) return; let html = clean(el, cs(el.parentElement)); const pa = el.closest('a[href]'); if (pa && !/<a /.test(html)) html = `<a href="${absUrl(pa.getAttribute('href'))}">${html}</a>`; const wrap = `<${t.toLowerCase()} style="${styleOf(el).replace(/"/g,"'")}">${html}</${t.toLowerCase()}>`; if (html.replace(/<[^>]+>/g,'').trim() || html.includes('<img')) out.push({type:'text', html: (t==='UL'||t==='OL'||t==='TABLE')? `<${t.toLowerCase()}>${html}</${t.toLowerCase()}>`: wrap, ...R(el)}); return; }
      const direct = [...el.childNodes].some(n=>n.nodeType===3 && n.textContent.trim());
      if (direct && leafOk) { const s = cs(el); const href = el.closest('a') ? el.closest('a').getAttribute('href') : null;
        const txt = el.innerText.trim(); if (txt) { const st = `font-size:${s.fontSize};line-height:${s.lineHeight};font-family:${s.fontFamily.split(',')[0].replace(/["']/g,'')};font-weight:${s.fontWeight};color:${s.color};${s.textAlign!=='start'?'text-align:'+s.textAlign+';':''}${s.textTransform!=='none'?'text-transform:'+s.textTransform+';':''}${s.fontStyle==='italic'?'font-style:italic;':''}${s.letterSpacing!=='normal'?'letter-spacing:'+s.letterSpacing+';':''}`;
          let inner = clean(el, s); if (href) inner = `<a href="${absUrl(href)}">${inner}</a>`;
          const clamped = (s.webkitLineClamp && s.webkitLineClamp!=='none') || el.scrollHeight > el.clientHeight + 4;
          const lhp = parseFloat(s.lineHeight) || parseFloat(s.fontSize)*1.3;
          out.push({type:'text', html:`<div style="${st}">${inner}</div>`, clampLines: clamped ? Math.max(1, Math.round(el.clientHeight / lhp)) : null, ...R(el)}); }
        return; }
      for (const c of el.children) walk(c, out);
    };
    walk(root, blocks);
    return blocks;
  }
  const main = document.querySelector('#PAGES_CONTAINER') || document.querySelector('main');
  let secs = [...main.querySelectorAll('section')].filter(s => !s.parentElement.closest('section'));
  // include top-level non-section children carrying content (some pages use strips)
  const sections = [];
  const covered = el => secs.some(s => s.contains(el) || el.contains(s));
  const extras = [...main.querySelectorAll(':scope > * > * > * > *, :scope > * > * > *')].filter(e => !covered(e) && vis(e) && e.innerText && e.innerText.trim());
  for (const s of secs) if (vis(s)) sections.push({id:s.id, ...R(s), bg: bgOf(s), blocks: blocksIn(s)});
  // fallback: whole main if no sections
  if (!sections.length) sections.push({id:'main', ...R(main), bg: bgOf(main), blocks: blocksIn(main)});
  else { const loose = []; for (const e of main.querySelectorAll('*')) {} }
  const footer = document.querySelector('footer');
  const header = document.querySelector('header');
  const hdr = header ? {rect:R(header), bg: bgOf(header), color: cs(header).backgroundColor, phone: [...header.querySelectorAll('a[href^="tel:"]')].map(a=>({href:a.getAttribute('href'), text:a.innerText.trim()})),
    logo: (header.querySelector('img')||{}).currentSrc || null, logoAlt: (header.querySelector('img')||{}).alt, blocks: blocksIn(header, el => el.matches('nav, [data-testid="dropdownMenu"], [id^="comp-"][class*="DropDownMenu"]'))} : null;
  const navItems = [];
  const nav = header && (header.querySelector('nav') || header.querySelector('ul'));
  if (nav) { const lis = nav.querySelectorAll(':scope > ul > li, :scope ul:first-of-type > li');
    for (const li of nav.querySelector('ul') ? nav.querySelector('ul').children : []) { const a = li.querySelector('a'); const sub = [...li.querySelectorAll('ul a, [data-testid="dropdownMenu"] a')].filter(x=>x!==a).map(x=>({text:x.textContent.trim(), href:absUrl(x.getAttribute('href')||'')}));
      navItems.push({text: (li.querySelector('p, span, a')||li).textContent.trim().split('\n')[0], href: a? absUrl(a.getAttribute('href')||''):null, sub}); } }
  const ftr = footer ? {...R(footer), bg: bgOf(footer), blocks: blocksIn(footer)} : null;
  const fixed = [...document.querySelectorAll('body *')].filter(e => { const p = cs(e).position; return (p==='fixed') && vis(e) && e.innerText && e.innerText.trim().length<200 && !e.closest('header'); }).map(e => ({text:e.innerText.trim(), html: e.outerHTML.slice(0,500), ...R(e)})).slice(0,10);
  const meta = n => (document.querySelector(`meta[name="${n}"], meta[property="${n}"]`)||{}).content || null;
  const canon = (document.querySelector('link[rel=canonical]')||{}).href || null;
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].map(s=>s.textContent);
  return {url: location.href, title: document.title, description: meta('description'), ogImage: meta('og:image'), ogTitle: meta('og:title'), canonical: canon, lang: document.documentElement.lang,
    bodyBg: cs(document.body).backgroundColor, pageW: document.documentElement.scrollWidth, pageH: document.documentElement.scrollHeight,
    header: hdr, nav: navItems, sections, footer: ftr, fixed, ld,
    iframes: [...document.querySelectorAll('iframe')].map(f=>({src:f.src, title:f.title, visible: vis(f), ...R(f)})),
    links: [...document.querySelectorAll('a[href]')].map(a=>absUrl(a.getAttribute('href')))};
}
