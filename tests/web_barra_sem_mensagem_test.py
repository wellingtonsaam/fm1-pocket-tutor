#!/usr/bin/env python3
"""T196: a barra MIDI segue o Figma 114:780 (Com mensagem = Não): avisos como "Testando: …" e "Alinhado: …" não aparecem
à direita da barra; um erro (barra vermelha) continua escrito.

    python3 tests/web_barra_sem_mensagem_test.py      (APP=outro.html para testar uma cópia dentro de docs/)
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


VIS = "() => { const m = document.getElementById('midiMsg'); return {txt: m.textContent, vis: m.offsetParent !== null && m.getBoundingClientRect().width > 0}; }"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000})
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(400)
    pg.evaluate("() => midiMsg('Testando: as teclas do FM-1 acendem da esquerda (Fá3) para a direita (Sol5).')")
    q = pg.evaluate(VIS)
    check('aviso comum não aparece na barra', q['txt'] and not q['vis'], q)
    pg.evaluate("() => midiMsg('Para testar, escolha o FM1 Pocket Tutor em \"LEDs\".', true)")
    q = pg.evaluate(VIS)
    check('erro continua escrito na barra', q['vis'], q)
    pg.evaluate("() => midiMsg('Conectado.')")
    q = pg.evaluate(VIS)
    check('depois do erro, aviso comum some de novo', not q['vis'], q)
    check('sem erros de JavaScript', not erros, erros[:2])
    b.close()
print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
