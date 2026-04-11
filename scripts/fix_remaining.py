#!/usr/bin/env python3
"""
fix_remaining.py — fixes the remaining 9 SEO issues on loricarson root pages.
Run from site root: python scripts/fix_remaining.py
"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(fname):
    return open(os.path.join(SITE, fname), encoding='utf-8', errors='ignore').read()


def write(fname, content):
    with open(os.path.join(SITE, fname), 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  ✓ {fname}')


# ── 1. Shorten long titles ─────────────────────────────────────────────────────

TITLE_FIXES = {
    '%09.html':       'Lori Carson — Life and Music Blog',
    'paged=2.html':   'Lori Carson — Life and Music Blog | Page 2',
    'p=1268.html':    'I Wonder Which of All These Things | Lori Carson',
    'page_id=22.html': 'Everything I Touch Runs Wild (1997) | Lori Carson',
}

print('=== 1. Fixing long titles ===')
for fname, new_title in TITLE_FIXES.items():
    html = read(fname)
    new_html = re.sub(r'<title>[^<]+</title>', f'<title>{new_title}</title>', html, count=1)
    if new_html != html:
        write(fname, new_html)
    else:
        print(f'  ✗ {fname}: no change (title pattern not found)')


# ── 2. Add archive intro/outro to index.html (June 2014 archive saved as index) ──

ARCHIVE_INTRO = '<p class="archive-intro">Lori Carson is a critically acclaimed singer-songwriter and author whose music has earned praise from NPR, WNYC, and critics worldwide. This archive brings together her personal blog entries from this period — intimate reflections on music, creativity, daily life, and the inner world of an artist. Carson writes with the same directness and emotional honesty that defines her music: spare, lyrical, and deeply felt. Browse the posts below to follow her thoughts and experiences during this time.</p>'

ARCHIVE_OUTRO = '<p class="archive-outro">Lori Carson\'s blog has always been an extension of her artistic practice — a place where songs begin, where ideas are tested, and where the boundary between music and writing dissolves. Each entry offers a glimpse into the creative life of one of independent music\'s most distinctive voices. Her albums include <em>Shelter</em>, <em>Where It Goes</em>, <em>Everything I Touch Runs Wild</em>, and <em>Another Year</em>. Her debut novel, <em>The Original 1982</em>, was published by William Morrow (HarperCollins).</p>'

print('\n=== 2. Adding archive intro/outro to index.html ===')
html = read('index.html')
if 'archive-intro' not in html:
    h1_end = re.search(r'</h1>', html, re.IGNORECASE)
    if h1_end:
        html = html[:h1_end.end()] + '\n' + ARCHIVE_INTRO + html[h1_end.end():]
        print('  Intro added')
    else:
        print('  ✗ No </h1> found')
else:
    print('  Intro already present')

if 'archive-outro' not in html:
    main_close = re.search(r'</div>\s*<!--[^>]*#main[^>]*-->', html, re.IGNORECASE)
    if main_close:
        html = html[:main_close.start()] + ARCHIVE_OUTRO + '\n' + html[main_close.start():]
        print('  Outro added')
    else:
        articles = list(re.finditer(r'</article>', html, re.IGNORECASE))
        if articles:
            pos = articles[-1].end()
            html = html[:pos] + '\n' + ARCHIVE_OUTRO + html[pos:]
            print('  Outro added (after last article)')
else:
    print('  Outro already present')

write('index.html', html)


# ── 3. Add noindex to p=1106.html (short 87-word post) ────────────────────────

print('\n=== 3. Noindexing short post p=1106.html ===')
html = read('p=1106.html')
if 'name="robots"' not in html.lower():
    noindex = '<meta name="robots" content="noindex, follow">'
    head_close = html.find('</head>')
    if head_close > 0:
        html = html[:head_close] + noindex + '\n' + html[head_close:]
        write('p=1106.html', html)
    else:
        print('  ✗ No </head> found')
else:
    print('  Robots meta already present')


# ── 4. Fix duplicate H1 in page_id=470.html ───────────────────────────────────

print('\n=== 4. Fixing duplicate H1 in page_id=470.html ===')
html = read('page_id=470.html')
# The duplicate is <h1 align="center"><i>Another Year</i></h1> — convert to H2
html = re.sub(
    r'<h1(\s+align="center"[^>]*)>(.*?)</h1>',
    r'<h2\1>\2</h2>',
    html, count=1, flags=re.DOTALL | re.IGNORECASE
)
h1s = re.findall(r'<h1[^>]*>', html, re.IGNORECASE)
print(f'  H1 count after fix: {len(h1s)}')


# ── 5. Add content to thin special pages ───────────────────────────────────────

EXTRA_CONTENT = {
    'page_id=276.html': '''
<div class="seo-extra-2">
<p>Throughout her career, Lori Carson has collaborated with producers including T Bone Burnett and Craig Street, and her music has been featured in film and television soundtracks. Her songs have been covered by other artists and her influence is felt across the singer-songwriter landscape. Streaming and download options are available through major digital platforms including Spotify, Apple Music, and Bandcamp. Physical copies of selected albums can be ordered through her store.</p>
</div>''',

    'page_id=43.html': '''
<div class="seo-extra-2">
<p>Lori Carson welcomes messages from fans, journalists, and collaborators. Whether you are interested in discussing her music, her novel <em>The Original 1982</em>, or potential collaboration, please use the contact information above. Response times may vary depending on touring and recording schedules. For media kits, high-resolution photos, or biographical materials, please specify your publication and deadline in your message.</p>
</div>''',

    'page_id=470.html': '''
<div class="seo-extra-2">
<p>Purchasing directly from Lori Carson's store ensures that the maximum portion of each sale supports her work as an independent artist. Digital downloads are delivered immediately after purchase. Physical CDs are shipped within 3–5 business days. For international orders or bulk purchases, please use the contact page to inquire about shipping options. All purchases help fund future recordings and live performances.</p>
</div>''',
}

print('\n=== 5. Adding content to thin special pages ===')
for fname, extra in EXTRA_CONTENT.items():
    html = read(fname) if fname != 'page_id=470.html' else html  # reuse already-modified for 470
    if 'seo-extra-2' in html:
        print(f'  {fname}: extra-2 already present')
        continue
    # Insert before closing </div> of entry-content
    ec_end = html.rfind('</div>', 0, html.find('</div><!-- #main -->') if '</div><!-- #main -->' in html else len(html))
    # Better: find entry-content div and insert before its close
    ec_match = re.search(r'<div class="entry-content">', html, re.IGNORECASE)
    if ec_match:
        # Find the matching close - look for seo-extra div or just inject before #main
        main_close = re.search(r'</div>\s*<!--[^>]*#main[^>]*-->', html, re.IGNORECASE)
        if main_close:
            html = html[:main_close.start()] + extra + '\n' + html[main_close.start():]
            write(fname, html)
        else:
            print(f'  ✗ {fname}: no #main close found')
    else:
        print(f'  ✗ {fname}: no entry-content found')


print('\n=== Done ===')
