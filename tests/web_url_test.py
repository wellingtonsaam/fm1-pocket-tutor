#!/usr/bin/env python3
"""T154: a URL guarda a tela (#/7-musicas/shape-of-you?vista=...): recarregar volta ao mesmo lugar, o Voltar do navegador volta uma tela.

    python3 tests/web_url_test.py            (precisa de playwright com o Chromium)
"""
import os,sys
from playwright.sync_api import sync_playwright
APP='file://'+os.path.abspath(os.environ.get('APP') or os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','docs','prototipo-aulas.html')); ok=True
def chk(n,c,i=''):
    global ok; print(('ok   ' if c else 'FALHA'),n,i); ok&=bool(c)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1600,'height':1000},locale='pt-BR'); er=[]
    pg.on('pageerror',lambda e:er.append(str(e)[:150]))
    pg.goto(APP); pg.evaluate("localStorage.clear()"); pg.goto(APP); pg.wait_for_timeout(400)
    H=lambda: pg.evaluate("decodeURIComponent(location.hash)")
    chk('início', H()=='#/', H())
    pg.click('[data-act="cat:all"]'); pg.wait_for_timeout(200); chk('catálogo 7 · Músicas', H()=='#/7-musicas', H())
    pg.evaluate("()=>document.querySelector('[data-act^=\"open:8.15\"]')?.click()||openLesson('8.15')"); pg.wait_for_timeout(300)
    chk('Shape of You', H()=='#/7-musicas/shape-of-you?vista=midi&aba=arranjo&parte=1', H())
    pg.evaluate("()=>document.querySelector('[data-act=\"part:2\"]')?.click()"); pg.wait_for_timeout(200)
    pg.evaluate("()=>document.querySelector('[data-act=\"pview:frases\"]').click()"); pg.wait_for_timeout(300)
    chk('vista Notas, parte 3', H()=='#/7-musicas/shape-of-you?vista=notas&aba=arranjo&parte=3', H())
    st=pg.evaluate("()=>({s:S.screen,id:S.lesson.id,part:S.part,v:CFG.view,mod:S.mod})")
    pg.reload(); pg.wait_for_timeout(500)
    st2=pg.evaluate("()=>({s:S.screen,id:S.lesson&&S.lesson.id,part:S.part,v:CFG.view,mod:S.mod})")
    chk('recarregar volta à mesma tela', st==st2, (st,st2))
    pg.go_back(); pg.wait_for_timeout(400); chk('Voltar do navegador: catálogo', H()=='#/7-musicas' and pg.evaluate("S.screen")=='catalog', H())
    pg.go_back(); pg.wait_for_timeout(400); chk('Voltar de novo: início', pg.evaluate("S.screen")=='home', H())
    pg.goto(APP+'#/1-geografia-do-teclado/ache-os-dos'); pg.reload(); pg.wait_for_timeout(400)
    chk('lição pela URL', pg.evaluate("[S.screen,S.lesson&&S.lesson.id]")==['intro','1.1'], (pg.evaluate("[S.screen,S.lesson&&S.lesson.id]"),H()))
    pg.goto(APP+'#/7-musicas/nao-existe'); pg.reload(); pg.wait_for_timeout(400)
    chk('música que não existe: início', pg.evaluate("S.screen")=='home', H())
    chk('sem erros de JavaScript', not er, er); b.close()
sys.exit(0 if ok else 1)
