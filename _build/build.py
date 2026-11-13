"""Builds the landing page and the legal pages in every language.

Landing: _build/template.html (layout) + _build/locales/<lang>.json (text).
Legal:   _build/legal-template.html (layout) + _build/legal/<doc>.<lang>.html
         (the document body; translations must keep the same <h2> count/order).
Edit, then run:  python3 _build/build.py            (all languages)
      or:  python3 _build/build.py de ru      (only these)
English goes to /index.html, /terms/, /privacy/; other languages to /<lang>/...
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / '_build'
SITE = 'https://mymindhub.app'
LANGS = ['en', 'ru', 'de', 'uk', 'fr', 'es']
LABELS = {'en': 'EN', 'ru': 'RU', 'de': 'DE', 'uk': 'UK', 'fr': 'FR', 'es': 'ES'}
NAMES = {
    'en': 'English', 'ru': 'Русский', 'de': 'Deutsch',
    'uk': 'Українська', 'fr': 'Français', 'es': 'Español',
}
HTML_LANG = {'en': 'en', 'ru': 'ru', 'de': 'de', 'uk': 'uk', 'fr': 'fr', 'es': 'es'}

SWITCHER_CSS = '''      .lang { display: flex; gap: 4px; font-size: 13px; }
      .lang a { color: var(--muted); text-decoration: none; padding: 2px 6px; border-radius: 6px; }
      .lang a[aria-current] { color: var(--fg); font-weight: 700; background: var(--soft); }
      footer .lang { width: 100%; flex-wrap: wrap; }
'''

REDIRECT_SCRIPT = '''    <script>
      (() => {
        const langs = %s;
        let saved = null;
        try { saved = localStorage.getItem('lang'); } catch (e) {}
        if (saved || document.documentElement.lang !== 'en') return;
        const wanted = (navigator.languages || [navigator.language || 'en'])
          .map((l) => l.toLowerCase().split('-')[0])
          .find((l) => langs.includes(l));
        if (wanted && wanted !== 'en') location.replace('/' + wanted + '/' + location.hash);
      })();
    </script>
'''

REMEMBER_SCRIPT = '''    <script>
      document.querySelectorAll('.lang a').forEach((a) => a.addEventListener('click', () => {
        try { localStorage.setItem('lang', a.dataset.lang); } catch (e) {}
      }));
    </script>
'''


def page_url(lang: str) -> str:
    return f'{SITE}/' if lang == 'en' else f'{SITE}/{lang}/'


def switcher(current: str) -> str:
    links = []
    for lang in LANGS:
        href = '/' if lang == 'en' else f'/{lang}/'
        current_attr = ' aria-current="true"' if lang == current else ''
        links.append(
            f'<a href="{href}" hreflang="{lang}" lang="{lang}" data-lang="{lang}" '
            f'title="{NAMES[lang]}"{current_attr}>{LABELS[lang]}</a>'
        )
    return '<div class="lang">' + ''.join(links) + '</div>'


def replace_once(html: str, old: str, new: str) -> str:
    if html.count(old) != 1:
        sys.exit(f'template marker not found exactly once: {old!r}')
    return html.replace(old, new)


DOCS = {'terms': 'terms', 'privacy': 'privacy'}


def has_doc(doc: str, lang: str) -> bool:
    return (BUILD / 'legal' / f'{doc}.{lang}.html').exists()


def doc_path(doc: str, lang: str) -> str:
    if lang == 'en' or not has_doc(doc, lang):
        return f'/{doc}/'
    return f'/{lang}/{doc}/'


def render(template: str, strings: dict, lang: str, en: dict) -> str:
    missing = sorted(set(en) - set(strings))
    extra = sorted(set(strings) - set(en))
    if missing or extra:
        sys.exit(f'{lang}: missing {missing} extra {extra}')

    html = re.sub(r'\{\{([a-zA-Z0-9_.]+)\}\}', lambda m: strings[m.group(1)], template)
    leftover = re.findall(r'\{\{[^}]*\}\}', html)
    if leftover:
        sys.exit(f'{lang}: unknown keys {leftover}')

    html = replace_once(html, '<html lang="en">', f'<html lang="{HTML_LANG[lang]}">')
    alternates = ''.join(
        f'    <link rel="alternate" hreflang="{l}" href="{page_url(l)}" />\n' for l in LANGS
    ) + f'    <link rel="alternate" hreflang="x-default" href="{page_url("en")}" />\n'
    html = replace_once(
        html,
        f'    <link rel="canonical" href="{SITE}/" />\n',
        f'    <link rel="canonical" href="{page_url(lang)}" />\n' + alternates,
    )
    html = replace_once(html, '      .points { display: grid;', SWITCHER_CSS + '      .points { display: grid;')
    html = replace_once(html, '<a class="brand" href="/">', f'<a class="brand" href="{"/" if lang == "en" else f"/{lang}/"}">')
    html = replace_once(
        html,
        f'>{strings["nav.getHelp"]}</a>\n        </div>\n      </nav>',
        f'>{strings["nav.getHelp"]}</a>\n          {switcher(lang)}\n        </div>\n      </nav>',
    )
    html = replace_once(
        html,
        '        </div>\n      </footer>',
        f'        </div>\n        {switcher(lang)}\n      </footer>',
    )
    html = replace_once(html, '  </head>', REDIRECT_SCRIPT % json.dumps(LANGS) + '  </head>')
    html = replace_once(html, '  </body>', REMEMBER_SCRIPT + '  </body>')
    for doc in DOCS:
        html = html.replace(f'href="/{doc}/"', f'href="{doc_path(doc, lang)}"')
    return html


def slug(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text).lower().replace('&amp;', 'and')
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def render_legal(doc: str, lang: str, strings: dict) -> str:
    template = (BUILD / 'legal-template.html').read_text()
    body = (BUILD / 'legal' / f'{doc}.{lang}.html').read_text()
    en_body = (BUILD / 'legal' / f'{doc}.en.html').read_text()
    en_heads = re.findall(r'<h2>(.*?)</h2>', en_body, re.S)
    heads = re.findall(r'<h2>(.*?)</h2>', body, re.S)
    if len(heads) != len(en_heads):
        sys.exit(f'{doc}.{lang}: {len(heads)} <h2> but English has {len(en_heads)}')
    ids = [slug(h) for h in en_heads]
    it = iter(ids)
    body = re.sub(r'<h2>', lambda m: f'<h2 id="{next(it)}">', body)

    title = re.search(r'<h1>(.*?)</h1>', body, re.S).group(1).strip()
    toc_items = ''.join(f'<li><a href="#{i}">{h.strip()}</a></li>' for i, h in zip(ids, heads))
    toc = (f'  <details class="toc" open><summary>{strings["legal.contents"]}</summary>'
           f'<ol>{toc_items}</ol></details>\n')
    note = ''
    if lang != 'en':
        note = '  <p class="note">' + strings['legal.translationNote'].replace('{en}', f'/{doc}/') + '</p>\n'
    body = re.sub(r'(<p class="muted">.*?</p>\n)', lambda m: m.group(1) + note + toc, body, count=1, flags=re.S)
    body = re.sub(r'(<table>.*?</table>)', r'<div class="table-scroll">\1</div>', body, flags=re.S)
    body = '\n'.join(('      ' + l) if l else l for l in body.rstrip('\n').split('\n'))

    avail = [l for l in LANGS if has_doc(doc, l)]
    links = []
    for l in avail:
        cur = ' aria-current="true"' if l == lang else ''
        links.append(f'<a href="{doc_path(doc, l)}" hreflang="{l}" lang="{l}" data-lang="{l}" '
                     f'title="{NAMES[l]}"{cur}>{LABELS[l]}</a>')
    sw = '<div class="lang">' + ''.join(links) + '</div>'
    alternates = ''.join(f'    <link rel="alternate" hreflang="{l}" href="{SITE}{doc_path(doc, l)}" />\n' for l in avail)
    if len(avail) > 1:
        alternates += f'    <link rel="alternate" hreflang="x-default" href="{SITE}/{doc}/" />\n'
    redirect = REDIRECT_SCRIPT.replace("'/' + wanted + '/' + location.hash", f"'/' + wanted + '/{doc}/' + location.hash") % json.dumps(avail)
    first_p = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', re.search(r'<p>(.*?)</p>', body, re.S).group(1))).strip()

    values = {
        'lang': HTML_LANG[lang], 'title': title, 'description': first_p.replace('"', '&quot;')[:300],
        'canonical': f'{SITE}{doc_path(doc, lang)}', 'alternates': alternates,
        'redirect': redirect, 'remember': REMEMBER_SCRIPT,
        'home': '/' if lang == 'en' else f'/{lang}/',
        'privacyUrl': doc_path('privacy', lang), 'termsUrl': doc_path('terms', lang),
        'privacyCurrent': ' aria-current="page"' if doc == 'privacy' else '',
        'termsCurrent': ' aria-current="page"' if doc == 'terms' else '',
        'privacyLabel': strings['footer.privacy'], 'termsLabel': strings['footer.terms'],
        'helpLabel': strings['nav.getHelp'], 'deleteLabel': strings['footer.delete'],
        'contactLabel': strings['footer.contact'], 'switcher': sw, 'content': body,
    }
    html = re.sub(r'\{\{([a-zA-Z]+)\}\}', lambda m: values[m.group(1)], template)
    leftover = re.findall(r'\{\{[^}]*\}\}', html)
    if leftover:
        sys.exit(f'{doc}.{lang}: unknown keys {leftover}')
    return html


def main() -> None:
    template = (BUILD / 'template.html').read_text()
    en = json.loads((BUILD / 'locales' / 'en.json').read_text())
    only = sys.argv[1:]
    for lang in LANGS:
        if only and lang not in only:
            continue
        path = BUILD / 'locales' / f'{lang}.json'
        if not path.exists():
            print(f'skip {lang}: no {path.name}')
            continue
        strings = json.loads(path.read_text())
        out = ROOT / 'index.html' if lang == 'en' else ROOT / lang / 'index.html'
        out.parent.mkdir(exist_ok=True)
        out.write_text(render(template, strings, lang, en))
        print(f'built {out.relative_to(ROOT)}')
        for doc in DOCS:
            if not has_doc(doc, lang):
                continue
            out = ROOT / doc / 'index.html' if lang == 'en' else ROOT / lang / doc / 'index.html'
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_legal(doc, lang, strings))
            print(f'built {out.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
