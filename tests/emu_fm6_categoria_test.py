#!/usr/bin/env python3
"""T173: FM6 in fm1-emu. (1) the app's lines (a MODULE frame 'L', one per own voice) replace "FM6 n OF 24" on the
voice line; (2) the PRESETS knob sends Bank Select 0 + Program Change to the computer, so the app follows the voice.
  ./build.sh --no-package && tests/emu_fm6_categoria_test.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import emu_test as E  # noqa: E402
from PIL import Image  # noqa: E402

fail = []


def ok(name, cond, why):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}: {why}")
    if not cond:
        fail.append(name)


def line_px(case):
    """the voice line (y 28..44) of the LCD as bytes: to compare two runs"""
    s = E.OUT / case / "screen.png"
    img = Image.open(s).convert("RGB") if s.exists() else Image.open(E.OUT / case / "panel.png").convert("RGB").crop((370, 42, 850, 522)).resize((240, 240))
    return img.crop((0, 28, 240, 44)).tobytes(), img


import hbdeploy  # noqa: E402
names = {1: "TINE EP", 7: "ORGAN"}
cat = ["OTHER"] + ["KEYS"] * 24
lines = [f"{cat[i]} #{i}" for i in range(25)]
lab = b"L" + b"".join(x.encode() + b"\0" for x in lines)
f = hbdeploy.frame(hbdeploy.MODULE, 1, lab)
base = E.pick("FM6")
E.run("fm6cat_off", base, 1900)
E.run("fm6cat_on", base + f",1500:m{f.hex()}", 1900)
a, ia = line_px("fm6cat_off")
b, ib = line_px("fm6cat_on")
ib.save(E.OUT / "fm6cat_on" / "lcd.png")
ok("fm6cat_line", a != b, "the app's line ('KEYS #1') replaces 'FM6 1 OF 24' (see build/emu/fm6cat_on/lcd.png)")

# PRESETS: 6 clicks right from TINE EP (1) -> 7 (ORGAN): CC 0 = 0 and Program Change 7 to the computer
E.run("fm6cat_knob", base + ",1500:e6:6", 2200, extra=("--usb",))
out = E.midi_out("fm6cat_knob")
pcs = [(s, d1) for s, d1, _ in out if s & 0xF0 == 0xC0]
ok("fm6cat_pc", (0xC0, 7) in pcs and any(s == 0xB0 and d1 == 0 for s, d1, _ in out),
   f"the knob sends Bank Select 0 and Program Change 7 (sent: {[(hex(s), d1, d2) for s, d1, d2 in out][-6:]})")

# T179: with the app's order ('O'), PRESETS walks it: from TINE EP (1), five clicks right -> 9, 14, 7, 15, 5
order = [1, 9, 14, 7, 15, 5, 16, 17, 19, 8, 4, 10, 21, 2, 12, 6, 13, 20, 22, 24, 3, 11, 23, 18, 0]
fo = hbdeploy.frame(hbdeploy.MODULE, 2, bytes([0x4F] + order))
E.run("fm6cat_order", base + f",1400:m{fo.hex()},1700:e6:5", 2400, extra=("--usb",))
pcs = [d1 for s, d1, _ in E.midi_out("fm6cat_order") if s & 0xF0 == 0xC0]
idx = [order.index(x) for x in pcs]
ok("fm6cat_order", pcs and pcs[-1] == 5 and idx == sorted(idx) and len(set(idx)) == len(idx),
   f"PRESETS walks the app's order and ends on PAD (5), five steps from TINE EP (program changes {pcs}; clicks close together come as one event)")
E.run("fm6cat_order_back", base + f",1400:m{fo.hex()},1700:e6:-1", 2400, extra=("--usb",))
pcs = [d1 for s, d1, _ in E.midi_out("fm6cat_order_back") if s & 0xF0 == 0xC0]
ok("fm6cat_order_first", pcs and pcs[-1] == 0, f"T184: left of the first (TINE EP) it loops to the last, INIT (program changes {pcs})")
E.run("fm6cat_order_wrap", base + f",1400:m{fo.hex()},1700:e6:-1,1900:e6:1", 2400, extra=("--usb",))
pcs = [d1 for s, d1, _ in E.midi_out("fm6cat_order_wrap") if s & 0xF0 == 0xC0]
ok("fm6cat_order_wrap", pcs[-2:] == [0, 1], f"T184: and from the last (INIT) right again to the first, TINE EP (program changes {pcs})")

# a Program Change from the app (MIDI in) does not come back (no loop)
E.run("fm6cat_pcin", base + ",1500:mc007", 2200, extra=("--usb",))
out = E.midi_out("fm6cat_pcin")
ok("fm6cat_noecho", not any(s & 0xF0 == 0xC0 for s, _, _ in out), "a Program Change from the app is not sent back")
print("\ntudo certo" if not fail else "falhas: " + ", ".join(fail))
sys.exit(1 if fail else 0)
