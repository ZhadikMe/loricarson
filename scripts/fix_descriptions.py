#!/usr/bin/env python3
"""
fix_descriptions.py — Generates and inserts meta descriptions for pages missing them.

Run from site root:
  cd d:/loricarson
  python scripts/fix_descriptions.py

Fixes root English pages only (lang pages handled separately via translate pipeline).
"""

import os, re, sys, calendar
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

SITE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_description(content: str) -> str | None:
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>',
                  content, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']\s*/?>',
                      content, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_text_snippet(content: str, max_words: int = 40) -> str:
    """Extract clean text from entry-content or entry-summary."""
    # Try entry-content first
    for marker in ['<div class="entry-content">', '<div class="entry-summary">']:
        start = content.find(marker)
        if start < 0:
            continue
        end = content.find('</article>', start)
        chunk = content[start:end if end > 0 else start + 3000]
        text = re.sub(r'<[^>]+>', ' ', chunk)
        text = re.sub(r'&[a-z#0-9]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()
        if len(words) >= 10:
            return ' '.join(words[:max_words])
    return ''


def parse_archive_date(fname: str):
    """m=YYYYMM.html → (Month_name, Year) e.g. ('February', '2008')"""
    m = re.match(r'm=(\d{4})(\d{2})\.html', fname)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return calendar.month_name[month], str(year)
    return None, None


def make_description(fname: str, content: str) -> str:
    """Generate a 120–155 char description for the page."""

    # ── Archive pages ──────────────────────────────────────────────────────────
    if fname.startswith('m='):
        month, year = parse_archive_date(fname)
        if month and year:
            return (f"Read Lori Carson's personal blog posts from {month} {year}. "
                    f"Intimate reflections on music, songwriting, and creative life from the acclaimed singer-songwriter.")

    # ── Special pages ──────────────────────────────────────────────────────────
    special = {
        'index.html':     "Lori Carson — acclaimed singer-songwriter and author. Explore her music, albums, novel The Original 1982, and personal blog. Official website.",
        'paged=2.html':   "More posts from Lori Carson's personal blog. Reflections on music, songwriting, creativity, and daily life from the acclaimed singer-songwriter.",
        'author=87.html': "Read all posts by Lori Carson — acclaimed singer-songwriter and author of The Original 1982. Personal reflections on music and creative life.",
        'cat=1.html':     "Browse Lori Carson's blog posts on life and music. Intimate reflections from the acclaimed singer-songwriter and author of The Original 1982.",
        '%09.html':       "Lori Carson — acclaimed singer-songwriter and author. Explore her music, albums, novel, and personal blog. Official website of loricarson.com.",
    }
    if fname in special:
        return special[fname]

    # ── Posts and pages — extract from content ────────────────────────────────
    h1 = re.findall(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
    h1_text = re.sub(r'<[^>]+>', '', h1[0]).strip() if h1 else ''
    snippet = extract_text_snippet(content, 35)

    # Page-specific overrides
    page_templates = {
        'page_id=844.html': ("Lori Carson's debut novel The Original 1982, published by William Morrow (HarperCollins). "
                             "A lyrical story praised for its spare prose and emotional depth."),
        'page_id=276.html': ("Explore Lori Carson's complete discography — from her debut Shelter (1990) to Another Year (2012). "
                             "Albums, songs, and music from the acclaimed indie singer-songwriter."),
        'page_id=471.html': None,  # fallback
        'page_id=271.html': ("News and press coverage of Lori Carson — acclaimed singer-songwriter and author. "
                             "Reviews, interviews, and updates on her music and novel The Original 1982."),
        'page_id=470.html': ("Shop Lori Carson's music and books. Buy Another Year (CD or digital) and her debut novel "
                             "The Original 1982. Support independent music directly."),
        'page_id=22.html':  ("Lori Carson's Everything I Touch Runs Wild (1997) — a landmark indie folk album. "
                             "Lush, seductive songwriting praised by critics worldwide. Available on CD and digital."),
    }
    if fname in page_templates and page_templates[fname]:
        return page_templates[fname]

    # Generic: use H1 + text snippet
    if snippet and h1_text:
        candidate = f"{h1_text} — {snippet}"
        # Trim to 155 chars at word boundary
        if len(candidate) > 155:
            candidate = candidate[:152].rsplit(' ', 1)[0] + '...'
        if len(candidate) >= 50:
            return candidate

    if snippet:
        candidate = snippet
        if len(candidate) > 155:
            candidate = candidate[:152].rsplit(' ', 1)[0] + '...'
        if len(candidate) >= 50:
            return candidate + ' — Lori Carson'

    if h1_text:
        return (f"{h1_text} — read on Lori Carson's official website. "
                f"Acclaimed singer-songwriter and author of The Original 1982.")

    return "Lori Carson — acclaimed singer-songwriter and author. Explore her music, albums, and personal blog."


def set_description(content: str, desc: str) -> tuple[str, bool]:
    """Insert or replace meta description. Returns (new_content, changed)."""
    # Escape desc for HTML attribute
    desc_safe = desc.replace('"', '&quot;').replace("'", '&#39;')

    existing = get_description(content)

    new_meta = f'<meta name="description" content="{desc_safe}">'

    if existing is not None:
        if len(existing) >= 50 and len(existing) <= 160:
            return content, False  # Already OK
        # Replace existing
        content, n = re.subn(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\'](\s*/?)>',
            new_meta,
            content, flags=re.IGNORECASE)
        if n == 0:
            content, _ = re.subn(
                r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']\s*/?>',
                new_meta,
                content, flags=re.IGNORECASE)
        # Also update og:description if present
        content = re.sub(
            r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\'](\s*/?)>',
            f'<meta property="og:description" content="{desc_safe}">',
            content, flags=re.IGNORECASE)
        return content, True
    else:
        # Insert before </head>
        head_close = content.find('</head>')
        if head_close < 0:
            head_close = content.find('<body')
        if head_close < 0:
            return content, False
        inject = f'{new_meta}\n<meta property="og:description" content="{desc_safe}">\n'
        return content[:head_close] + inject + content[head_close:], True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    fixed = 0
    skipped = 0

    for filepath in sorted(SITE.glob('*.html')):
        fname = filepath.name
        if fname in ('%09.html',) and False:  # can exclude if needed
            continue

        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"  ERROR reading {fname}: {e}")
            continue

        existing = get_description(content)
        if existing and 50 <= len(existing) <= 160:
            skipped += 1
            continue

        desc = make_description(fname, content)
        if not desc or len(desc) < 50:
            print(f"  SKIP (no desc generated): {fname}")
            continue

        new_content, changed = set_description(content, desc)
        if changed:
            filepath.write_text(new_content, encoding='utf-8')
            status = 'FIXED' if existing else 'ADDED'
            print(f"  {status}: {fname} ({len(desc)} chars)")
            fixed += 1
        else:
            skipped += 1

    print(f"\nDone: {fixed} fixed, {skipped} skipped")


if __name__ == '__main__':
    main()
