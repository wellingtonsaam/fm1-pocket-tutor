#!/usr/bin/env python3
"""T182: o ícone do app (Figma 375:6744, docs/pwa/icon-192.png) aparece no header antes do título, como no Cabeçalho
114:779: 28 px no computador e no celular em pé, 24 px no celular deitado, carregado e alinhado ao título.

    python3 tests/web_icone_app_test.py      (APP=outro.html para testar uma cópia dentro de docs/)
"""
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


Q = """() => { const i = document.querySelector('header .appic'), t = document.getElementById('title');
  if (!i) return null; const a = i.getBoundingClientRect(), b = t.getBoundingClientRect();
  return {w: Math.round(a.width), h: Math.round(a.height), ok: i.complete && i.naturalWidth > 0,
          antes: !!(i.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING), esq: a.right <= b.left + 1,
          meio: Math.abs((a.top + a.height / 2) - (b.top + b.height / 2))}; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for nome, vp, tam in (('computador 1600', (1600, 1000), 28), ('celular em pé 375', (375, 812), 28), ('celular deitado 873', (873, 393), 24)):
        pg = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        erros = []
        pg.on('pageerror', lambda e: erros.append(str(e)))
        pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(400)
        q = pg.evaluate(Q)
        check(f'{nome}: ícone no header', q is not None)
        if q:
            check(f'{nome}: {tam} px e carregado', q['w'] == tam and q['h'] == tam and q['ok'], q)
            check(f'{nome}: antes do título e alinhado', q['antes'] and q['esq'] and q['meio'] <= 4, q)
        check(f'{nome}: sem erros de JavaScript', not erros, erros[:2])
        if nome.startswith('computador'):
            pg.screenshot(path=os.path.join(HERE, '..', 'build', 't182-icone-header.png'), clip={'x': 0, 'y': 0, 'width': 1600, 'height': 80})
        pg.close()
    b.close()
print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
