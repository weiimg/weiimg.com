"""Beehiiv CSV → weiimg.com blog importer.
Test mode: pass --slug to process only one post.
"""
import csv, sys, io, re, os, argparse, pathlib
from bs4 import BeautifulSoup, NavigableString

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
csv.field_size_limit(10**8)

CSV_PATH = r'D:\iCloudDrive\posts-2026-05-1120260511-2-og6f9p.csv'
ROOT = pathlib.Path(__file__).parent
BLOG_DIR = ROOT / 'blog'

ALLOWED_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li',
                'blockquote', 'img', 'a', 'strong', 'em', 'br', 'figure', 'figcaption'}


_HALF_TO_FULL = str.maketrans({
    ',': '，', '?': '？', '!': '！', ':': '：', ';': '；',
    '(': '（', ')': '）',
})


def has_cjk(s):
    return any('一' <= ch <= '鿿' for ch in s)


def fullwidth_punct(t):
    """Convert ASCII punctuation to full-width form, but only when the string
    contains CJK characters (i.e., skip pure-English titles)."""
    if not has_cjk(t):
        return t
    return t.translate(_HALF_TO_FULL)


def clean_title(t):
    t = re.sub(r'\s*[【\[]weiimg[】\]]\s*$', '', t).strip()
    return fullwidth_punct(t)


def slug_from_url(url):
    m = re.search(r'/p/([^/?#]+)', url)
    return m.group(1) if m else None


def extract_body(html, title):
    soup = BeautifulSoup(html, 'html.parser')
    # Beehiiv wraps the article body inside <div id="content-blocks"> typically,
    # else fall back to scanning all <p>/<h*>/<img>.
    container = soup.find(id='content-blocks') or soup.find('div', class_=re.compile(r'content', re.I)) or soup.body or soup

    # Collect block-level content elements in document order, excluding header/footer/nav
    # Beehiiv's article paragraphs typically sit in <td> with no class; the simplest robust
    # approach: grab all <p>, <h1-4>, <ul>, <ol>, <blockquote>, <img> directly from container
    # but skip those inside elements with class containing 'footer','header','social','rec','copyright','subscribe'.

    def in_chrome(node):
        for p in node.parents:
            cls = ' '.join(p.get('class', []) or [])
            idv = p.get('id', '') or ''
            blob = (cls + ' ' + idv).lower()
            if any(k in blob for k in ['footer', 'header', 'social', 'rec', 'copyright',
                                       'subscribe', 'unsubscribe', 'preheader', 'nav']):
                return True
            # Skip the title <h1> at the top (we'll add our own)
        return False

    out = []
    seen_first_h1 = False
    for el in container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote', 'img', 'figure']):
        if in_chrome(el):
            continue
        # Skip empty paragraphs (only whitespace or non-breaking space)
        text = el.get_text(strip=True).replace('\xa0', '').replace('​', '')
        if el.name == 'img':
            src = el.get('src', '')
            if not src:
                continue
            out.append(f'<img src="{src}" alt="{el.get("alt","")}">')
            continue
        if el.name == 'h1' and not seen_first_h1:
            # Skip the duplicate of post title rendered at top of email
            if text and clean_title(title) in text:
                seen_first_h1 = True
                continue
        if not text and el.name != 'figure':
            continue

        # Strip styling attrs, keep only essential
        for tag in el.find_all(True):
            attrs = {}
            if tag.name == 'a' and tag.get('href'):
                href = tag['href']
                # Strip beehiiv tracking
                href = re.sub(r'\?utm_[^"&]*', '', href)
                attrs['href'] = href
                attrs['target'] = '_blank'
                attrs['rel'] = 'noopener'
            if tag.name == 'img' and tag.get('src'):
                attrs['src'] = tag['src']
                if tag.get('alt'):
                    attrs['alt'] = tag['alt']
            tag.attrs = attrs

        # Promote element with cleared attrs on itself
        el.attrs = {k: v for k, v in el.attrs.items() if k in ('href', 'src', 'alt')}

        html_str = str(el)
        # Demote any nested h1 to h2
        html_str = re.sub(r'<(/?)h1\b', r'<\1h2', html_str)
        out.append(html_str)

    # Deduplicate consecutive identical blocks (Beehiiv sometimes renders mobile+desktop dupes)
    deduped = []
    for b in out:
        if deduped and deduped[-1] == b:
            continue
        deduped.append(b)

    # Merge fragmented <p>: Beehiiv stores each visual line as its own <p>.
    # If a <p> ends with non-terminal punctuation (，、；：) or no terminal at all,
    # merge it with the following <p>.
    TERMINAL = set('。！？.!?」』）)…』」')
    CONTINUE = set('，、；：,;:')

    def is_p(s):
        return s.startswith('<p>') or s.startswith('<p ')

    def p_text(s):
        return re.sub(r'<[^>]+>', '', s).strip().replace('\xa0', '').replace('​', '')

    def is_emphasis_only(html_block):
        """A <p> whose visible content is entirely inside <b>/<strong> (a headline-style emphasis line)."""
        inner = re.sub(r'^<p[^>]*>|</p>$', '', html_block).strip()
        stripped = re.sub(r'<(b|strong)\b[^>]*>.*?</\1>', '', inner, flags=re.DOTALL).strip()
        return stripped == '' and inner != ''

    merged = []
    for block in deduped:
        if merged and is_p(merged[-1]) and is_p(block):
            # Don't merge if either side is a bold-only emphasis line
            if is_emphasis_only(merged[-1]) or is_emphasis_only(block):
                merged.append(block)
                continue
            prev_text = p_text(merged[-1])
            if prev_text:
                last_char = prev_text[-1]
                if last_char in CONTINUE or last_char not in TERMINAL:
                    prev_inner = re.sub(r'^<p[^>]*>|</p>$', '', merged[-1])
                    curr_inner = re.sub(r'^<p[^>]*>|</p>$', '', block)
                    merged[-1] = f'<p>{prev_inner.strip()}{curr_inner.strip()}</p>'
                    continue
        merged.append(block)

    return '\n    '.join(merged)


PAGE_TPL = '''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<title>{title} — WEIIMG</title>
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/favicon.png">
<link rel="stylesheet" href="../../style.css?v=3">
<script>try{{var t=localStorage.getItem('weiimg-theme');if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
</head>
<body class="inner-page">

<nav class="nav">
  <a href="/" class="nav-logo">WEIIMG<span class="reg">*</span><span class="arrow-line"></span></a>
  <button class="theme-toggle" type="button" aria-label="Toggle dark mode">
    <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.07" y2="4.93"/></svg>
    <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
  </button>
  <div class="nav-items">
    <div class="nav-slide-wrap">
      <div class="nav-slide-inner">
        <div class="nav-row">
          <span class="has-dropdown">WORK</span>
          <a href="/about/">ABOUT</a>
          <a href="/blog/" class="active">BLOG</a>
        </div>
        <div class="nav-row">
          <a href="/design/">DESIGN</a>
          <a href="/film/">FILM</a>
          <a href="/shortform/">SHORTS</a>
        </div>
      </div>
    </div>
    <div class="nav-cta-wrap">
      <span class="nav-cta">FIND ME</span>
      <div class="findme-dropdown">
        <a href="mailto:hi@weiimg.com"><span class="fm-icon">✉</span>hi@weiimg.com</a>
        <a href="https://instagram.com/wei_img" target="_blank" rel="noopener noreferrer"><span class="fm-icon">📷</span>Instagram</a>
        <a href="https://threads.net/@wei_img" target="_blank" rel="noopener noreferrer"><span class="fm-icon">🧵</span>Threads</a>
      </div>
    </div>
  </div>
</nav>

<aside class="blog-toc" aria-label="Table of contents">{toc}</aside>

<main>
  <div class="article-back"><a href="/blog/">&larr; 返回 Blog</a></div>

  <div class="blog-article-header">
    <h1>{title}</h1>
    <div class="blog-article-meta">{date} · WEIIMG</div>
  </div>

  <div class="blog-article-body">
    {body}
  </div>
</main>

<footer class="contact">
  <div class="contact-label">Let's collaborate!</div>
  <div class="contact-email"><a href="mailto:hi@weiimg.com">hi@weiimg.com</a></div>
  <a href="mailto:hi@weiimg.com" class="contact-cta">FIND ME</a>
  <div class="contact-copyright">&copy; 2026 林晉維 — weiimg.com</div>
</footer>

<script>
(() => {{
  const btn = document.querySelector('.theme-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {{
    const cur = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = cur;
    try {{ localStorage.setItem('weiimg-theme', cur); }} catch(e) {{}}
  }});
}})();
(() => {{
  document.querySelectorAll('.blog-article-body img').forEach(img => {{
    if (img.parentElement.classList.contains('photo-zoom')) return;
    const wrap = document.createElement('span');
    wrap.className = 'photo-zoom';
    img.parentNode.insertBefore(wrap, img);
    wrap.appendChild(img);
    let raf = 0;
    wrap.addEventListener('mousemove', e => {{
      const r = wrap.getBoundingClientRect();
      const dx = ((e.clientX - r.left) / r.width - 0.5) * r.width * 0.08;
      const dy = ((e.clientY - r.top) / r.height - 0.5) * r.height * 0.08;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {{
        img.style.transform = `scale(1.2) translate(${{dx}}px, ${{dy}}px)`;
      }});
    }});
    wrap.addEventListener('mouseleave', () => {{
      cancelAnimationFrame(raf);
      wrap.classList.add('leaving');
      img.style.transform = '';
      setTimeout(() => wrap.classList.remove('leaving'), 520);
    }});
  }});
}})();
(() => {{
  const wrap = document.querySelector('.nav-slide-wrap');
  const trigger = wrap && wrap.querySelector('.has-dropdown');
  if (!wrap || !trigger) return;
  let timer;
  const show = () => {{ clearTimeout(timer); wrap.classList.add('open'); }};
  const hide = () => {{ timer = setTimeout(() => wrap.classList.remove('open'), 250); }};
  trigger.addEventListener('mouseenter', show);
  wrap.addEventListener('mouseleave', hide);
  wrap.querySelectorAll('.nav-row:last-child a').forEach(a => {{
    a.addEventListener('mouseenter', show);
  }});
}})();
const logo = document.querySelector('.nav-logo');
const line = logo && logo.querySelector('.arrow-line');
const navItems = document.querySelector('.nav-items');
if (logo && line && navItems) {{
  function setArrowWidth() {{
    const lR = logo.getBoundingClientRect(), nR = navItems.getBoundingClientRect();
    line.style.width = Math.max(0, nR.left - lR.right - 12) + 'px';
  }}
  logo.addEventListener('mouseenter', () => {{ setArrowWidth(); logo.classList.remove('arrow-out'); logo.classList.add('arrow-in'); }});
  logo.addEventListener('mouseleave', () => {{ logo.classList.remove('arrow-in'); logo.classList.add('arrow-out'); line.addEventListener('transitionend', () => logo.classList.remove('arrow-out'), {{ once: true }}); }});
}}
</script>
<script>
(() => {{
  const links = Array.from(document.querySelectorAll('.blog-toc a'));
  if (!links.length) return;
  const targets = links.map(a => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
  const easeInOut = t => t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2)/2;
  function smoothScrollTo(el) {{
    const targetY = el.getBoundingClientRect().top + window.pageYOffset - 80;
    const startY = window.pageYOffset;
    const dist = targetY - startY;
    const duration = 700;
    const startTime = performance.now();
    function step(now) {{
      const t = Math.min((now - startTime) / duration, 1);
      window.scrollTo(0, startY + dist * easeInOut(t));
      if (t < 1) requestAnimationFrame(step);
    }}
    requestAnimationFrame(step);
  }}
  links.forEach(a => a.addEventListener('click', e => {{
    const id = a.getAttribute('href').slice(1);
    const el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    history.pushState(null, '', '#' + id);
    smoothScrollTo(el);
  }}));
  function updateActive() {{
    const scrollY = window.pageYOffset + 120;
    let activeIdx = 0;
    for (let i = 0; i < targets.length; i++) {{
      if (targets[i].offsetTop <= scrollY) activeIdx = i;
    }}
    links.forEach((a, i) => a.classList.toggle('active', i === activeIdx));
  }}
  window.addEventListener('scroll', updateActive, {{ passive: true }});
  updateActive();
}})();
</script>
<script src="/nav.js?v=3"></script>
</body>
</html>
'''


def build_toc(body_html):
    """Find every <h2>...</h2>, assign id=s-N, return (body_with_ids, toc_html)."""
    toc_items = []
    counter = [0]

    def repl(m):
        counter[0] += 1
        sid = f's-{counter[0]}'
        inner = m.group(1)
        # Strip nested tags from heading text for TOC label
        label = re.sub(r'<[^>]+>', '', inner).strip()
        toc_items.append((sid, label))
        return f'<h2 id="{sid}">{inner}</h2>'

    body_with_ids = re.sub(r'<h2>(.*?)</h2>', repl, body_html, flags=re.DOTALL)

    if not toc_items:
        return body_with_ids, ''

    items = '\n      '.join(
        f'<li><a href="#{sid}"><span>{label}</span></a></li>' for sid, label in toc_items
    )
    toc_html = '<ul>\n      ' + items + '\n    </ul>'
    return body_with_ids, toc_html


def build_page(post):
    title = clean_title(post['web_title'])
    slug = slug_from_url(post['url'])
    if not slug:
        return None
    date = post['created_at'][:10].replace('-', '.')
    body = extract_body(post['content_html'], post['web_title'])
    body, toc = build_toc(body)
    desc = (post.get('web_subtitle') or title).strip() or title
    return slug, PAGE_TPL.format(title=title, date=date, body=body, desc=desc, toc=toc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug', help='Process only the post whose URL slug matches')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    with open(CSV_PATH, encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r['status'] == 'confirmed']

    if args.list:
        for r in rows:
            print(slug_from_url(r['url']), '|', clean_title(r['web_title']))
        return

    if args.slug:
        rows = [r for r in rows if slug_from_url(r['url']) == args.slug]
        if not rows:
            print('No match for slug:', args.slug)
            return

    written = []
    for r in rows:
        result = build_page(r)
        if not result:
            continue
        slug, html = result
        out_dir = BLOG_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'index.html').write_text(html, encoding='utf-8')
        print('wrote', out_dir / 'index.html', '(', len(html), 'bytes )')
        written.append({
            'slug': slug,
            'title': clean_title(r['web_title']),
            'date': r['created_at'][:10],
        })

    if not args.slug:
        write_index(written)


INDEX_TPL = '''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="WEIIMG Blog — 品牌經營、內容策略、短影音觀點分享。">
<title>Blog — WEIIMG</title>
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/favicon.png">
<link rel="stylesheet" href="../style.css?v=3">
<script>try{{var t=localStorage.getItem('weiimg-theme');if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
</head>
<body class="inner-page">

<nav class="nav">
  <a href="/" class="nav-logo">WEIIMG<span class="reg">*</span><span class="arrow-line"></span></a>
  <button class="theme-toggle" type="button" aria-label="Toggle dark mode">
    <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.07" y2="4.93"/></svg>
    <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
  </button>
  <div class="nav-items">
    <div class="nav-slide-wrap">
      <div class="nav-slide-inner">
        <div class="nav-row">
          <span class="has-dropdown">WORK</span>
          <a href="/about/">ABOUT</a>
          <a href="/blog/" class="active">BLOG</a>
        </div>
        <div class="nav-row">
          <a href="/design/">DESIGN</a>
          <a href="/film/">FILM</a>
          <a href="/shortform/">SHORTS</a>
        </div>
      </div>
    </div>
    <div class="nav-cta-wrap">
      <span class="nav-cta">FIND ME</span>
      <div class="findme-dropdown">
        <a href="mailto:hi@weiimg.com"><span class="fm-icon">✉</span>hi@weiimg.com</a>
        <a href="https://instagram.com/wei_img" target="_blank" rel="noopener noreferrer"><span class="fm-icon">📷</span>Instagram</a>
        <a href="https://threads.net/@wei_img" target="_blank" rel="noopener noreferrer"><span class="fm-icon">🧵</span>Threads</a>
      </div>
    </div>
  </div>
</nav>

<main>
  <div class="blog-list">
    <div class="blog-en">weiimg's newsletter</div>
    <h1>Blog</h1>
    {rows}
  </div>
</main>

<footer class="contact">
  <div class="contact-label">Let's collaborate!</div>
  <div class="contact-email"><a href="mailto:hi@weiimg.com">hi@weiimg.com</a></div>
  <a href="mailto:hi@weiimg.com" class="contact-cta">FIND ME</a>
  <div class="contact-copyright">&copy; 2026 林晉維 — weiimg.com</div>
</footer>

<script>
(() => {{
  const btn = document.querySelector('.theme-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {{
    const cur = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = cur;
    try {{ localStorage.setItem('weiimg-theme', cur); }} catch(e) {{}}
  }});
}})();
(() => {{
  document.querySelectorAll('.blog-article-body img').forEach(img => {{
    if (img.parentElement.classList.contains('photo-zoom')) return;
    const wrap = document.createElement('span');
    wrap.className = 'photo-zoom';
    img.parentNode.insertBefore(wrap, img);
    wrap.appendChild(img);
    let raf = 0;
    wrap.addEventListener('mousemove', e => {{
      const r = wrap.getBoundingClientRect();
      const dx = ((e.clientX - r.left) / r.width - 0.5) * r.width * 0.08;
      const dy = ((e.clientY - r.top) / r.height - 0.5) * r.height * 0.08;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {{
        img.style.transform = `scale(1.2) translate(${{dx}}px, ${{dy}}px)`;
      }});
    }});
    wrap.addEventListener('mouseleave', () => {{
      cancelAnimationFrame(raf);
      wrap.classList.add('leaving');
      img.style.transform = '';
      setTimeout(() => wrap.classList.remove('leaving'), 520);
    }});
  }});
}})();
(() => {{
  const wrap = document.querySelector('.nav-slide-wrap');
  const trigger = wrap && wrap.querySelector('.has-dropdown');
  if (!wrap || !trigger) return;
  let timer;
  const show = () => {{ clearTimeout(timer); wrap.classList.add('open'); }};
  const hide = () => {{ timer = setTimeout(() => wrap.classList.remove('open'), 250); }};
  trigger.addEventListener('mouseenter', show);
  wrap.addEventListener('mouseleave', hide);
  wrap.querySelectorAll('.nav-row:last-child a').forEach(a => {{
    a.addEventListener('mouseenter', show);
  }});
}})();
</script>
<script src="/nav.js?v=3"></script>
</body>
</html>
'''


def write_index(posts):
    posts_sorted = sorted(posts, key=lambda p: p['date'], reverse=True)
    rows = '\n    '.join(
        '<a href="/blog/{slug}/" class="blog-row">\n'
        '      <div class="blog-date">{date_disp}</div>\n'
        '      <div class="blog-title">{title}</div>\n'
        '    </a>'.format(
            slug=p['slug'],
            date_disp=p['date'].replace('-', '.'),
            title=p['title'],
        )
        for p in posts_sorted
    )
    out = INDEX_TPL.format(rows=rows)
    (BLOG_DIR / 'index.html').write_text(out, encoding='utf-8')
    print('wrote', BLOG_DIR / 'index.html', f'({len(posts_sorted)} posts)')


if __name__ == '__main__':
    main()
