#!/usr/bin/env python3
"""T155: o botão Próxima nota (barra do piano, OFF por padrão) liga e desliga a luz fraca da próxima nota no app e no FM-1.

    python3 tests/web_proxima_nota_test.py            (precisa de playwright com o Chromium)
"""
import os,sys
from playwright.sync_api import sync_playwright
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'web_abas_test.py')).read(); FAKE=src.split('FAKE_MIDI = """')[1].split('"""')[0]
APP='file://'+os.path.abspath(os.environ.get('APP') or os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','docs','prototipo-aulas.html')); ok=True
def chk(n,c,i=''):
    global ok; print(('ok   ' if c else 'FALHA'),n,i); ok&=bool(c)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1600,'height':1000},locale='pt-BR'); er=[]
    pg.on('pageerror',lambda e:er.append(str(e)[:150])); pg.add_init_script(FAKE)
    pg.goto(APP); pg.evaluate("localStorage.clear()"); pg.goto(APP); pg.wait_for_timeout(400)
    pg.click('#btFm'); pg.wait_for_timeout(300); pg.evaluate("()=>{__fm1.key(53,true);__fm1.key(53,false)}")
    chk('botão Próxima nota na barra, OFF', pg.evaluate("document.getElementById('tgNext')?.getAttribute('aria-pressed')")=='false')
    pg.evaluate("()=>{CFG.view='midi';CFG.pvTab='arr';openLesson('8.15');S.part=0;openSong(S.lesson)}"); pg.wait_for_timeout(300)
    pg.evaluate("()=>{__fm1.sent.length=0;document.querySelector('[data-act=\"pvpmel\"]').click()}"); pg.wait_for_timeout(500)
    led=lambda: pg.evaluate("()=>__fm1.sent.filter(m=>m[0]===0x9F).map(m=>m[1]+':'+m[2])")
    op=lambda n: pg.evaluate(f"()=>getComputedStyle(keyEl[{n}],'::after').opacity")
    l=led(); chk('OFF: FM-1 só com a nota de agora', l==['61:100'], l); chk('OFF: Mi4 sem luz fraca no app', op(64)=='0', op(64))
    pg.evaluate("()=>{__fm1.sent.length=0}"); pg.click('#tgNext'); pg.wait_for_timeout(300)
    l=led(); chk('ON: a luz fraca vai para o FM-1', '64:32' in l, l); chk('ON: Mi4 com luz fraca no app', abs(float(op(64))-.28)<.01, op(64))
    pg.evaluate("()=>{__fm1.sent.length=0}"); pg.click('#tgNext'); pg.wait_for_timeout(300)
    chk('OFF de novo: apaga a luz fraca do FM-1', pg.evaluate("()=>__fm1.sent.some(m=>m[0]===0x8F&&m[1]===64)"), pg.evaluate("()=>__fm1.sent.map(m=>m.join(' '))"))
    pg.reload(); pg.wait_for_timeout(400); pg.click('#tgNext'); pg.reload(); pg.wait_for_timeout(400)
    chk('a escolha fica guardada', pg.evaluate("document.getElementById('tgNext').getAttribute('aria-pressed')")=='true')
    chk('sem erros de JavaScript', not er, er); b.close()
sys.exit(0 if ok else 1)
