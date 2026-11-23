#!/usr/bin/env python3
"""T182: o app como PWA (build/fm1-pocket-tutor, montado por tools/web_pwa.py). Serve a pasta em localhost, abre num celular Android
simulado e confere: manifest em tela cheia com os ícones, service worker ativo, nada pedido ao Google Fonts, e que sem
rede o app abre de novo do cache com as fontes, as músicas e sem erro de JavaScript. A página do firmware também abre
offline e o botão de voltar leva ao app.

    python3 tools/web_pwa.py && python3 tests/web_pwa_test.py
"""
import functools
import http.server
import json
import os
import sys
import threading

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PWA = os.path.join(HERE, '..', 'build', 'fm1-pocket-tutor')
falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


class Quieto(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


Quieto.extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.webmanifest': 'application/manifest+json'}
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory=PWA))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_port}/'

man = json.load(open(os.path.join(PWA, 'manifest.webmanifest'), encoding='utf-8'))
check('manifest: abre em tela cheia, sem barra de URL', man['display'] == 'fullscreen' and 'standalone' in man['display_override'], man['display'])
check('manifest: ícones 192 e 512 (e maskable)', {i['sizes'] for i in man['icons']} == {'192x192', '512x512'} and any(i['purpose'] == 'maskable' for i in man['icons']))
for i in man['icons']:
    check(f"ícone existe: {i['src']}", os.path.exists(os.path.join(PWA, i['src'])))

with sync_playwright() as p:
    b = p.chromium.launch()
    dev = p.devices['Pixel 7']
    ctx = b.new_context(**dev, locale='pt-BR')
    pg = ctx.new_page()
    erros, google = [], []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    ctx.on('request', lambda r: google.append(r.url) if 'fonts.g' in r.url else None)
    pg.goto(URL)
    pg.evaluate("() => navigator.serviceWorker.ready")
    pg.wait_for_timeout(1500)
    q = pg.evaluate("""async () => ({sw: !!(navigator.serviceWorker.controller || (await navigator.serviceWorker.getRegistration())?.active),
        caches: await caches.keys(), man: document.querySelector('link[rel=manifest]')?.href})""")
    check('service worker ativo', q['sw'], q['caches'])
    check('cache do app criado', any(k.startswith('fm1-tutor-') for k in q['caches']), q['caches'])
    check('nada pedido ao Google Fonts', not google, google[:2])
    ctx.set_offline(True)
    pg.reload()
    pg.wait_for_timeout(1200)
    q = pg.evaluate("""async () => { const ok = async f => (await document.fonts.load(f)).length > 0;
        return {lex: await ok('900 20px "Lexend Mega"'), pub: await ok('700 14px "Public Sans"'),
                mono: await ok('700 14px "Space Mono"'), titulo: document.title,
                musicas: (window.MUSICAS_LOCAIS || []).length, header: !!document.querySelector('header')}; }""")
    check('offline: o app abre de novo', q['header'] and 'FM1' in q['titulo'], q['titulo'])
    check('offline: as três fontes carregadas', q['lex'] and q['pub'] and q['mono'], q)
    check('músicas protegidas (musicas-locais.js) fora da publicação', q['musicas'] == 0 and not os.path.exists(os.path.join(PWA, 'musicas-locais.js')), q['musicas'])
    pg.goto(URL + 'instalar-firmware.html?de=app')
    pg.wait_for_timeout(800)
    q = pg.evaluate("() => ({pacote: !!window.FM1_PACOTE, t: document.title})")
    check('offline: a página do firmware abre com o pacote', q['pacote'], q['t'])
    pg.screenshot(path=os.path.join(HERE, '..', 'build', 't182-pwa-offline.png'))
    check('sem erros de JavaScript', not erros, erros[:3])
    b.close()
srv.shutdown()
print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
