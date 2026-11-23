#!/usr/bin/env python3
"""T201: a tag Beta (vermelha, token status-bad) aparece logo depois do nome FM1 Pocket Tutor no header,
em computador, celular em pé e deitado, e continua lá depois que o app troca o título (setTitle).

    python3 tests/web_tag_beta_test.py      (APP=outro.html para testar uma cópia dentro de docs/)
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


Q = """() => { const b = document.querySelector('#title .beta'), t = document.getElementById('titleTxt');
  if (!b || !t) return null; const a = b.getBoundingClientRect(), c = t.getBoundingClientRect(), s = getComputedStyle(b);
  return {txt: b.textContent, bg: s.backgroundColor, cor: s.color, w: Math.round(a.width), h: Math.round(a.height),
          depois: a.left >= c.right - 1 && a.left - c.right <= 12, meio: Math.abs((a.top + a.height / 2) - (c.top + c.height / 2)),
          visivel: a.right <= Math.min(innerWidth, document.getElementById('title').getBoundingClientRect().right) + 0.5 && a.width > 0, nome: t.textContent}; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for nome, vp in (('computador 1600', (1600, 1000)), ('celular em pé 375', (375, 812)), ('celular deitado 873', (873, 393))):
        pg = b.new_page(viewport={'width': vp[0], 'height': vp[1]})
        erros = []
        pg.on('pageerror', lambda e: erros.append(str(e)))
        pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(400)
        q = pg.evaluate(Q)
        check(f'{nome}: tag Beta no header', q is not None)
        if q:
            check(f'{nome}: texto Beta branco, fundo vermelho', q['txt'] == 'Beta' and q['bg'] == 'rgb(255, 107, 107)' and q['cor'] == 'rgb(255, 255, 255)', q)
            check(f'{nome}: logo depois do nome, alinhada e visível', q['depois'] and q['meio'] <= 3 and q['visivel'], q)
        pg.evaluate("() => setTitle('x')")
        q = pg.evaluate(Q)
        check(f'{nome}: continua depois de setTitle', q is not None and q['txt'] == 'Beta' and 'FM1' in q['nome'], q)
        check(f'{nome}: sem erros de JavaScript', not erros, erros[:2])
        pg.screenshot(path=os.path.join(HERE, '..', 'build', f"t201-beta-{vp[0]}.png"), clip={'x': 0, 'y': 0, 'width': min(vp[0], 900), 'height': 70})
        pg.close()
    b.close()
print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
