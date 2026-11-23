#!/usr/bin/env python3
"""T178 (Figma T175, Pocket Tutor/Aba Arranjo 353:6225): na aba Arranjo, "Ver a sequência completa" fica logo abaixo do
mapa de compassos, antes dos acordes. Confere com a Parte 1 (8 compassos, 16 trocas) e com a Música inteira, fechada e
aberta, e que o acorde que soa continua marcado nas duas listas.

    python3 tests/web_sequencia_test.py       (precisa de playwright com o Chromium; APP=outro.html para testar uma cópia)
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


ORDEM = """() => { const a = document.getElementById('pvArr'); if (!a) return null;
  const kids = [...a.children].map(e => e.id || e.className || e.tagName);
  const seq = a.querySelector(':scope > details.seqd');
  return {kids, iSeq: [...a.children].indexOf(seq), iLab: [...a.children].findIndex(e => e.classList.contains('blab')),
          iAc: [...a.children].indexOf(document.getElementById('fold-ac')),
          n: seq ? seq.querySelectorAll('[data-ci]').length : 0, cells: document.querySelectorAll('#pvStrip i').length,
          open: seq ? seq.open : null, txt: seq ? seq.querySelector('summary').textContent.trim() : ''}; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000}, locale='pt-BR')
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto('file://' + os.path.abspath(APP)); pg.evaluate("localStorage.clear()"); pg.goto('file://' + os.path.abspath(APP))
    pg.wait_for_timeout(400)
    for parte, cells in (('Parte 1', 8), ('Música inteira', 36)):
        pg.evaluate("""nome => { CFG.view = 'midi'; openLesson('8.15'); const L = S.lesson;
            S.part = L.parts.findIndex(p => p.name === nome); openSong(L); }""", parte)
        pg.wait_for_timeout(200)
        q = pg.evaluate(ORDEM)
        check(f'{parte}: {cells} compassos no mapa', q and q['cells'] == cells, q and q['cells'])
        check(f'{parte}: sequência logo abaixo do mapa (depois dos rótulos P1…)', q and q['iSeq'] == q['iLab'] + 1, q and q['kids'])
        check(f'{parte}: sequência antes dos acordes', q and 0 <= q['iSeq'] < q['iAc'], q and q['kids'])
        check(f'{parte}: começa fechada', q and q['open'] is False, q and q['open'])
        if parte == 'Parte 1':
            check('Parte 1: 16 trocas na sequência', q and q['n'] == 16 and '(16)' in q['txt'], q and q['txt'])
    pg.evaluate("() => document.querySelector('#pvArr details.seqd summary').click()"); pg.wait_for_timeout(100)
    q = pg.evaluate(ORDEM)
    check('abrir a sequência: os chips aparecem logo abaixo do mapa', q['open'] is True and q['n'] > 0 and q['iSeq'] == q['iLab'] + 1, q['n'])
    pg.screenshot(path=os.path.join(HERE, '..', 'build', 't178-sequencia.png'), clip={'x': 0, 'y': 0, 'width': 1600, 'height': 1000})
    check('sem erros de JavaScript', not erros, erros[:3])
    b.close()

print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
