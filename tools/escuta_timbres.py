#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""FM1 Pocket Tutor (T24): escuta dos timbres do FM6 para o estudo de acordes.

Cada candidato toca a mesma sequência nas 27 teclas do FM-1 (Fá3 a Sol5): Dó, Lá menor, Fá e Sol em
posição fechada, e depois Dó arpejado. O número e o nome aparecem no terminal enquanto o timbre toca.
Troca o timbre por Program Change (o FM6: programa = voz, 0 INIT, 1..24 as vozes de fábrica). Não grava
nada na flash; no fim volta ao timbre 1 (TINE EP), o padrão de uma instalação nova.

  tools/escuta_timbres.py                     todos os candidatos
  tools/escuta_timbres.py 5 16 17             só esses números
  tools/escuta_timbres.py --todos             as 24 vozes, inclusive baixos e leads
  tools/escuta_timbres.py --lista             só mostra a lista, sem tocar
"""
import argparse
import sys
import time

# FM6: 0 INIT, 1..8 Melodee (melodee_fm6.h), 9..24 a ROM (eng_fm6_rom.h)
VOZES = ["INIT", "TINE EP", "BELL", "FM BASS", "BRASS", "PAD", "MARIMBA", "ORGAN", "PLUCK",
         "TINE EP (ROM)", "BRASS SECT", "SOLID BASS", "BELLS", "MARIMBA (ROM)", "CLAVINET", "DRAWBARS",
         "STRINGS", "GLASS PAD", "SYNC LEAD", "HARP", "KALIMBA", "FLUTE", "STEEL DRUM", "SAW BASS", "TUBULAR"]
# os que seguram um acorde: polifônicos, ataque claro, sem ser baixo nem lead
CANDIDATOS = [1, 9, 5, 7, 15, 14, 8, 16, 17, 19]
ACORDES = [("Dó", [60, 64, 67]), ("Lá menor", [57, 60, 64]), ("Fá", [53, 57, 60]), ("Sol", [55, 59, 62])]
ARPEJO = [60, 64, 67, 72, 76, 79]               # Dó até o Sol5, a tecla mais aguda
PORTA = "FM1 Pocket Tutor"


def abrir(nome):
    import mido
    for p in mido.get_output_names():
        if nome.lower() in p.lower():
            return mido.open_output(p)
    sys.exit(f"FM-1 não encontrado (porta '{nome}'). Portas: {', '.join(mido.get_output_names()) or 'nenhuma'}")


def tocar(out, n, dur=1.1, gap=0.15, vel=90):
    import mido
    out.send(mido.Message("program_change", program=n))
    time.sleep(0.25)
    for nome, notas in ACORDES:
        print(f"    {nome}", flush=True)
        for k in notas:
            out.send(mido.Message("note_on", note=k, velocity=vel))
        time.sleep(dur)
        for k in notas:
            out.send(mido.Message("note_off", note=k))
        time.sleep(gap)
    for k in ARPEJO:
        out.send(mido.Message("note_on", note=k, velocity=vel))
        time.sleep(0.22)
        out.send(mido.Message("note_off", note=k))
    time.sleep(1.0)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("vozes", nargs="*", type=int, help="números das vozes (0..24)")
    a.add_argument("--todos", action="store_true")
    a.add_argument("--lista", action="store_true")
    a.add_argument("--port", default=PORTA)
    o = a.parse_args()
    sel = o.vozes or (list(range(1, 25)) if o.todos else CANDIDATOS)
    if any(not 0 <= n < len(VOZES) for n in sel):
        sys.exit("os números vão de 0 a 24")
    if o.lista:
        for n in sel:
            print(f"{n:2d}  {VOZES[n]}")
        return
    out = abrir(o.port)
    try:
        for i, n in enumerate(sel, 1):
            print(f"[{i}/{len(sel)}] timbre {n}: {VOZES[n]}", flush=True)
            tocar(out, n)
    except KeyboardInterrupt:
        pass
    finally:
        import mido
        out.send(mido.Message("control_change", control=123, value=0))
        out.send(mido.Message("program_change", program=1))
        out.close()
    print("Fim. O FM-1 voltou ao timbre 1 (TINE EP).")


if __name__ == "__main__":
    main()
