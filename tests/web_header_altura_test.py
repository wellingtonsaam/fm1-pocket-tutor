#!/usr/bin/env python3
"""T164: os toggles do header (FM-1, COMPUTADOR, SOM; Figma 178:956) têm 32 px, a mesma altura dos outros botões do header.

    python3 tests/web_header_altura_test.py            (precisa de playwright com o Chromium)
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
falhas = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1600, 375):
        pg = b.new_page(viewport={'width': w, 'height': 900}, locale='pt-BR')
        erros = []
        pg.on('pageerror', lambda e: erros.append(str(e)))
        pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(800)
        h = pg.evaluate("""() => [...document.querySelectorAll('header .tgl, header button.tg, header select')].filter(e => e.offsetParent)
            .map(e => [e.id, Math.round(e.getBoundingClientRect().height)])""")
        tgl = [x for x in h if x[0] in ('btFm', 'tgPc', 'tgSnd')]
        ok = tgl and all(a == 32 for _, a in tgl) and len({a for _, a in h}) == 1
        print(f"  {'ok  ' if ok else 'FALHA'}  {w}px: toggles com 32 px e todos os botões do header com a mesma altura — {h}")
        if not ok: falhas.append(f'altura {w}')
        if erros: falhas.append(f'js {w}'); print('  FALHA  erros de JavaScript', erros)
    b.close()
print('\ntudo certo' if not falhas else 'falhas: ' + ', '.join(falhas))
sys.exit(1 if falhas else 0)
