#!/usr/bin/env python3
"""T173: o timbre entre o app e o FM-1.
- Ao conectar, o app manda ao módulo FM6 (quadro MODULE 0x23 do dock, 'L') a linha de cada timbre: a categoria no
  idioma do app e o nº ("KEYS #7"); ao trocar o idioma, manda de novo.
- O knob PRESETS do FM-1 manda CC 0 + Program Change: o app troca o timbre (rótulo e lista) sem mandar de volta.

    python3 tests/web_timbre_fm1_test.py            (precisa de playwright com o Chromium)
"""
import os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from web_abas_test_fake import FAKE_MIDI  # noqa: E402
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


# o payload de um quadro do dock (F0 7D 48 42 cmd seq pack7(payload + crc) F7), desempacotado
UNPACK = """f => { const b = f.slice(6, -1), out = []; let acc = 0, nb = 0; for (const x of b) { acc |= (x & 0x7f) << nb; nb += 7;
  if (nb >= 8) { out.push(acc & 0xff); acc >>>= 8; nb -= 8; } } return out.slice(0, -4); }"""
LABELS = f"""() => __fm1.sent.filter(m => m[0] === 0xF0 && m[1] === 0x7D && m[2] === 0x48 && m[3] === 0x42 && m[4] === 0x23)
  .map(m => ({UNPACK})(m)).filter(p => p[0] === 0x4C).map(p => String.fromCharCode(...p.slice(1)).split('\\0'))"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1440, 'height': 900}, locale='pt-BR')
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.add_init_script(FAKE_MIDI)
    pg.goto('file://' + os.path.abspath(APP)); pg.evaluate("localStorage.clear()"); pg.goto('file://' + os.path.abspath(APP))
    pg.wait_for_timeout(500)
    pg.click('#btFm'); pg.wait_for_timeout(2500)
    ls = pg.evaluate(LABELS)
    check('ao conectar: manda as linhas ao FM6', len(ls) >= 1, len(ls))
    last = ls[-1] if ls else []
    check('linhas em português: TECLAS #7, SOPROS #21, OUTROS #0', len(last) >= 25 and last[7] == 'TECLAS #7' and last[21] == 'SOPROS #21' and last[0] == 'OUTROS #0', last[:8])
    ORD = f"""() => __fm1.sent.filter(m => m[0] === 0xF0 && m[1] === 0x7D && m[2] === 0x48 && m[3] === 0x42 && m[4] === 0x23)
      .map(m => ({UNPACK})(m)).filter(p => p[0] === 0x4F).map(p => p.slice(1))"""
    od = pg.evaluate(ORD)
    check('T179: manda a ordem do modal (TINE EP 1, TINE EP 2 9, CLAVINET 14 ... INIT 0 no fim)', bool(od) and od[-1][:6] == [1, 9, 14, 7, 15, 5] and od[-1][-1] == 0 and len(od[-1]) == 25, od[-1][:8] if od else od)
    check('ASCII e no máximo 20 caracteres', all(len(x) <= 20 and all(32 <= ord(c) < 127 for c in x) for x in last), max(map(len, last)) if last else 0)
    pg.evaluate("() => { __fm1.sent.length = 0; const l = document.getElementById('lang'); l.value = 'en'; l.dispatchEvent(new Event('change')); }")
    pg.wait_for_timeout(1500)
    ls = pg.evaluate(LABELS)
    last = ls[-1] if ls else []
    check('ao trocar o idioma: manda de novo, em inglês', len(last) >= 25 and last[7] == 'KEYS #7' and last[16] == 'PADS AND STRINGS #16', last[14:18])
    # knob PRESETS: CC 0 = 0, PC 7 -> ORGAN
    pg.evaluate("() => { __fm1.sent.length = 0; CFG.voice = 1; const i = __fm1.input; i.onmidimessage({data: new Uint8Array([0xB0, 0, 0])}); i.onmidimessage({data: new Uint8Array([0xC0, 7])}); }")
    pg.wait_for_timeout(200)
    q = pg.evaluate("() => ({voice: CFG.voice, label: document.getElementById('voiceName').textContent, back: __fm1.sent.filter(m => (m[0] & 0xF0) === 0xC0).length})")
    check('PRESETS do FM-1: o app passa para ORGAN (nº 7)', q['voice'] == 7 and q['label'] == 'Organ', q)
    check('sem mandar o Program Change de volta', q['back'] == 0, q)
    # o modal de timbres aberto também segue o FM-1 (pedido do Wellington: a barra e o modal)
    pg.evaluate("() => { document.querySelector('[data-act=\"voice\"]').click(); const i = __fm1.input; i.onmidimessage({data: new Uint8Array([0xB0, 0, 0])}); i.onmidimessage({data: new Uint8Array([0xC0, 22])}); }")
    pg.wait_for_timeout(200)
    q = pg.evaluate("() => ({open: document.getElementById('voicedlg').open, on: [...document.querySelectorAll('#voice-body [aria-pressed=\"true\"]')].map(b => b.dataset.v), label: document.getElementById('voiceName').textContent})")
    check('modal aberto: o timbre do FM-1 fica marcado na lista (Steel Drum, nº 22)', q['open'] and q['on'] == ['22'] and q['label'] == 'Steel Drum', q)
    pg.evaluate("() => document.getElementById('voicedlg').close()")
    pg.evaluate("() => { const i = __fm1.input; i.onmidimessage({data: new Uint8Array([0xB0, 0, 1])}); i.onmidimessage({data: new Uint8Array([0xC0, 3])}); }")
    pg.wait_for_timeout(100)
    check('timbre de outro banco (BANK/USER): o app não muda', pg.evaluate("() => CFG.voice") == 22)
    check('sem erros de JavaScript', not erros, erros)
    b.close()
print('\ntudo certo' if not falhas else 'falhas: ' + ', '.join(falhas))
sys.exit(1 if falhas else 0)
