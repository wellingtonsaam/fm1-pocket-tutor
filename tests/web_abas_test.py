#!/usr/bin/env python3
"""T123: a tela da música na vista MIDI em duas abas (Figma 270:135600 Arranjo, 279:98603 Notas da frase), com um FM-1
simulado. Durante o Tocar, o Arranjo marca os compassos (os tocados escuros, o atual amarelo) e o acorde que soa; Notas
da frase mostra as notas da frase que toca em mini teclados, a atual em amarelo, e a barra TOCANDO. Na introdução
(T124: só acordes, antes da melodia), cada acorde acende as luzes e a tela do FM-1 desde o início.

    python3 tests/web_abas_test.py            (precisa de playwright com o Chromium)
"""
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
# um FM-1 de mentira (o mesmo de tests/web_som_test.py): o app pede acesso MIDI e encontra este aparelho
FAKE_MIDI = """
(() => {
  const sent = [];
  const input = { id: 'in1', name: 'FM1 Pocket Tutor', type: 'input', state: 'connected', onmidimessage: null,
                  addEventListener() {}, removeEventListener() {} };
  const output = { id: 'out1', name: 'FM1 Pocket Tutor', type: 'output', state: 'connected',
                   send(d) { sent.push(Array.from(d)); }, addEventListener() {}, removeEventListener() {} };
  window.__fm1 = { sent, input,
    key(n, on) { if (input.onmidimessage) input.onmidimessage({ data: new Uint8Array([on ? 0x90 : 0x80, n, on ? 100 : 0]) }); } };
  navigator.requestMIDIAccess = async () => ({ inputs: new Map([['in1', input]]), outputs: new Map([['out1', output]]),
    sysexEnabled: true, onstatechange: null, addEventListener() {}, removeEventListener() {} });
})();
"""

falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000}, locale='pt-BR')
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.add_init_script(FAKE_MIDI)
    pg.goto('file://' + os.path.abspath(APP)); pg.evaluate("localStorage.clear()"); pg.goto('file://' + os.path.abspath(APP))
    pg.wait_for_timeout(400)
    pg.click('#btFm'); pg.wait_for_timeout(300)
    pg.evaluate("() => { M.cal = false; CFG.offs['FM1 Pocket Tutor'] = 0; }")
    pg.evaluate("""() => { CFG.view = 'midi'; CFG.cmap = 'grade'; openLesson('8.15'); const L = S.lesson;
        S.part = L.parts.findIndex(p => p.name === 'Música inteira'); openSong(L); PV.setB(240); }""")
    q = pg.evaluate("""() => ({tabs: document.querySelectorAll('[data-act^="ptab:"]').length,
        cells: document.querySelectorAll('#pvStrip i').length, parts: document.querySelectorAll('#pvStrip i.ps').length,
        uq: document.querySelectorAll('#pv [data-cu]').length})""")
    check('as duas abas', q['tabs'] == 2, q)
    check('36 compassos, 4 divisões de parte', q['cells'] == 36 and q['parts'] == 4, q)
    check('4 acordes sem repetir (MIDI: C#m F#m7 A B)', q['uq'] == 4, q)
    pg.evaluate("() => document.getElementById('pvPlay').click()"); pg.wait_for_timeout(6000)
    q = pg.evaluate("""() => ({done: document.querySelectorAll('#pvStrip i.done').length, cur: document.querySelectorAll('#pvStrip i.cur').length,
        bar: PV.pos && PV.pos.bar, ac: document.querySelectorAll('#pv [data-cu].now').length, hd: document.getElementById('pvHd').textContent})""")
    check('Arranjo: compassos tocados e o atual marcados', q['cur'] == 1 and q['done'] == q['bar'] and q['done'] > 0, q)
    check('Arranjo: o acorde que soa marcado', q['ac'] == 1, q)
    pg.evaluate("() => document.querySelector('[data-act=\"ptab:frase\"]').click()"); pg.wait_for_timeout(1500)
    q = pg.evaluate("""() => ({arr: document.getElementById('arrWrap').hidden, cards: document.querySelectorAll('#pvFrRow button').length,
        now: document.querySelectorAll('#pvFrRow button.now').length, bar: document.getElementById('pvBar').textContent, tocando: !!PV.tr})""")
    check('Notas da frase: o arranjo some e a música continua', q['arr'] and q['tocando'], q)
    check('Notas da frase: mini teclados, a nota atual marcada', q['cards'] > 0 and q['now'] == 1, q)
    check('Notas da frase: barra TOCANDO', q['bar'].startswith('TOCANDO') and 'COMPASSO' in q['bar'], q['bar'])
    pg.evaluate("() => document.getElementById('pvPlay').click()"); pg.wait_for_timeout(300)
    q = pg.evaluate("() => document.getElementById('pvBar') ? document.getElementById('pvBar').textContent : ''")
    check('Parar: a barra volta a PARADO', q.startswith('PARADO'), q)
    # T124: a introdução (só acordes, antes da 1ª nota da melodia: ~9,8 s a 96 BPM) já acende o FM-1 no 1º segundo
    pg.evaluate("() => { PV.setB(96); document.querySelector('[data-act=\"ptab:arr\"]').click(); __fm1.sent.length = 0; document.getElementById('pvPlay').click(); }")
    pg.wait_for_timeout(700)
    q = pg.evaluate("""() => { const s = __fm1.sent, tela = s.filter(m => m[0] === 0xF0 && m[4] === 1);
        return {luzes: s.filter(m => m[0] === 0x9F && m[2] > 0).map(m => m[1]),
                tela: tela.length ? String.fromCharCode(...tela[tela.length - 1].slice(8, -1)).split('\\0') : [],
                cur: document.querySelectorAll('#pvStrip i.cur').length, ac: document.querySelectorAll('#pv [data-cu].now').length}; }""")
    check('introdução: as luzes do 1º acorde no 1º segundo', len(q['luzes']) >= 3, q['luzes'])
    check('introdução: a tela do FM-1 mostra o acorde', len(q['tela']) > 4 and q['tela'][4].startswith('INTRO'), q['tela'])
    check('introdução: o compasso 1 e o acorde marcados', q['cur'] == 1 and q['ac'] == 1, q)
    pg.evaluate("() => document.getElementById('pvPlay').click()")
    # T124 também no formato nota a nota (vista Notas): Tocar e Ouvir a frase acendem o acorde da introdução
    pg.evaluate("() => { CFG.view = 'frases'; S.part = 0; openSong(S.lesson); PV.setB(96); }"); pg.wait_for_timeout(300)
    for act in ('pvnotes', 'pvhear'):
        pg.evaluate("a => { __fm1.sent.length = 0; document.querySelector(`[data-act=\"${a}\"]`).click(); }", act)
        pg.wait_for_timeout(700)
        q = pg.evaluate("() => __fm1.sent.filter(m => m[0] === 0x9F && m[2] > 0).map(m => m[1])")
        check(f'nota a nota ({act}): as luzes do 1º acorde no 1º segundo', len(q) >= 3, q)
        pg.evaluate("a => document.querySelector(`[data-act=\"${a}\"]`).click()", act); pg.wait_for_timeout(300)
    # Praticar na aba Arranjo (sem a caixa #pvNow): a tecla certa avança e a luz passa para a nota seguinte
    pg.evaluate("() => { CFG.view = 'midi'; CFG.pvTab = 'arr'; S.part = 0; openSong(S.lesson); PV.setB(96); }"); pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('[data-act=\"pvpmel\"]').click()"); pg.wait_for_timeout(500)
    seq = []
    for _ in range(4):
        cue = pg.evaluate("() => Object.keys(keyEl).filter(k => keyEl[k].classList.contains('cue')).map(Number)")
        if not cue:
            break
        pg.evaluate("n => { __fm1.key(n, true); __fm1.key(n, false); }", cue[0]); pg.wait_for_timeout(200)
        seq.append((cue[0], pg.evaluate("() => PV.fidx")))
    mel = pg.evaluate("() => pvNotesOf().slice(0, 4).map(m => m[0])")
    check('Praticar no Arranjo: a luz segue a melodia', [c for c, _ in seq] == mel and [f for _, f in seq] == [1, 2, 3, 4], (seq, mel))
    # T153: as duas luzes tocadas juntas (a seguinte chega 150 ms antes da certa): contam as duas, em ordem, sem erro
    for n in (61, 64):
        pg.evaluate("n => __fm1.key(n, false)", n)
    pg.evaluate("() => document.querySelector('[data-act=\"pvpmel\"]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("() => __fm1.key(64, true)"); pg.wait_for_timeout(150); pg.evaluate("() => __fm1.key(61, true)"); pg.wait_for_timeout(50)
    q = pg.evaluate("() => ({fidx: PV.fidx, err: PV.err || 0})")
    check('Praticar: a seguinte tocada junto com a certa conta as duas', q['fidx'] == 2 and q['err'] == 0, q)
    for n in (61, 64):
        pg.evaluate("n => __fm1.key(n, false)", n)
    pg.evaluate("() => document.querySelector('[data-act=\"pvpmel\"]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("() => __fm1.key(64, true)"); pg.wait_for_timeout(400)
    q = pg.evaluate("() => ({fidx: PV.fidx, err: PV.err || 0})")
    check('Praticar: só a seguinte, sem a certa, continua errada', q['fidx'] == 0 and q['err'] == 1, q)
    check('sem erros de JavaScript', not erros, erros)
    b.close()

print(f"\n{'tudo certo' if not falhas else str(len(falhas)) + ' falha(s): ' + ', '.join(falhas)}")
sys.exit(1 if falhas else 0)
