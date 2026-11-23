#!/usr/bin/env python3
"""T150: a página docs/instalar-firmware.html (caminho B dos wireframes, Figma 315:251) com um FM-1 simulado no
Web MIDI. Nada vai para um FM-1 de verdade: o navegador do teste só enxerga o aparelho de mentira abaixo, que fala o
protocolo de atualização do Felucca (como o FakeFM1 de tests/install_test.mjs) e o HELLO/INFO/LIST do dock.

Cobre: sem Web MIDI; FM-1 não encontrado; aparelho que não é FM-1; conferir versões (NOVA, mesma versão = REINSTALAR);
GRAVAR só com a caixa marcada; gravação inteira com cada byte conferido; cabo que cai no meio e TENTAR DE NOVO que
termina; FM-1 que já estava em modo de atualização; CANCELAR sem mandar nada; idioma EN; nenhum glifo de ícone.

    python3 tests/web_instalar_firmware_test.py        (precisa de playwright com o Chromium; ~2 min)
"""
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = 'file://' + os.path.abspath(os.path.join(HERE, '..', 'docs', 'instalar-firmware.html'))
APP = os.environ.get('APP') or os.path.join(HERE, '..', 'docs', 'prototipo-aulas.html')
PACOTE = open(os.path.join(HERE, '..', 'docs', 'install', 'pacote-fm1.js'), encoding='utf-8').read()
VER = json.loads(re.search(r'^// (\{.*\})$', PACOTE, re.M)[1])['version']
NOVA = bool(re.match(r'\d+\.\d+', VER)) and tuple(map(int, re.match(r'(\d+)\.(\d+)', VER).groups())) > (0, 1)   # selo NOVA: só com X.Y
INFO = json.loads(re.search(r'window\.FM1_PACOTE_INFO = (\{.*\});', open(os.path.join(HERE, '..', 'docs', 'install', 'pacote-fm1-info.js'), encoding='utf-8').read())[1])
PKG, PKG_BUILD = INFO['version'], INFO.get('build') or INFO['version']   # T160: a versão que a barra do app compara
PKG_NUM = bool(re.fullmatch(r'\d+\.\d+(\.\d+)?', PKG)) and PKG not in ('0.0', '0.1')

FAKE = r"""
(() => {
  const C = %s;
  if (C.nomidi) { Object.defineProperty(navigator, 'requestMIDIAccess', { value: undefined, configurable: true }); return; }
  const eq = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
  const HS = [0xF0, 0x00, 0x32, 0x45, 0x00, 0x00, 0x00, 0x40, 0x7F, 0xF7], UP = [0xF0, 0x22, 0x24, 0x35, 0x7F, 0xF7];
  const inputs = new Map(), outputs = new Map();
  const access = { inputs, outputs, sysexEnabled: true, onstatechange: null, addEventListener() {}, removeEventListener() {} };
  const F = window.__fake = { upgrades: 0, served: 0, bad: 0, writes: 0, sysexBefore: 0, version: C.version, product: C.product || 'FM-1_902',
    newVersion: C.newVersion, asks: 0, dropped: false };
  let input = null;
  let image = null;
  const img = () => image || (image = (() => { const s = atob(window.FM1_PACOTE.b64), b = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return window.FM1Install.logicalImage(b); })());
  function boot(identity, name) {
    F.identity = identity; F.waiting = null; F.queue = [];
    for (const m of [inputs, outputs]) { for (const p of m.values()) p.state = 'disconnected'; m.clear(); }
    setTimeout(() => { if (access.onstatechange) access.onstatechange({}); }, 0);
    if (identity == null) { input = null; return; }
    const id = Math.random().toString(36).slice(2), ls = new Set();
    const i = { id: 'i' + id, name, type: 'input', state: 'connected', onmidimessage: null, open: async () => {},
      addEventListener: (_, f) => ls.add(f), removeEventListener: (_, f) => ls.delete(f), _ls: ls };
    const o = { id: 'o' + id, name, type: 'output', state: 'connected', open: async () => {} };
    o.send = (d) => { if (o.state !== 'connected') throw new Error('InvalidStateError'); const dd = Array.from(d); setTimeout(() => rx(dd), 1); };
    input = i; inputs.set(i.id, i); outputs.set(o.id, o);
  }
  function tx(bytes) {
    const i = input;
    setTimeout(() => { if (!i || i.state !== 'connected') return; const ev = { data: Uint8Array.from(bytes) };
      if (i.onmidimessage) i.onmidimessage(ev); i._ls.forEach((f) => f(ev)); }, 1);
  }
  const u32 = (v) => [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255];
  function dock(r) {
    const D = window.FM1Dock || window.PTDock, reply = (d) => tx(Array.from(D.frame(r.cmd | 0x40, r.seq, Uint8Array.from(d))));
    if (r.cmd === D.CMD.HELLO) reply([0, 1, 2, 1, 0, 0, 0, 0, ...u32(400000), ...u32(500000), ...u32(300000), ...new Array(16).fill(0), ...u32(0), ...new Array(4).fill(0)]);
    else if (r.cmd === D.CMD.INFO) {
      if (C.noinfo) return;                     // T160: um firmware que não responde ao INFO
      if (!F.version) { reply([10]); return; }
      const b = new Array(88).fill(0), str = (o, s) => [...new TextEncoder().encode(s)].forEach((c, k) => { b[o + k] = c; });
      b.splice(1, 11, 1, 0, 3, 1, 0, 0, 0, 0, 0, 0, 0x16);
      str(36, 'AC791N'); str(44, F.version); str(60, C.build || F.version); str(72, 'FM-1');
      reply(b);
    } else if (r.cmd === D.CMD.LIST) { reply([0, 0, 0, 0, ...u32(1), ...u32(1000), ...u32(0), ...new TextEncoder().encode('FM6'.padEnd(24, '\0'))]); reply([0, 0xff]); }
  }
  function rx(d) {
    if (eq(d, HS)) {
      const t = [...new TextEncoder().encode(F.identity)];
      tx([0xF0, ...window.FM1Ota.pack7([0, 0x59, 0x11, 0, 0, 0, ...t, ...new Array(28 - t.length).fill(0)]), 0xF7]);
    } else if (eq(d, UP)) {
      F.upgrades++;
      const im = img();
      F.queue = F.identity.startsWith('ota-')
        ? [...Array.from({ length: Math.ceil(im.length / 512) }, (_, k) => [k * 512, Math.min(512, im.length - k * 512)]), [0xF0000000, 8]]
        : [[0, 64], [0x40, 160], [0x1000, 512], [0xE0000000, 8]];
      next();
    } else if (F.waiting) {
      const u = window.FM1Ota.unpack7(d.slice(1, -1)), [addr, len] = F.waiting;
      const got = u.slice(14, 14 + (addr >= 0xE0000000 ? 8 : len));
      const want = addr >= 0xE0000000 ? [...new TextEncoder().encode('success'), 0] : Array.from(img().subarray(addr, addr + len));
      if (!eq(got, want)) F.bad++;
      F.waiting = null; F.served++;
      if (F.identity.startsWith('ota-') && addr < 0xE0000000) {
        F.writes++;
        if (C.dropAt && !F.dropped && F.writes === C.dropAt) { F.dropped = true; boot(null); return; }
      }
      if (addr === 0xE0000000) setTimeout(() => boot('ota-' + F.product, 'Felucca Update'), 300);
      else if (addr === 0xF0000000) setTimeout(() => { F.version = F.newVersion; boot(F.product, 'FM1 Pocket Tutor'); }, 300);
      else next();
    } else if (d[0] === 0xF0 && !F.identity.startsWith('ota-')) {
      const r = (window.FM1Dock || window.PTDock).parse(Uint8Array.from(d));
      if (r) dock(r);
    }
  }
  function next() {
    const r = F.queue.shift();
    if (!r) return;
    F.waiting = r;
    const [addr, len] = r;
    const u = [0, 0x59, 0x30, 0, 0, 0, 0, addr & 0xFF, (addr >>> 8) & 0xFF, (addr >>> 16) & 0xFF, (addr >>> 24) & 0xFF, len & 0xFF, len >> 8, 0];
    let s = 0; for (let i = 6; i < 14; i++) s += u[i]; u.push(~s & 0xFF);
    tx([0xF0, ...window.FM1Ota.pack7(u), 0xF7]);
  }
  F.replug = () => boot('ota-' + F.product, 'Felucca Update');
  if (C.identity) boot(C.identity, C.identity.startsWith('ota-') ? 'Felucca Update' : (C.port || 'FM1 Pocket Tutor'));
  navigator.requestMIDIAccess = async (o) => { F.asks++; F.sysex = !!(o && o.sysex); return access; };
})();
"""

falhas = []
BAD = re.compile('[←-⇿⌀-⏿■-◿☀-➿⬀-⯿‹›«»]|[\U0001F000-\U0001FAFF]')


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}", flush=True)
    if not ok:
        falhas.append(nome)


def abre(b, cfg, lang='pt'):
    pg = b.new_page(viewport={'width': 1400, 'height': 900}, locale='pt-BR')
    pg.erros = []
    pg.on('pageerror', lambda e: pg.erros.append(str(e)))
    pg.add_init_script(f"try{{localStorage.setItem('fm1lang','{lang}')}}catch(_){{}}")
    pg.add_init_script(FAKE % json.dumps(cfg))
    pg.goto(PAGE)
    pg.wait_for_timeout(200)
    return pg


def txt(pg, sel='#tela'):
    return pg.inner_text(sel)


def fake(pg):
    return pg.evaluate('() => window.__fake')


def espera_tela(pg, nome, ms=90000):
    pg.wait_for_function(f"() => window.__instalar.tela === '{nome}' || window.__instalar.tela === 'erro'", timeout=ms)
    return pg.evaluate('() => window.__instalar.tela')


with sync_playwright() as p:
    b = p.chromium.launch()

    print('sem Web MIDI')
    pg = abre(b, {'nomidi': True})
    check('CONECTAR FM-1 desativado', pg.is_disabled('[data-act=conectar]'))
    check('lateral: Sem Web MIDI, aviso de Safari/iPhone', 'Sem Web MIDI' in txt(pg, '#lado') and 'SAFARI' in txt(pg).upper())
    pg.close()

    print('FM-1 não encontrado')
    pg = abre(b, {'identity': None})
    pg.click('[data-act=conectar]'); pg.wait_for_function('() => !window.__instalar.busy', timeout=20000)
    check('mensagem de não encontrado, continua em Conectar', 'não encontrado' in txt(pg) and pg.evaluate('() => window.__instalar.tela') == 'conectar')
    check('pediu o MIDI com SysEx', fake(pg)['sysex'] is True)
    pg.close()

    print('aparelho que não é FM-1')
    pg = abre(b, {'identity': 'SMK-37 Pro_016', 'version': None})
    pg.click('[data-act=conectar]'); pg.wait_for_function('() => !window.__instalar.busy', timeout=20000)
    check('recusado, nada enviado', 'não é um FM-1' in txt(pg) and fake(pg)['upgrades'] == 0)
    pg.close()

    print('caminho feliz: v0.1 no FM-1, a do app no pacote')
    pg = abre(b, {'identity': 'FM-1_902', 'version': '0.1', 'newVersion': VER})
    check('título FLASH FM1 na página e na aba', pg.inner_text('h1').strip().upper() == 'FLASH FM1' and pg.title().startswith('Flash FM1'), pg.title())
    check('fase 1 Conectar ativa, FM-1 OFF', pg.inner_text('#fases li.now').startswith('1') and 'OFF' in pg.inner_text('#pill'))
    pg.click('[data-act=conectar]'); espera_tela(pg, 'conferir', 20000)
    t = txt(pg)
    check('conferir: v0.1 no FM-1 e a versão do app com NOVA', 'v0.1' in t and (VER in t) and pg.locator('.chip').count() == (1 if NOVA else 0), t[:200])
    check('lateral: conectado, identidade, versão', 'FM-1_902' in txt(pg, '#lado') and '0.1' in txt(pg, '#lado') and 'ON' in pg.inner_text('#pill'))
    check('GRAVAR desativado sem a caixa', pg.is_disabled('[data-act=gravar]'))
    pg.evaluate("() => document.querySelector('[data-act=gravar]').removeAttribute('disabled')")
    pg.click('[data-act=gravar]'); pg.wait_for_timeout(300)
    check('...e mesmo forçado, sem a caixa nada é enviado', fake(pg)['upgrades'] == 0 and pg.evaluate('() => window.__instalar.tela') == 'conferir')
    pg.check('#conf')
    check('com a caixa, GRAVAR liberado', not pg.is_disabled('[data-act=gravar]'))
    pg.click('[data-act=gravar]')
    pg.wait_for_function("() => window.__instalar.et[2] === 'now' && window.__instalar.pct > 5", timeout=40000)
    t = txt(pg)
    check('gravando: barra, etapas, aviso de não desligar, VOLTAR desativado',
          'NÃO DESLIGUE' in t.upper() and pg.is_disabled('#voltar') and pg.inner_text('#fases li.now').startswith('3'), pg.inner_text('#pct'))
    check('lateral mostra o modo de atualização', 'Modo de atualização' in txt(pg, '#lado') and 'ota-FM-1_902' in txt(pg, '#lado'))
    check('sair da página pede confirmação', pg.evaluate("() => { const e = new Event('beforeunload', {cancelable: true}); dispatchEvent(e); return e.defaultPrevented; }"))
    fim = espera_tela(pg, 'pronto')
    f = fake(pg)
    check('pronto, sem erro', fim == 'pronto', pg.evaluate('() => window.__instalar.err'))
    check('cada byte servido conferido', f['bad'] == 0 and f['writes'] > 500, f)
    check('tela de sucesso com a versão lida do FM-1', 'FIRMWARE INSTALADO' in txt(pg).upper() and VER in txt(pg) and pg.locator('#fases li.done').count() == 4)
    check('sair já não pede confirmação', not pg.evaluate("() => { const e = new Event('beforeunload', {cancelable: true}); dispatchEvent(e); return e.defaultPrevented; }"))
    check('sem erros de JS', not pg.erros, pg.erros)
    pg.close()

    print('o cabo cai no meio da gravação, TENTAR DE NOVO termina')
    pg = abre(b, {'identity': 'FM-1_902', 'version': '0.1', 'newVersion': VER, 'dropAt': 120})
    pg.click('[data-act=conectar]'); espera_tela(pg, 'conferir', 20000); pg.check('#conf'); pg.click('[data-act=gravar]')
    fim = espera_tela(pg, 'pronto')
    t = txt(pg)
    check('erro: a gravação parou, o FM-1 não perdeu nada', fim == 'erro' and 'NÃO PERDEU NADA' in t.upper(), pg.evaluate('() => window.__instalar.err'))
    check('fase Gravar em vermelho, etapa 3 PAROU', 'bad' in pg.get_attribute('#fases li:nth-child(3)', 'class') and pg.locator('#etapas li.bad').count() == 1)
    check('resgate OCT− e detalhes na tela', 'OCT−' in t and pg.locator('#det').count() == 1)
    pg.evaluate('() => window.__fake.replug()')
    pg.click('[data-act=tentar]')
    pg.wait_for_function("() => window.__instalar.tela !== 'erro'", timeout=20000)
    fim = espera_tela(pg, 'pronto')
    f = fake(pg)
    check('TENTAR DE NOVO terminou a gravação a partir do modo de atualização', fim == 'pronto' and f['bad'] == 0, f)
    check('sem erros de JS', not pg.erros, pg.erros)
    pg.close()

    print('o FM-1 já está em modo de atualização ao conectar')
    pg = abre(b, {'identity': 'ota-FM-1_902', 'version': None, 'newVersion': VER})
    pg.click('[data-act=conectar]'); espera_tela(pg, 'retomar', 20000)
    check('tela Terminar a instalação', 'TERMINAR A INSTALAÇÃO' in txt(pg).upper() and pg.is_disabled('[data-act=gravar]'))
    pg.check('#conf'); pg.click('[data-act=gravar]')
    fim = espera_tela(pg, 'pronto')
    check('terminou', fim == 'pronto' and fake(pg)['bad'] == 0)
    pg.close()

    print('mesma versão no FM-1 e no app')
    pg = abre(b, {'identity': 'FM-1_902', 'version': VER})
    pg.click('[data-act=conectar]'); espera_tela(pg, 'conferir', 20000)
    check('avisa "você já tem esta versão" e o botão é REINSTALAR, sem NOVA',
          'JÁ TEM ESTA VERSÃO' in txt(pg).upper() and pg.inner_text('[data-act=gravar]').upper() == 'REINSTALAR' and pg.locator('.chip').count() == 0)
    print('CANCELAR')
    pg.click('[data-act=voltar]'); pg.wait_for_timeout(800)
    check('volta para o app sem mandar nada', pg.url.split('#')[0].endswith('prototipo-aulas.html') and fake(pg)['upgrades'] == 0, pg.url)
    pg.close()

    print('o botão na barra do app')
    pg = b.new_page(viewport={'width': 1600, 'height': 900}, locale='pt-BR')
    pg.add_init_script("try{localStorage.setItem('fm1lang','pt')}catch(_){}")
    pg.add_init_script("try{localStorage.setItem('fm1cadastro','teste')}catch(_){}")   # T203: cadastro já feito; o modal tem teste próprio
    pg.add_init_script(FAKE % json.dumps({'identity': 'FM1_SEM_RESPOSTA', 'version': None}))
    pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(500)
    check('FM-1 OFF: FLASH FM1 escondido', pg.locator('#btFw').count() == 1 and not pg.is_visible('#btFw'))
    pg.click('#btFm'); pg.wait_for_timeout(600)
    on = pg.get_attribute('#btFm', 'aria-pressed')
    check('FM-1 ON: FLASH FM1 aparece ao lado', on == 'true' and pg.is_visible('#btFw') and pg.inner_text('#btFw').upper() == 'FLASH FM1', on)
    pg.click('#btFw'); pg.wait_for_timeout(500)
    check('leva à página de instalação', 'instalar-firmware.html' in pg.url, pg.url)
    pg.click('#voltar'); pg.wait_for_timeout(600)
    check('VOLTAR traz de volta ao app', pg.url.split('#')[0].endswith(os.path.basename(APP)), pg.url)
    pg.close()

    print('T160: FLASH FM1 só quando o FM-1 precisa (versão do pacote: %s)' % PKG)

    def barra(cfg):
        pg = b.new_page(viewport={'width': 1600, 'height': 900}, locale='pt-BR')
        pg.erros = []
        pg.on('pageerror', lambda e: pg.erros.append(str(e)))
        pg.add_init_script("try{localStorage.setItem('fm1lang','pt')}catch(_){}")
        pg.add_init_script(FAKE % json.dumps(cfg))
        pg.goto('file://' + os.path.abspath(APP)); pg.wait_for_timeout(400)
        pg.click('#btFm'); pg.wait_for_timeout(1200)
        r = {'on': pg.get_attribute('#btFm', 'aria-pressed') == 'true', 'vis': pg.is_visible('#btFw'),
             'txt': pg.inner_text('#btFw').strip().upper() if pg.is_visible('#btFw') else '',
             'selo': pg.inner_text('#btFw .nova').strip().upper() if pg.is_visible('#btFw .nova') else '',
             'st': pg.evaluate('window.__fw && window.__fw.st'), 'erros': pg.erros}
        pg.close()
        return r

    r = barra({'identity': 'FM-1_921', 'version': None, 'port': 'FM-1'})
    check('outro firmware (porta FM-1): FLASH FM1 aparece, sem selo', r['on'] and r['vis'] and r['txt'] == 'FLASH FM1' and not r['selo'] and not r['erros'], r)
    if PKG_NUM:
        r = barra({'identity': 'FM-1_902', 'version': '0.1'})
        check('Pocket Tutor 0.1: FLASH FM1 com o selo v%s NOVA' % PKG, r['vis'] and r['selo'] == ('V%s NOVA' % PKG) and r['st'] == 'old' and not r['erros'], r)
        r = barra({'identity': 'FM-1_902', 'version': '9.9'})
        check('Pocket Tutor mais novo que o pacote: FLASH FM1 sem selo', r['vis'] and not r['selo'] and r['st'] == 'other', r)
    r = barra({'identity': 'FM-1_902', 'version': PKG, 'build': PKG_BUILD})
    check('mesma versão (%s): a barra fica sem o FLASH FM1' % PKG, r['on'] and not r['vis'] and r['st'] == 'same' and not r['erros'], r)
    r = barra({'identity': 'FM-1_902', 'version': PKG, 'noinfo': True})
    check('INFO sem resposta: FLASH FM1 aparece, sem selo', r['on'] and r['vis'] and not r['selo'] and r['st'] == 'unknown', r)
    r = barra({'identity': 'FM-1_902', 'version': 'eb76e35+'})
    check('build de desenvolvimento (eb76e35+): FLASH FM1 aparece, sem selo', r['vis'] and not r['selo'] and r['st'] == 'other', r)

    print('inglês e glifos')
    pg = abre(b, {'identity': 'FM-1_902', 'version': '0.1'}, lang='en')
    check('textos em inglês', 'CONNECT THE FM-1' in txt(pg).upper() and pg.inner_text('#voltar').strip().upper() == 'BACK')
    check('título FLASH FM1 também em inglês', pg.inner_text('h1').strip().upper() == 'FLASH FM1')
    pg.click('[data-act=conectar]'); espera_tela(pg, 'conferir', 20000)
    check('conferir em inglês', 'Check before writing'.upper() in txt(pg).upper())
    body = pg.inner_text('body')
    check('nenhum emoji nem glifo de ícone', not BAD.search(body.replace('OCT−', '')), BAD.findall(body))
    pg.close()
    b.close()

print('\n' + ('TUDO OK' if not falhas else f'{len(falhas)} FALHA(S): ' + '; '.join(falhas)))
sys.exit(1 if falhas else 0)
