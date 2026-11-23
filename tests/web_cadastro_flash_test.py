#!/usr/bin/env python3
"""T203: o FLASH FM1 abre o cadastro (nome, email e consentimento) antes da página de instalação.

- sem dados válidos e sem o consentimento, CONTINUAR fica desligado;
- o envio vai para api/cadastro (aqui simulado); erro: avisa e não segue; deu certo: segue para instalar-firmware.html;
- depois do cadastro, o botão vai direto; FECHAR fecha; em inglês o modal aparece traduzido; cabe no celular.

    python3 tests/web_cadastro_flash_test.py      (APP=outro.html para testar uma cópia dentro de docs/)
"""
import functools
import http.server
import json
import os
import re
import sys
import threading

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, '..', 'docs')
APP = os.path.basename(os.environ.get('APP') or 'prototipo-aulas.html')
BAD = re.compile('[←-⇿⌀-⏿■-◿☀-➿⬀-⯿‹›«»️]|[\U0001F000-\U0001FAFF]')
falhas = []


def check(nome, ok, info=''):
    print(f"  {'ok  ' if ok else 'FALHA'}  {nome}{' — ' + str(info) if info else ''}")
    if not ok:
        falhas.append(nome)


class Quieto(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quieto, directory=os.path.abspath(DOCS)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/{APP}'
MOSTRA = "() => { const b = document.getElementById('btFw'); b.style.display = 'inline-flex'; }"
estado = {'status': 500, 'corpos': []}


def api(route):
    estado['corpos'].append(json.loads(route.request.post_data or 'null'))
    route.fulfill(status=estado['status'], content_type='application/json', body='{"ok":%s}' % ('true' if estado['status'] < 300 else 'false'))


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, locale='pt-BR')
    ctx.add_init_script("try{if(!sessionStorage.getItem('t203')){localStorage.clear();localStorage.setItem('fm1lang','pt');sessionStorage.setItem('t203','1')}}catch(_){}")
    ctx.route('**/api/cadastro', api)
    pg = ctx.new_page()
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(500)
    pg.evaluate(MOSTRA)
    pg.click('#btFw'); pg.wait_for_timeout(300)
    check('FLASH FM1 abre o modal e não sai do app', pg.is_visible('#caddlg') and pg.url.split('#')[0].endswith(APP), pg.url)
    check('CONTINUAR começa desligado', pg.is_disabled('#cadGo'))
    pg.fill('#cadNome', 'Ana Teste')
    check('só o nome: desligado', pg.is_disabled('#cadGo'))
    pg.fill('#cadEmail', 'ana@exemplo')
    pg.check('#cadOk')
    check('email inválido: desligado', pg.is_disabled('#cadGo'))
    pg.fill('#cadEmail', 'ana@exemplo.com')
    check('nome, email e consentimento: ligado', pg.is_enabled('#cadGo'))
    txt = pg.inner_text('#caddlg')
    check('sem emoji nem glifo de ícone no modal', not BAD.search(txt), BAD.findall(txt))

    estado['status'] = 500
    pg.click('#cadGo'); pg.wait_for_timeout(500)
    check('erro no envio: avisa e fica no app', 'Não deu para enviar' in pg.inner_text('#cadMsg') and pg.url.split('#')[0].endswith(APP), pg.inner_text('#cadMsg'))
    check('erro no envio: o navegador não marca como feito', pg.evaluate("localStorage.getItem('fm1cadastro')") is None)

    estado['status'] = 201
    with pg.expect_navigation():
        pg.click('#cadGo')
    pg.wait_for_timeout(300)
    c = estado['corpos'][-1]
    check('deu certo: segue para a instalação', 'instalar-firmware.html?de=app' in pg.url, pg.url)
    check('envia nome, email e consentimento', c and c['nome'] == 'Ana Teste' and c['email'] == 'ana@exemplo.com' and c['ok'] is True and c['site'] == '', c)
    check('lembra o cadastro', bool(pg.evaluate("localStorage.getItem('fm1cadastro')")))

    pg.goto(URL); pg.wait_for_timeout(500); pg.evaluate(MOSTRA)
    n = len(estado['corpos'])
    with pg.expect_navigation():
        pg.click('#btFw')
    check('depois do cadastro, o botão vai direto', 'instalar-firmware.html' in pg.url and len(estado['corpos']) == n, pg.url)
    pg.close()

    ctx2 = b.new_context(viewport={'width': 375, 'height': 812}, locale='en-US')
    ctx2.add_init_script("try{localStorage.setItem('fm1lang','en');localStorage.removeItem('fm1cadastro')}catch(_){}")
    pg = ctx2.new_page()
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(500); pg.evaluate(MOSTRA)
    pg.click('#btFw'); pg.wait_for_timeout(400)
    t = pg.inner_text('#caddlg')
    check('em inglês: modal traduzido', 'BEFORE INSTALLING' in t.upper() and 'CONTINUE TO INSTALL' in t.upper() and 'Nome' not in t, t[:120])
    r = pg.evaluate("(() => { const r = document.getElementById('caddlg').getBoundingClientRect(); return [r.left, r.right, innerWidth]; })()")
    check('celular 375: o modal cabe na tela', r[0] >= 0 and r[1] <= r[2], r)
    pg.screenshot(path=os.path.join(HERE, '..', 'build', 't203-cadastro-375-en.png'))
    pg.click('#cadX'); pg.wait_for_timeout(200)
    check('FECHAR fecha o modal', not pg.is_visible('#caddlg'))
    pg.close()
    check('sem erros de JavaScript', not erros, erros[:2])
    b.close()
srv.shutdown()
print('\nTUDO OK' if not falhas else f'\n{len(falhas)} FALHA(S): {falhas}')
sys.exit(1 if falhas else 0)
