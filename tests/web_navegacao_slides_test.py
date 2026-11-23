#!/usr/bin/env python3
"""T171 (Figma Navegação 114:903): na vista Notas › Slides, Anterior e Próximo têm o tamanho S do Botão
(33 px de altura, fonte 11 px), como no Figma.

    python3 tests/web_navegacao_slides_test.py            (precisa de playwright com o Chromium)
"""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1440, 375):
        pg = b.new_page(viewport={'width': w, 'height': 1000}, locale='pt-BR')
        erros = []
        pg.on('pageerror', lambda e: erros.append(str(e)))
        pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(500)
        pg.evaluate("() => { openLesson('8.15'); CFG.view = 'frases'; S.part = 1; CFG.cmap = 'slides'; openSong(S.lesson); }")
        pg.wait_for_timeout(300)
        q = pg.evaluate("""() => [...document.querySelectorAll('.cnav button')].map(e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
            return {h: Math.round(r.height), fs: s.fontSize, fw: s.fontWeight}; })""")
        check(f'{w}px: Anterior e Próximo com 33 px e fonte 11 px Black', len(q) == 2 and all(31 <= x['h'] <= 35 and x['fs'] == '11px' and x['fw'] == '900' for x in q), q)
        pg.evaluate("() => document.querySelector('[data-act=\"cslide:next\"]').click()"); pg.wait_for_timeout(200)
        check(f'{w}px: Próximo continua funcionando', pg.evaluate("() => PV.slide === 1"))
        check(f'{w}px: sem erros de JavaScript', not erros, erros)
        pg.close()
    b.close()
print('\ntudo certo' if not falhas else 'falhas: ' + ', '.join(falhas))
sys.exit(1 if falhas else 0)
