#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""FM1 Pocket Tutor: copia para docs/presets os presets do FM6 salvos com o botão SAVE do FM-1.

O FM6 escreve cada SAVE no log do FM-1: "fm6 up# N" (o número do preset USER N) e 35 linhas "fm6 upw XXXXXXXX"
(o registro de 140 bytes: a voz DX7 compactada (128), os 7 macros, o modo, o motor e o bend). Esta ferramenta lê
o log, monta cada preset e grava docs/presets/fm6-user-NN.md, .json e .syx (uma voz DX7 VCED, que volta ao FM6 com
`tools/dock.py send` e abre no Dexed). Vale o último SAVE de cada número.

  tools/fm6_presets.py [--port "FM1 Pocket Tutor"]     lê o log do FM-1 (tools/dock.py logs)
  tools/fm6_presets.py --log ARQUIVO                    lê um log salvo (ex.: a saída do emulador)
"""
import argparse
import datetime
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
OUT = SRC / "docs" / "presets"
WAVE = ["TRIANGLE", "SAW DOWN", "SAW UP", "SQUARE", "SINE", "S&H"]
MODE = ["POLY", "MONO", "LEGATO"]
ENGINE = ["MODERN", "MARK I", "OPL"]
MACROS = ["ALG", "FB", "BRIGHTNESS (MLVL)", "MRAT", "MOD ENV (MEG)", "VMOD", "DTUN"]


def unpack_voice(pk):
    """voz DX7 compactada (128 bytes, formato VMEM) -> os 155 bytes da voz (VCED)"""
    v = []
    for op in range(6):                         # operador 6 primeiro, 17 bytes cada
        p = pk[op * 17:(op + 1) * 17]
        v += list(p[0:11])                      # R1-4, L1-4, BP, LD, RD
        v += [p[11] & 3, p[11] >> 2 & 3]       # LC, RC
        v += [p[12] & 7]                        # RS
        v += [p[13] & 3, p[13] >> 2 & 7]       # AMS, KVS
        v += [p[14], p[15] & 1, p[15] >> 1 & 31, p[16]]   # OL, M, FC, FF
        v += [p[12] >> 3 & 15]                  # DET
    g = pk[102:128]
    v += list(g[0:8])                           # PR1-4, PL1-4
    v += [g[8] & 31, g[9] & 7, g[9] >> 3 & 1]  # ALG, FB, OKS
    v += [g[10], g[11], g[12], g[13]]          # LFS, LFD, LPMD, LAMD
    v += [g[14] & 1, g[14] >> 1 & 7, g[14] >> 4 & 7]   # LFKS, LFW, LPMS
    v += [g[15]]                                # TRNSP
    v += list(g[16:26])                         # nome
    assert len(v) == 155
    return v


def read_log(a):
    if a.log:
        return Path(a.log).read_text(errors="replace")
    cmd = [sys.executable, str(SRC / "tools" / "dock.py"), "logs"] + (["--port", a.port] if a.port else [])
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace").stdout


def parse(text):
    presets, cur, words = {}, None, []
    for line in text.splitlines():
        m = re.search(r"fm6 up# ([0-9a-fA-F]{8})", line)
        if m:
            cur, words = int(m[1], 16), []
            continue
        m = re.search(r"fm6 upw ([0-9a-fA-F]{8})", line)
        if m and cur is not None:
            words.append(int(m[1], 16))
            if len(words) == 35:
                presets[cur] = struct.pack("<35I", *words)
                cur = None
    return presets


def save(n, raw, now):
    pk, e = raw[:128], list(struct.unpack("7b", raw[128:135]))
    mode, engine, bend = raw[135], raw[136], raw[137]
    v = unpack_voice(pk)
    name = bytes(v[145:155]).decode("latin-1").strip() or "SEM NOME"
    base = OUT / f"fm6-user-{n:02d}"
    syx = bytes([0xF0, 0x43, 0x00, 0x00, 0x01, 0x1B]) + bytes(v) + bytes([(-sum(v)) & 0x7F, 0xF7])
    base.with_suffix(".syx").write_bytes(syx)
    ops = []
    for k in range(6):
        o = v[k * 21:(k + 1) * 21]
        ops.append({"op": 6 - k, "rates": o[0:4], "levels": o[4:8], "output_level": o[16], "osc_mode": o[17],
                    "coarse": o[18], "fine": o[19], "detune": o[20] - 7})
    data = {"name": f"USER {n}", "voice_name": name, "module": "FM6 (Melodee)", "copied_at": now,
            "main": {"K1_algorithm": v[134] + 1, "K2_feedback": v[135], "K3_brightness": e[2], "K4_mod_env": e[4]},
            "macros": dict(zip(MACROS, e)), "mode": MODE[mode % 3], "engine": ENGINE[engine % 3], "bend_st": bend,
            "transpose_st": v[144] - 24, "operators": ops,
            "lfo": {"speed": v[137], "delay": v[138], "pitch_depth": v[139], "amp_depth": v[140], "wave": WAVE[v[142] % 6]},
            "voice_vced_155": v}
    base.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    md = [f"# Preset FM6 · USER {n} · {name}", "",
          f"Copiado do FM-1 em {now} (salvo com o botão SAVE no FM6). Modo {data['mode']}, motor {data['engine']}, bend {bend} semitons.", "",
          "## Página MAIN (knobs)", "", "| Knob | Controle | Valor |", "|---|---|---|",
          f"| K1 | ALGORITHM | {v[134] + 1} |", f"| K2 | FEEDBACK | {v[135]} |",
          f"| K3 | BRIGHTNESS | {e[2]:+d} |", f"| K4 | MOD ENV | {e[4]:+d} |", "",
          "## Operadores", "", "| OP | LEVEL | RATIO (coarse, fine) | DETUNE | ATTACK · DECAY · SUSTAIN LVL · RELEASE |", "|---|---|---|---|---|"]
    for o in sorted(ops, key=lambda x: x["op"]):
        md.append(f"| OP{o['op']} | {o['output_level']} | {o['coarse']}, {o['fine']}{' (fixo)' if o['osc_mode'] else ''} | "
                  f"{o['detune']:+d} | {o['rates'][0]} · {o['rates'][1]} · {o['levels'][2]} · {o['rates'][3]} |")
    lf = data["lfo"]
    md += ["", "## LFO", "", f"SPEED {lf['speed']} · DELAY {lf['delay']} · PITCH DEPTH {lf['pitch_depth']} · WAVE {lf['wave']}", "",
           "## Como usar", "",
           f"- **No FM-1:** o preset continua lá: gire PRESETS até **USER {n}** (com os macros, o modo e o motor).",
           f"- **Em outro FM-1:** `python3 tools/dock.py send docs/presets/{base.name}.syx` (a voz; os macros K3/K4 à mão).",
           "- **No computador:** o `.syx` é uma voz DX7 (VCED) e abre no Dexed."]
    base.with_suffix(".md").write_text("\n".join(md) + "\n")
    return base.name, name, data["main"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="porta MIDI do FM-1 (parte do nome)")
    ap.add_argument("--log", help="um log já salvo, em vez de ler o FM-1")
    a = ap.parse_args()
    presets = parse(read_log(a))
    if not presets:
        print("nenhum preset no log: aperte SAVE no FM6 e rode de novo (o log guarda os últimos eventos)")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for n in sorted(presets):
        f, name, main_ = save(n, presets[n], now)
        print(f"USER {n}: {name} -> docs/presets/{f}.md/.json/.syx  {main_}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
