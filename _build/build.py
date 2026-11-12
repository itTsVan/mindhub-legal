"""Builds the landing page in every language.

Edit _build/template.html (layout) and _build/locales/<lang>.json (text),
then run:  python3 _build/build.py            (all languages)
      or:  python3 _build/build.py de ru      (only these)
English goes to /index.html, every other language to /<lang>/index.html.
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


if __name__ == '__main__':
    main()
