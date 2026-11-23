#!/usr/bin/env python3
"""Saídas de som do web app (docs/prototipo-aulas.html): as 8 combinações de FM-1, TECLADO DO COMPUTADOR e
SOM DO COMPUTADOR (Figma 177:27340, corrigido em 177:27349, 177:27432, 196:46801), com um FM-1 simulado.

O FM-1 simulado é um aparelho Web MIDI falso chamado "FM1 Pocket Tutor": guarda tudo o que o app manda para ele
(notas no canal 1 e trocas de timbre) e aperta teclas como se fosse o aparelho. O som do computador é medido
espionando voiceOn() e blip(), as duas funções que tocam no alto-falante do computador.

    python3 tests/web_som_test.py            (precisa de playwright com o Chromium)
"""
import itertools
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')

# um FM-1 de mentira: o app pede acesso MIDI e encontra este aparelho
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

# espiões do som do computador (só conta quando ele realmente soa: SOM ligado e áudio pronto)
SPY = """() => {
  window.__pc = [];
  const v = voiceOn, b = blip;
  voiceOn = function (n, key, vol) { if (CFG.snd && ac) __pc.push(['nota', n]); return v.apply(this, arguments); };
  blip = function (f) { if (CFG.snd && ac) __pc.push(['sinal', f]); return b.apply(this, arguments); };
}"""

# o que conta como "tocou no FM-1": nota no canal 1 ou troca de timbre (o canal 16 são as luzes guia, sem som)
FM_SOUND = "() => __fm1.sent.filter(m => m[0] === 0x90 && m[2] > 0 || (m[0] & 0xF0) === 0xC0).length"
RESET = "() => { __fm1.sent.length = 0; __pc.length = 0; }"


def expect(fm, som, kb, fonte):
    """O comportamento combinado (Figma 177:27340): (toca no FM-1?, toca no computador?)"""
    return {
        'teclas do FM-1':        (False, fm and som),            # o FM-1 toca sozinho; com SOM ON o computador também soa (quadro aprovado)
        'letras do teclado':     (False, kb and som),
        'clique na tela':        (False, som),
        'amostra do timbre':     (fm, som),                     # Figma 196:46801: SOM ON = sempre no computador
        'tocar a música':        (fm, som),
        'exemplo da lição':      (fm and som, som),
        'sinais certo e errado': (False, som),
    }[fonte]


def run():
    res = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        for fm, som, kb in itertools.product([True, False], repeat=3):
            nome = f"FM-1 {'ON' if fm else 'OFF'} · SOM DO COMPUTADOR {'ON' if som else 'OFF'} · TECLADO DO COMPUTADOR {'ON' if kb else 'OFF'}"
            pg = b.new_page(viewport={'width': 1440, 'height': 900}, locale='pt-BR')
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.add_init_script(FAKE_MIDI)
            pg.goto('file://' + APP)
            pg.evaluate("localStorage.clear()")
            pg.goto('file://' + APP)
            pg.wait_for_timeout(300)
            # os três botões do header, como o aluno faria
            if fm:
                pg.click('#btFm')
                pg.wait_for_timeout(300)
                pg.evaluate("() => { M.cal = false; CFG.offs['FM1 Pocket Tutor'] = 0; }")
            if pg.get_attribute('#tgSnd', 'aria-pressed') != ('true' if som else 'false'):
                pg.click('#tgSnd')
            if pg.get_attribute('#tgPc', 'aria-pressed') != ('true' if kb else 'false'):
                pg.click('#tgPc')
            pg.evaluate("() => ensureAudio()")
            pg.evaluate(SPY)
            botoes = (pg.get_attribute('#btFm', 'aria-pressed') == ('true' if fm else 'false'))
            res.append((nome, 'botões no estado pedido', botoes, ''))

            def medir(fonte, acao):
                pg.evaluate(RESET)
                acao()
                pg.wait_for_timeout(150)
                no_fm = pg.evaluate(FM_SOUND) > 0
                no_pc = pg.evaluate("() => __pc.length") > 0
                ok = (no_fm, no_pc) == expect(fm, som, kb, fonte)
                res.append((nome, fonte, ok, f"FM-1 {'toca' if no_fm else 'mudo'}, computador {'toca' if no_pc else 'mudo'}"))

            if fm:
                medir('teclas do FM-1', lambda: (pg.evaluate("() => __fm1.key(60, true)"), pg.wait_for_timeout(80), pg.evaluate("() => __fm1.key(60, false)")))
            medir('letras do teclado', lambda: (pg.locator('body').focus(), pg.keyboard.down('t'), pg.wait_for_timeout(80), pg.keyboard.up('t')))

            def clique():
                r = pg.evaluate("() => { const e = keyEl[64].getBoundingClientRect(); return [e.x + e.width / 2, e.y + e.height - 20]; }")
                pg.mouse.move(*r)
                pg.mouse.down()
                pg.wait_for_timeout(80)
                pg.mouse.up()
                if kb:
                    pg.mouse.down()        # (com o teclado ligado o clique prende a tecla: um segundo clique solta)
                    pg.mouse.up()
            medir('clique na tela', clique)
            medir('amostra do timbre', lambda: pg.evaluate("() => voicePick(10)"))

            def musica():
                pg.evaluate("() => { const L = melMod.lessons[0]; CFG.view = 'midi'; openLesson(L.id); PV.setB(240); }")
                pg.evaluate(RESET)
                pg.click('#pvPlay')
                pg.wait_for_timeout(600)
                pg.click('#pvPlay')
            medir('tocar a música', musica)
            medir('exemplo da lição', lambda: pg.evaluate("() => { openLesson('3.1'); startLesson(); }"))
            medir('sinais certo e errado', lambda: pg.evaluate("() => { chime(); buzz(); }"))
            res.append((nome, 'sem erros de JavaScript', not errs, '; '.join(errs)[:200]))
            pg.close()
        b.close()
    falhas = 0
    atual = None
    for nome, fonte, ok, info in res:
        if nome != atual:
            print('\n' + nome)
            atual = nome
        print(('  ok    ' if ok else '  FALHA ') + fonte + (' — ' + info if info else ''))
        falhas += not ok
    print(f"\n{len(res) - falhas} de {len(res)} verificações certas" + ('' if not falhas else f"; {falhas} falharam"))
    return 1 if falhas else 0


if __name__ == '__main__':
    sys.exit(run())
