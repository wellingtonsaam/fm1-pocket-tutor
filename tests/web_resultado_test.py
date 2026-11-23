#!/usr/bin/env python3
"""T161 (Figma 227:50606): ao concluir qualquer prática da música (Praticar melodia, Praticar notas, frase a frase,
frases juntas), em qualquer aba (Arranjo, Notas da frase, vista Notas), o painel da direita ganha o estado RESULTADO,
como nas lições: LCD com estrelas e % de acertos de primeira, Repetir, Tentar de memória (no Guiado) e Menu. Sem modal.
Repetir recomeça a mesma prática; começar outra prática apaga o resultado.

    python3 tests/web_resultado_test.py            (precisa de playwright com o Chromium)
"""
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
from web_abas_test_fake import FAKE_MIDI  # noqa: E402

falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


RES = """() => { const r = document.getElementById('pvRes');
  return {on: !!r, inUcp: !!(r && r.closest('.card.ucp')), modal: document.querySelectorAll('dialog#resdlg').length,
          txt: r ? r.innerText : '', stars: r ? r.querySelectorAll('.rs .ic').length : 0,
          btns: r ? [...r.querySelectorAll('.res-act button')].map(b => b.dataset.act) : []}; }"""
# toca a prática inteira pelo FM-1 simulado; com erros=1, a 1ª nota leva uma tecla errada antes
TOCAR = """erros => { let i = 0, guard = 0;
  while (PV.fmode && guard++ < 2000) { const w = pvNotesOf()[PV.fidx]; if (!w) break;
    if (erros && i === 0) { const x = w[0] === 60 ? 62 : 60; __fm1.key(x, true); __fm1.key(x, false); }
    __fm1.key(w[0], true); __fm1.key(w[0], false); i++; }
  return i; }"""


def res(pg):
    return pg.evaluate(RES)


def cenario(pg, nome, prep, act, erros=0):
    pg.evaluate(prep); pg.wait_for_timeout(300)
    pg.evaluate("a => pvAct(a)", act); pg.wait_for_timeout(100)
    n = pg.evaluate(TOCAR, erros)
    q = res(pg)
    check(f'{nome}: o estado RESULTADO aparece no painel da direita, sem modal', q['on'] and q['inUcp'] and q['modal'] == 0 and n > 0,
          {k: q[k] for k in ('on', 'inUcp', 'modal')})
    check(f'{nome}: nota, Repetir e Menu', '% de acertos de primeira' in q['txt'] and 'pvagain' in q['btns'] and 'home' in q['btns'], q['btns'])
    return q


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000}, locale='pt-BR')
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.add_init_script(FAKE_MIDI)
    pg.goto('file://' + os.path.abspath(APP)); pg.evaluate("localStorage.clear()"); pg.goto('file://' + os.path.abspath(APP))
    pg.wait_for_timeout(400)
    pg.click('#btFm'); pg.wait_for_timeout(300)
    pg.evaluate("() => { M.cal = false; CFG.offs['FM1 Pocket Tutor'] = 0; S.mode = 'guiado'; openLesson('8.15'); }")
    song = "(v, tab) => { CFG.view = v; CFG.pvTab = tab; S.part = 0; PV.fcur = 0; S.mode = 'guiado'; openSong(S.lesson); }"
    arr = "() => (" + song + ")('midi', 'arr')"
    fr = "() => (" + song + ")('midi', 'frase')"
    notas = "() => (" + song + ")('frases', 'arr')"
    q = cenario(pg, 'Arranjo · Praticar melodia', arr, 'pvpmel')
    check('sem erro: 3 estrelas e 100%', q['stars'] == 3 and '100%' in q['txt'], q['txt'][:80])
    check('ordem dos botões do Figma: Repetir, Tentar de memória, Menu', q['btns'] == ['pvagain', 'pvmem', 'home'], q['btns'])
    check('o título RESULTADO', q['txt'].upper().startswith('RESULTADO'), q['txt'][:30])
    q = cenario(pg, 'Arranjo · com uma tecla errada', arr, 'pvpmel', erros=1)
    check('uma nota errada baixa a %', '100%' not in q['txt'], q['txt'][:80])
    # Repetir recomeça a mesma prática do início e apaga o resultado
    pg.evaluate("() => document.querySelector('#pvRes [data-act=\"pvagain\"]').click()"); pg.wait_for_timeout(150)
    r = pg.evaluate("() => ({on: !!document.getElementById('pvRes'), fmode: PV.fmode, fidx: PV.fidx, cue: Object.keys(keyEl).filter(k => keyEl[k].classList.contains('cue')).length})")
    check('Repetir: o resultado some e a prática recomeça', not r['on'] and r['fmode'] == 'seq' and r['fidx'] == 0 and r['cue'] > 0, r)
    pg.evaluate(TOCAR, 0)
    q = res(pg)
    check('Repetir: a prática repetida também mostra o resultado', q['on'] and q['stars'] == 3, q['txt'][:80])
    # Tentar de memória: muda o modo e recomeça a mesma prática
    pg.evaluate("() => document.querySelector('#pvRes [data-act=\"pvmem\"]').click()"); pg.wait_for_timeout(200)
    r = pg.evaluate("() => ({mode: S.mode, fmode: PV.fmode, fidx: PV.fidx, on: !!document.getElementById('pvRes')})")
    check('Tentar de memória: modo Memória e a mesma prática recomeça', r['mode'] == 'memoria' and r['fmode'] == 'seq' and r['fidx'] == 0 and not r['on'], r)
    pg.evaluate(TOCAR, 0)
    q = res(pg)
    check('no modo Memória o resultado não oferece Tentar de memória', q['on'] and 'pvmem' not in q['btns'], q['btns'])
    cenario(pg, 'Notas da frase · Praticar melodia', fr, 'pvpmel')
    cenario(pg, 'Vista Notas · Praticar (todas as frases, a introdução só de acordes é pulada)', notas, 'pvpnotes')
    pf = pg.evaluate("() => { const mel = fmOf(S.lesson).melody; return pvPhrases().findIndex(f => mel.filter(m => m[1] >= f.from && m[1] < f.to).length > 2); }")
    pfi = "() => { (" + song + ")('frases', 'arr'); PV.fcur = " + str(max(pf, 0)) + "; openSong(S.lesson); }"
    cenario(pg, 'Vista Notas · frase a frase', pfi, 'pvstep')
    pg.evaluate("() => document.querySelector('#pvRes [data-act=\"pvagain\"]').click()"); pg.wait_for_timeout(150)
    check('Repetir na frase a frase: recomeça a mesma frase', pg.evaluate("() => PV.fmode === 'step' && PV.fidx === 0 && !document.getElementById('pvRes')"))
    pg.evaluate("() => { PV.fmode = null; pvStop(); }")
    cenario(pg, 'Vista Notas · frases juntas', pfi, 'pvjoin')
    pg.evaluate("() => pvAct('pvstep')"); pg.wait_for_timeout(100)
    check('começar outra prática apaga o resultado', pg.evaluate("() => !document.getElementById('pvRes')"))
    check('sem erros de JavaScript', not erros, erros)
    b.close()

print(f"\n{'tudo certo' if not falhas else str(len(falhas)) + ' falha(s): ' + ', '.join(falhas)}")
sys.exit(1 if falhas else 0)
