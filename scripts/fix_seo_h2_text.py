#!/usr/bin/env python3
"""
fix_seo_h2_text.py — Adds H2 headings + expands thin pages

Run from site root:
  cd d:/loricarson
  python scripts/fix_seo_h2_text.py

Phases:
  1. Translate all texts using Groq (saves cache to scripts/seo_translations.json)
  2. Apply H2 to 24 pages × 23 versions
  3. Add intro/outro to archive pages × 23 versions
  4. Expand thin page_id pages × 23 versions
"""

import os, re, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')
import requests

SITE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seo_translations.json')
GROQ_KEY  = os.environ.get("GROQ_API_KEY", "")
GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

LANGS = ['ar', 'cs', 'de', 'el', 'es', 'fi', 'fr', 'hi', 'it', 'ja', 'ko',
         'nl', 'pl', 'pt', 'ro', 'ru', 'sk', 'sv', 'tr', 'uk', 'zh']

LANG_NAMES = {
    'ar': 'Arabic', 'cs': 'Czech', 'de': 'German', 'el': 'Greek',
    'es': 'Spanish', 'fi': 'Finnish', 'fr': 'French', 'hi': 'Hindi',
    'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean', 'nl': 'Dutch',
    'pl': 'Polish', 'pt': 'Portuguese', 'ro': 'Romanian', 'ru': 'Russian',
    'sk': 'Slovak', 'sv': 'Swedish', 'tr': 'Turkish', 'uk': 'Ukrainian',
    'zh': 'Chinese'
}

# ── H2 for 24 pages (English) ─────────────────────────────────────────────────
H2_PAGES = {
    'p=1088.html':     'Thoughts on Solitude and Music',
    'p=1106.html':     'A Village by the Sea',
    'p=1173.html':     'On Living with Purpose',
    'p=1190.html':     'Reflections on Life and Experience',
    'p=1205.html':     'Finding Balance in Uncertain Times',
    'p=1239.html':     'Writing for Connection',
    'p=1253.html':     'A Journey of Healing',
    'p=1268.html':     'Questions of Meaning',
    'p=1290.html':     'Seasons and Songs',
    'p=1313.html':     'Daily Pleasures',
    'page_id=2.html':  'About Lori Carson',
    'page_id=8.html':  'About the Album',
    'page_id=17.html': 'About the Album',
    'page_id=20.html': 'About the Album',
    'page_id=22.html': 'About the Album',
    'page_id=33.html': 'About the Album',
    'page_id=35.html': 'About the Album',
    'page_id=37.html': 'About the Album',
    'page_id=43.html': 'Get in Touch',
    'page_id=271.html':'Latest News',
    'page_id=276.html':'Albums and Music',
    'page_id=470.html':'Shop Music and Books',
    'page_id=496.html':'About the Album',
    'page_id=844.html':'About the Novel',
}

# ── Archive intro/outro ───────────────────────────────────────────────────────
ARCHIVE_INTRO_EN = '<p class="archive-intro">Lori Carson is a critically acclaimed singer-songwriter and author whose music has earned praise from NPR, WNYC, and critics worldwide. This archive brings together her personal blog entries from this period — intimate reflections on music, creativity, daily life, and the inner world of an artist. Carson writes with the same directness and emotional honesty that defines her music: spare, lyrical, and deeply felt. Browse the posts below to follow her thoughts and experiences during this time.</p>'

ARCHIVE_OUTRO_EN = '<p class="archive-outro">Lori Carson\'s blog has always been an extension of her artistic practice — a place where songs begin, where ideas are tested, and where the boundary between music and writing dissolves. Each entry offers a glimpse into the creative life of one of independent music\'s most distinctive voices. Her albums include <em>Shelter</em>, <em>Where It Goes</em>, <em>Everything I Touch Runs Wild</em>, and <em>Another Year</em>. Her debut novel, <em>The Original 1982</em>, was published by William Morrow (HarperCollins).</p>'

# ── Thin page expansions ──────────────────────────────────────────────────────
THIN_PAGE_EXTRAS = {
    'page_id=276.html': '<h3>Complete Discography</h3>\n<p>Lori Carson\'s musical journey spans over two decades of critically acclaimed recordings. Her debut album <em>Shelter</em> (1990) introduced her intimate songwriting style, followed by the indie classic <em>Where It Goes</em> (1995), produced by Anton Fier, and the celebrated <em>Everything I Touch Runs Wild</em> (1997). Her Golden Palominos collaborations showcased her versatility as a vocalist. <em>Stars</em> (1999) and <em>Stolen Beauty</em> (2003) continued her artistic evolution, while <em>House in the Weeds</em> (2001) and <em>The Finest Thing</em> (2004, 2005) demonstrate her commitment to craft. Her most recent studio album <em>Another Year</em> (2012) marks a triumphant return, capturing the emotional depth and lyrical sophistication that have defined her career. Lori\'s music has appeared in films and television, reaching audiences around the world. Each album represents a distinct chapter in an ongoing artistic conversation about love, loss, memory, and hope.</p>',

    'page_id=470.html': '<h3>Available Now</h3>\n<p>Support independent music by purchasing directly from Lori Carson\'s store. <em>Another Year</em> (2012) is available as a CD or digital download — a deeply personal album that NPR called "gorgeous" and critics praised for its lyrical sophistication and emotional intimacy. Each purchase supports Lori\'s ongoing creative work and independent music-making.</p>\n<p>Lori Carson\'s debut novel <em>The Original 1982</em>, published by William Morrow (HarperCollins), is also available. This lyrical, evocative story has earned praise for its spare prose and emotional resonance. A perfect companion to her music for fans who want to explore her full artistic vision. For bulk orders, licensing inquiries, or special requests, please use the <a href="/page_id=43.html">contact page</a>. Thank you for supporting independent art.</p>',

    'page_id=43.html': '<h3>Booking and Licensing</h3>\n<p>For live performance bookings, press inquiries, or licensing Lori Carson\'s music for film, television, or other media, please reach out using the contact information above. Lori\'s music has been featured in major film and television productions, and her catalog is available for licensing through appropriate channels.</p>\n<p>Fans are always welcome to write with thoughts about the music, the novel, or the blog. For the most up-to-date information on performances, new releases, and news, follow Lori Carson\'s blog at loricarson.com. New posts appear periodically, sharing her reflections on music, writing, and life.</p>',

    'page_id=20.html': '<p><em>Stars</em> was Lori Carson\'s last release for Restless Records, produced in Seattle and New York City with Layng Martine III and Joe Ferla. The standout track "Take Your Time" became one of Carson\'s most licensed songs, appearing in numerous films and television programs. Its timeless quality — a meditation on patience and presence — represents everything that makes Carson\'s songwriting so enduringly powerful. The album demonstrates her gift for melody and her unflinching honesty as a lyricist, qualities that have earned her a devoted following over decades of recording and performing.</p>',

    'page_id=271.html': '<h3>Press and Critical Reception</h3>\n<p>Lori Carson\'s work has received widespread critical acclaim throughout her career. Her debut novel <em>The Original 1982</em> earned praise from NPR, WNYC\'s Soundcheck, MSN, and numerous literary publications for its spare, lyrical prose. Music critics have consistently highlighted her singular voice and her ability to communicate profound emotion through minimalist arrangements. Her album <em>Another Year</em> was featured in NPR\'s Summer Reads list, reviewed by Volume 1 Brooklyn, and received extensive coverage across independent music press worldwide. Live performances at venues including Book Soup in Los Angeles have introduced her work to new audiences, while longtime fans continue to follow her personal blog for updates on new projects and her ongoing creative life.</p>',

    'page_id=496.html': '<p>Recorded with meticulous attention to texture and space, <em>Another Year</em> features Carson\'s most mature songwriting, drawing on years of experience and hard-won wisdom. The album\'s production — spare, intimate, and precise — allows her voice to carry the full weight of each lyrical moment. Songs like "Drive Away" and "Undercurrent" demonstrate her ability to find universal truths in deeply personal experience. Released in 2012 through Blue Kitchen Music and United for Opportunity, <em>Another Year</em> received immediate critical acclaim, with reviewers praising its emotional honesty and sonic sophistication. For longtime fans, it represented a welcome return; for new listeners, it served as an ideal introduction to one of independent music\'s most distinctive voices.</p>',

    'page_id=33.html': '<p>Produced by the legendary Anton Fier, <em>Where It Goes</em> established Lori Carson as a major voice in independent music. The album\'s opening track, "You Won\'t Fall," became the first of her songs licensed for film, appearing in Bernardo Bertolucci\'s <em>Stealing Beauty</em>. This placement introduced her music to international audiences and cemented her reputation as a songwriter capable of conveying deep emotional truth with quiet precision. The album\'s production is a masterclass in restraint — every element serves the song. <em>Where It Goes</em> remains one of the defining albums of 1990s independent folk, a record that sounds as fresh and immediate today as it did upon its release.</p>',

    'page_id=22.html': '<p>Released in 1997, <em>Everything I Touch Runs Wild</em> represents a peak of Lori Carson\'s early career — a collection of songs so perfectly realized that critics struggled to find adequate superlatives. Available as both a standard disc and an expanded two-CD set featuring remixes, the album demonstrates Carson\'s full range as a songwriter, arranger, and vocalist. The title track and "Waking to the Dream of You" have become staples of her live performances, while deeper cuts reward repeated listening with hidden nuances. The remix disc, featuring interpretations by leading electronic producers, demonstrated the adaptability of Carson\'s songwriting. Decades after its release, <em>Everything I Touch Runs Wild</em> continues to attract new listeners who discover in it a timeless exploration of love, longing, and creative passion.</p>',

    'page_id=37.html': '<p><em>Stolen Beauty</em> (2003) marks a significant chapter in Lori Carson\'s career, showcasing her continued evolution as an artist and songwriter. The album arrives at a moment of artistic maturity, with Carson drawing on a decade of experience to craft songs of uncommon depth and resonance. The production, carefully balanced between intimacy and ambition, creates space for her voice to explore the full spectrum of human emotion. The album title reflects one of Carson\'s central artistic concerns: the ways in which beauty emerges from unexpected places and fleeting moments. Each track captures a different facet of this theme, moving from moments of quiet introspection to passages of genuine emotional power. <em>Stolen Beauty</em> demonstrates why Lori Carson has remained one of independent music\'s most compelling and enduring voices.</p>',
}

# ── Groq API ──────────────────────────────────────────────────────────────────

def groq_call(messages, max_tokens=4000, retries=5):
    """Call Groq with exponential backoff on 429."""
    delay = 3
    for attempt in range(retries):
        try:
            r = requests.post(GROQ_URL,
                headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'},
                json={'model': GROQ_MODEL, 'messages': messages, 'temperature': 0.1, 'max_tokens': max_tokens},
                timeout=90)
            if r.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f" [429, wait {wait}s]", end='', flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content'].strip()
        except requests.exceptions.HTTPError as e:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))
    raise RuntimeError("Max retries exceeded")


def translate_list(texts, lang):
    """Translate a numbered list of texts to lang."""
    lang_name = LANG_NAMES[lang]
    numbered = '\n'.join(f'{i+1}. {t}' for i, t in enumerate(texts))
    system = (f"Translate the following items to {lang_name}. "
              f"Return ONLY the translations, numbered the same way, one per line. "
              f"Do not add explanations or extra text.")
    result = groq_call([
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': numbered}
    ])
    out = []
    for line in result.split('\n'):
        line = line.strip()
        if re.match(r'^\d+[.)]\s*', line):
            line = re.sub(r'^\d+[.)]\s*', '', line)
        if line:
            out.append(line)
    while len(out) < len(texts):
        out.append(texts[len(out)])
    return out[:len(texts)]


def translate_html(html, lang):
    """Translate text inside HTML to lang, preserving tags."""
    lang_name = LANG_NAMES[lang]
    system = (f"You are a professional HTML translator. Translate the visible text in the following HTML to {lang_name}. "
              f"Preserve ALL HTML tags, attributes, class names, and href values exactly as-is. "
              f"Only translate the visible text content. Return only the translated HTML.")
    return groq_call([
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': html}
    ], max_tokens=2000)


# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ── File patching ─────────────────────────────────────────────────────────────

def insert_h2(content, h2_text):
    """Insert H2 right after <div class="entry-content"> opening tag."""
    ec_start = content.find('<div class="entry-content">')
    if ec_start < 0:
        return content, False
    # Check if H2 already present close to entry-content opening
    window = content[ec_start:ec_start+500]
    if '<h2 class="entry-heading"' in window:
        return content, False
    insert_pos = content.find('>', ec_start) + 1
    h2_tag = f'\n<h2 class="entry-heading">{h2_text}</h2>'
    return content[:insert_pos] + h2_tag + content[insert_pos:], True


def insert_archive_text(content, intro_html, outro_html):
    """Add intro after H1 and outro before navigation on archive pages."""
    changed = False
    # Add intro if missing
    if 'archive-intro' not in content:
        h1_end = re.search(r'</h1>', content, re.IGNORECASE)
        if not h1_end:
            return content, False
        content = content[:h1_end.end()] + '\n' + intro_html + content[h1_end.end():]
        changed = True
    # Add outro if missing
    if 'archive-outro' not in content:
        nav_match = re.search(r'<nav[^>]*class="[^"]*navigation[^"]*"', content, re.IGNORECASE)
        if nav_match:
            content = content[:nav_match.start()] + outro_html + '\n' + content[nav_match.start():]
            changed = True
        else:
            main_close = re.search(r'</div>\s*<!--[^>]*#main[^>]*-->', content, re.IGNORECASE)
            if main_close:
                content = content[:main_close.start()] + outro_html + '\n' + content[main_close.start():]
                changed = True
            else:
                articles = list(re.finditer(r'</article>', content, re.IGNORECASE))
                if articles:
                    pos = articles[-1].end()
                    content = content[:pos] + '\n' + outro_html + content[pos:]
                    changed = True
    return content, changed


def append_page_extra(content, extra_html):
    """Append extra HTML before closing </div> of entry-content."""
    if 'seo-extra' in content:
        return content, False
    ec_start = content.find('<div class="entry-content">')
    if ec_start < 0:
        return content, False
    # Find the closing div of entry-content (first </div> after a reasonable offset)
    close_pos = content.find('</div>', ec_start + 100)
    if close_pos < 0:
        return content, False
    wrapped = f'<div class="seo-extra">{extra_html}</div>\n'
    return content[:close_pos] + wrapped + content[close_pos:], True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cache = load_cache()

    # ── Phase 1: Collect all translations ────────────────────────────────────
    print("=== Phase 1: Building translation cache ===")

    en_h2_texts = list(H2_PAGES.values())
    changed = False

    # H2 headings per language
    if 'h2_headings' not in cache:
        cache['h2_headings'] = {'en': en_h2_texts}
    for lang in LANGS:
        if lang in cache.get('h2_headings', {}):
            print(f"  H2/{lang}: cached")
            continue
        print(f"  H2/{lang}...", end=' ', flush=True)
        try:
            result = translate_list(en_h2_texts, lang)
            cache.setdefault('h2_headings', {})[lang] = result
            print(f"OK")
            changed = True
            save_cache(cache)
        except Exception as e:
            print(f"SKIP ({e})")
        time.sleep(2)

    # Archive intro per language
    if 'archive_intro' not in cache:
        cache['archive_intro'] = {'en': ARCHIVE_INTRO_EN}
    for lang in LANGS:
        if lang in cache.get('archive_intro', {}):
            print(f"  ArchiveIntro/{lang}: cached")
            continue
        print(f"  ArchiveIntro/{lang}...", end=' ', flush=True)
        try:
            result = translate_html(ARCHIVE_INTRO_EN, lang)
            cache.setdefault('archive_intro', {})[lang] = result
            print("OK")
            changed = True
            save_cache(cache)
        except Exception as e:
            print(f"SKIP ({e})")
        time.sleep(2)

    # Archive outro per language
    if 'archive_outro' not in cache:
        cache['archive_outro'] = {'en': ARCHIVE_OUTRO_EN}
    for lang in LANGS:
        if lang in cache.get('archive_outro', {}):
            print(f"  ArchiveOutro/{lang}: cached")
            continue
        print(f"  ArchiveOutro/{lang}...", end=' ', flush=True)
        try:
            result = translate_html(ARCHIVE_OUTRO_EN, lang)
            cache.setdefault('archive_outro', {})[lang] = result
            print("OK")
            changed = True
            save_cache(cache)
        except Exception as e:
            print(f"SKIP ({e})")
        time.sleep(2)

    # Thin page extras per language
    for page_fname, extra_html in THIN_PAGE_EXTRAS.items():
        key = f'thin_{page_fname}'
        if key not in cache:
            cache[key] = {'en': extra_html}
        for lang in LANGS:
            if lang in cache.get(key, {}):
                print(f"  {key}/{lang}: cached")
                continue
            print(f"  {key}/{lang}...", end=' ', flush=True)
            try:
                result = translate_html(extra_html, lang)
                cache.setdefault(key, {})[lang] = result
                print("OK")
                changed = True
                save_cache(cache)
            except Exception as e:
                print(f"SKIP ({e})")
            time.sleep(2)

    if changed:
        save_cache(cache)
    print("Translation cache complete.\n")

    # ── Phase 2: Apply to files ───────────────────────────────────────────────
    print("=== Phase 2: Applying to HTML files ===")

    en_h2_keys = list(H2_PAGES.keys())
    all_versions = [('en', SITE)] + [(lang, os.path.join(SITE, lang)) for lang in LANGS]

    h2_count = 0
    archive_count = 0
    thin_count = 0

    for lang, folder in all_versions:
        if not os.path.isdir(folder):
            continue

        h2_texts = cache.get('h2_headings', {}).get(lang)
        if h2_texts is None:
            if lang == 'en':
                h2_texts = en_h2_texts
            else:
                print(f"  [{lang}] skipping H2 — no translation")
                h2_texts = None

        intro_html = cache.get('archive_intro', {}).get(lang)
        outro_html = cache.get('archive_outro', {}).get(lang)
        skip_archive = (intro_html is None and lang != 'en')
        if lang == 'en':
            intro_html = intro_html or ARCHIVE_INTRO_EN
            outro_html = outro_html or ARCHIVE_OUTRO_EN

        # H2 patches
        if h2_texts is not None:
            for i, fname in enumerate(en_h2_keys):
                fpath = os.path.join(folder, fname)
                if not os.path.exists(fpath):
                    continue
                with open(fpath, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                h2_text = h2_texts[i] if i < len(h2_texts) else en_h2_texts[i]
                new_content, changed_f = insert_h2(content, h2_text)
                if changed_f:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    h2_count += 1

        # Archive patches
        if not skip_archive:
            for fname in os.listdir(folder):
                if not (fname.startswith('m=') and fname.endswith('.html')):
                    continue
                fpath = os.path.join(folder, fname)
                with open(fpath, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                new_content, changed_f = insert_archive_text(content, intro_html, outro_html)
                if changed_f:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    archive_count += 1

        # Thin page extras
        for page_fname in THIN_PAGE_EXTRAS:
            key = f'thin_{page_fname}'
            extra_html = cache.get(key, {}).get(lang)
            if extra_html is None:
                if lang == 'en':
                    extra_html = THIN_PAGE_EXTRAS[page_fname]
                else:
                    continue  # skip non-EN without translation

            fpath = os.path.join(folder, page_fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, encoding='utf-8', errors='ignore') as f:
                content = f.read()
            new_content, changed_f = append_page_extra(content, extra_html)
            if changed_f:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                thin_count += 1

        print(f"  [{lang}] done")

    print(f"\n=== Done ===")
    print(f"  H2 inserted:           {h2_count} files")
    print(f"  Archive intro/outro:   {archive_count} files")
    print(f"  Thin pages expanded:   {thin_count} files")


if __name__ == '__main__':
    main()
