#!/usr/bin/env python3
"""Barra MIDI (Figma 114:780 / 227:50645): todos os botões da barra têm a mesma altura (32 px), como no header (T164).
Os toggles (Tecla fundamental, Próxima nota) ficavam com 44 px pela regra geral button{min-height:44px}.

    python3 tests/web_midibar_altura_test.py            (precisa de playwright com o Chromium)
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
        # mostra também os controles que só aparecem com o FM-1 conectado, para medir todos
        h = pg.evaluate("""() => { document.querySelectorAll('#midibar .midionly').forEach(e => e.style.display = 'inline-flex');
            return [...document.querySelectorAll('#midibar button, #midibar select')].filter(e => e.offsetParent)
            .map(e => [e.id || e.textContent.trim().slice(0, 14), Math.round(e.getBoundingClientRect().height)]) }""")
        tgl = [x for x in h if x[0] in ('tgMono', 'tgNext')]
        ok = len(tgl) == 2 and all(a == 32 for _, a in h)
        print(f"  {'ok  ' if ok else 'FALHA'}  {w}px: todos os botões da barra MIDI com 32 px — {h}")
        if not ok: falhas.append(f'altura {w}')
        if erros: falhas.append(f'js {w}'); print('  FALHA  erros de JavaScript', erros)
    b.close()
print('\ntudo certo' if not falhas else 'falhas: ' + ', '.join(falhas))
sys.exit(1 if falhas else 0)
