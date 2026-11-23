#!/usr/bin/env python3
"""T195: Testar LEDs numa música acende a sequência do trecho escolhido no ARRANJO DA MÚSICA, na ordem da música.
Com um FM-1 simulado: vista MIDI na Parte 4 = as notas da melodia da Parte 4; vista Acordes = as teclas de cada acorde
da parte; Música inteira = mais notas que a Parte 4; fora da música = a varredura de Fá3 a Sol5 de sempre.

    python3 tests/web_testar_leds_test.py      (APP=outro.html para testar uma cópia dentro de docs/)
"""
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
FAKE_MIDI = """
(() => {
  const sent = [];
  const input = { id: 'in1', name: 'FM1 Pocket Tutor', type: 'input', state: 'connected', onmidimessage: null,
                  addEventListener() {}, removeEventListener() {} };
  const output = { id: 'out1', name: 'FM1 Pocket Tutor', type: 'output', state: 'connected',
                   send(d) { sent.push([performance.now(), ...Array.from(d)]); }, addEventListener() {}, removeEventListener() {} };
  window.__fm1 = { sent };
  navigator.requestMIDIAccess = async () => ({ inputs: new Map([['in1', input]]), outputs: new Map([['out1', output]]),
    sysexEnabled: true, onstatechange: null, addEventListener() {}, removeEventListener() {} });
})();
"""
falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


ESPERADO = """() => { const s = fmOf(S.lesson), [a, b] = pvRange(), fit = n => { while (n < LO) n += 12; while (n > HI) n -= 12; return n };
  return s.melody.filter(m => m[1] >= a && m[1] < b).map(m => fit(m[0])); }"""


def acesas(pg, ms):
    pg.evaluate("() => { __fm1.sent.length = 0; document.querySelector('[data-act=\"midi:led\"]').click(); }")
    pg.wait_for_timeout(ms)
    return pg.evaluate("() => __fm1.sent.filter(m => (m[1] & 0xF0) === 0x90 && m[3] > 0).map(m => [Math.round(m[0]), m[2]])")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000}, locale='pt-BR')
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.add_init_script(FAKE_MIDI)
    pg.goto('file://' + os.path.abspath(APP)); pg.evaluate("localStorage.clear()"); pg.goto('file://' + os.path.abspath(APP))
    pg.wait_for_timeout(400)
    pg.click('#btFm'); pg.wait_for_timeout(300)
    # fora da música: varredura
    on = acesas(pg, 2300)
    check('fora da música: varredura Fá3 a Sol5', [n for _, n in on] == list(range(53, 80)), [n for _, n in on][:6])
    # Parte 4, vista MIDI
    pg.evaluate("""() => { CFG.view = 'midi'; openLesson('8.15'); const L = S.lesson; S.part = L.parts.findIndex(p => p.name === 'Parte 4'); openSong(L); }""")
    pg.wait_for_timeout(300)
    esp = pg.evaluate(ESPERADO)
    on = acesas(pg, 150 * min(len(esp), 12) + 100)
    notas = [n for _, n in on]
    check('Parte 4 (MIDI): começa pelas notas da melodia da parte, na ordem', len(esp) > 0 and notas[:10] == esp[:len(notas[:10])] and len(notas) >= 5, (notas[:8], esp[:8]))
    msg = pg.evaluate("() => (document.getElementById('midiMsg') || document.querySelector('#midibar .msg') || document.body).textContent")
    check('mensagem diz o trecho', 'Parte 4' in msg, msg[-120:])
    check('nenhuma tecla fora do FM-1', all(53 <= n <= 79 for n in notas), notas)
    # Música inteira tem mais notas que a Parte 4
    pg.evaluate("""() => { const L = S.lesson; S.part = L.parts.findIndex(p => p.name === 'Música inteira'); openSong(L); }"""); pg.wait_for_timeout(300)
    tudo = pg.evaluate(ESPERADO)
    check('Música inteira: sequência maior que a da Parte 4', len(tudo) > len(esp), (len(tudo), len(esp)))
    # vista Acordes: grupos de teclas ao mesmo tempo
    pg.evaluate("""() => { CFG.view = 'acordes'; const L = S.lesson; S.part = L.parts.findIndex(p => p.name === 'Parte 4'); openSong(L); }"""); pg.wait_for_timeout(300)
    on = acesas(pg, 1000)
    grupos = {}
    for t, n in on:
        grupos.setdefault(round(t / 100), []).append(n)
    tam = [len(v) for v in grupos.values()]
    check('Parte 4 (Acordes): cada passo acende 3 ou mais teclas juntas', tam and all(x >= 3 for x in tam), tam)
    check('sem erros de JavaScript', not erros, erros[:3])
    b.close()
print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
