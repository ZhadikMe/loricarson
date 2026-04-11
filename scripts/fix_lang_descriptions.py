#!/usr/bin/env python3
"""
fix_lang_descriptions.py — Translates root descriptions to all lang versions.

Run from site root:
  cd d:/loricarson
  python scripts/fix_lang_descriptions.py
"""

import os, re, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')
import requests

SITE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seo_desc_translations.json')
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


# ── Groq ──────────────────────────────────────────────────────────────────────

def groq_translate_batch(texts: list[str], lang: str, retries=5) -> list[str]:
    lang_name = LANG_NAMES[lang]
    numbered = '\n'.join(f'{i+1}. {t}' for i, t in enumerate(texts))
    system = (f"Translate the following meta descriptions to {lang_name}. "
              f"Keep each description between 50-160 characters. "
              f"Return ONLY the translations, numbered the same way. No extra text.")
    delay = 3
    for attempt in range(retries):
        try:
            r = requests.post(GROQ_URL,
                headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'},
                json={'model': GROQ_MODEL,
                      'messages': [{'role': 'system', 'content': system},
                                   {'role': 'user', 'content': numbered}],
                      'temperature': 0.1, 'max_tokens': 4000},
                timeout=90)
            if r.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f' [429 wait {wait}s]', end='', flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            content = r.json()['choices'][0]['message']['content'].strip()
            out = []
            for line in content.split('\n'):
                line = line.strip()
                line = re.sub(r'^\d+[.)]\s*', '', line)
                if line:
                    out.append(line)
            while len(out) < len(texts):
                out.append(texts[len(out)])
            return out[:len(texts)]
        except requests.exceptions.HTTPError:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))
    raise RuntimeError("Max retries exceeded")


# ── File helpers ──────────────────────────────────────────────────────────────

def get_description(content: str) -> str | None:
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', content, re.IGNORECASE)
    return m.group(1).strip() if m else None


def set_description(content: str, desc: str) -> tuple[str, bool]:
    existing = get_description(content)
    if existing and 50 <= len(existing) <= 160:
        return content, False

    new_meta = f'<meta name="description" content="{desc}">'
    new_og   = f'<meta property="og:description" content="{desc}">'

    if existing is not None:
        content = re.sub(r'<meta\s+name="description"\s+content="[^"]*"(\s*/?)?>', new_meta, content, flags=re.IGNORECASE)
        content = re.sub(r'<meta\s+property="og:description"\s+content="[^"]*"(\s*/?)?>', new_og, content, flags=re.IGNORECASE)
        return content, True
    else:
        head_close = content.find('</head>')
        if head_close < 0:
            head_close = content.find('<body')
        if head_close < 0:
            return content, False
        inject = f'{new_meta}\n{new_og}\n'
        return content[:head_close] + inject + content[head_close:], True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Step 1: Collect all unique root descriptions ──────────────────────────
    print("=== Step 1: Reading root descriptions ===")
    root_descs = {}  # filename → description

    for fname in os.listdir(SITE):
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(SITE, fname)
        try:
            content = open(fpath, encoding='utf-8', errors='ignore').read()
            desc = get_description(content)
            if desc and 50 <= len(desc) <= 160:
                root_descs[fname] = desc
        except:
            pass

    print(f"  Root pages with valid descriptions: {len(root_descs)}")

    # ── Step 2: Group by description text (many archive pages share pattern) ──
    # Get unique descriptions and their filenames
    unique_descs = list(set(root_descs.values()))
    desc_to_files = {}
    for fname, desc in root_descs.items():
        desc_to_files.setdefault(desc, []).append(fname)
    print(f"  Unique descriptions: {len(unique_descs)}")

    # ── Step 3: Load/build translation cache ─────────────────────────────────
    print("\n=== Step 2: Building translation cache ===")
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding='utf-8') as f:
            cache = json.load(f)

    for lang in LANGS:
        if lang in cache and len(cache[lang]) >= len(unique_descs):
            print(f"  {lang}: cached ({len(cache[lang])} items)")
            continue

        existing = cache.get(lang, {})
        missing_descs = [d for d in unique_descs if d not in existing]

        if not missing_descs:
            print(f"  {lang}: all cached")
            continue

        print(f"  {lang}: translating {len(missing_descs)} descriptions...", end=' ', flush=True)

        # Batch in chunks of 20
        translated_all = []
        for i in range(0, len(missing_descs), 20):
            chunk = missing_descs[i:i+20]
            try:
                results = groq_translate_batch(chunk, lang)
                translated_all.extend(results)
            except Exception as e:
                print(f"ERROR: {e}")
                translated_all.extend(chunk)  # fallback
            time.sleep(2)

        for orig, trans in zip(missing_descs, translated_all):
            existing[orig] = trans

        cache[lang] = existing
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print("OK")

    # ── Step 4: Apply to lang files ───────────────────────────────────────────
    print("\n=== Step 3: Applying to lang files ===")
    fixed = 0
    skipped = 0

    for lang in LANGS:
        lang_dir = os.path.join(SITE, lang)
        if not os.path.isdir(lang_dir):
            continue

        lang_cache = cache.get(lang, {})

        for fname, en_desc in root_descs.items():
            fpath = os.path.join(lang_dir, fname)
            if not os.path.exists(fpath):
                continue

            translated_desc = lang_cache.get(en_desc, en_desc)
            # Ensure length within bounds
            if len(translated_desc) > 160:
                translated_desc = translated_desc[:157] + '...'
            if len(translated_desc) < 50:
                translated_desc = en_desc  # fallback to English

            try:
                content = open(fpath, encoding='utf-8', errors='ignore').read()
                new_content, changed = set_description(content, translated_desc)
                if changed:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    fixed += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ERROR {lang}/{fname}: {e}")

        print(f"  [{lang}] done")

    print(f"\n=== Done ===")
    print(f"  Fixed: {fixed} files")
    print(f"  Already OK: {skipped} files")


if __name__ == '__main__':
    main()
