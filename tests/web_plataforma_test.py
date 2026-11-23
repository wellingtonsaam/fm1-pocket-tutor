#!/usr/bin/env python3
"""T156: os botões TECLADO e SOM com o nome da plataforma (Mac, Windows, Linux; só TECLADO/SOM no Android, ChromeOS, iPad), em pt, en e es.

    python3 tests/web_plataforma_test.py            (precisa de playwright com o Chromium)
"""
import os,sys
from playwright.sync_api import sync_playwright
APP='file://'+os.path.abspath(os.environ.get('APP') or os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','docs','prototipo-aulas.html')); ok=True
def chk(n,c,i=''):
    global ok; print(('ok   ' if c else 'FALHA'),n,i); ok&=bool(c)
CASOS=[('Mac','Macintosh; Intel Mac OS X 10_15_7','MacIntel',0,'Teclado Mac','Som Mac'),
       ('Windows','Windows NT 10.0; Win64; x64','Win32',0,'Teclado Windows','Som Windows'),
       ('Linux','X11; Linux x86_64','Linux x86_64',0,'Teclado Linux','Som Linux'),
       ('Android','Linux; Android 14; Pixel 8','Linux armv8l',5,None,'Som Android'),
       ('ChromeOS','X11; CrOS x86_64 14541.0.0','Linux x86_64',0,'Teclado','Som'),
       ('iPad','Macintosh; Intel Mac OS X 10_15_7','MacIntel',5,'Teclado','Som')]
with sync_playwright() as p:
    b=p.chromium.launch(); er=[]
    for nome,ua,plat,touch,tk,sd in CASOS:
        ctx=b.new_context(user_agent=f'Mozilla/5.0 ({ua}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',locale='pt-BR',viewport={'width':1600,'height':1000})
        ctx.add_init_script(f"Object.defineProperty(navigator,'platform',{{get:()=>'{plat}'}});Object.defineProperty(navigator,'userAgentData',{{get:()=>undefined}});Object.defineProperty(navigator,'maxTouchPoints',{{get:()=>{touch}}});")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:er.append(str(e)[:150])); pg.goto(APP); pg.wait_for_timeout(300)
        r=pg.evaluate("()=>[document.querySelector('#tgPc .tgl-l').textContent,document.querySelector('#tgSnd .tgl-l').textContent,document.getElementById('tgPc').title]")
        vis=pg.evaluate("()=>{const e=document.getElementById('tgPc');return !e.hidden&&getComputedStyle(e).display!=='none'}")
        chk(nome, (vis if tk else not vis) and (r[0]==tk if tk else True) and r[1]==sd and 'computador' in r[2], (r,'teclado visível' if vis else 'teclado escondido')); ctx.close()
    ctx=b.new_context(locale='en-US',user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/130.0',viewport={'width':1600,'height':1000})
    ctx.add_init_script("Object.defineProperty(navigator,'platform',{get:()=>'MacIntel'});Object.defineProperty(navigator,'userAgentData',{get:()=>undefined})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:er.append(str(e)[:150])); pg.goto(APP); pg.wait_for_timeout(300)
    for lang,tk,sd in (('en','Mac keyboard','Mac sound'),('es','Teclado Mac','Sonido Mac'),('pt','Teclado Mac','Som Mac')):
        pg.evaluate(f"()=>setLang('{lang}')"); pg.wait_for_timeout(150)
        r=pg.evaluate("()=>[document.querySelector('#tgPc .tgl-l').textContent,document.querySelector('#tgSnd .tgl-l').textContent]")
        chk('idioma '+lang, r==[tk,sd], r)
    chk('sem erros de JavaScript', not er, er); b.close()
sys.exit(0 if ok else 1)
