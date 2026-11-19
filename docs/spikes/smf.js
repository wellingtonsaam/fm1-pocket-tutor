// SPDX-License-Identifier: GPL-3.0-only
// FM1 Pocket Tutor · leitor e escritor de MIDI padrão (SMF, formatos 0 e 1) para os spikes F2 e F3.
'use strict';
const SMF = (() => {
  function read(buf) {
    const d = new DataView(buf instanceof ArrayBuffer ? buf : buf.buffer), u8 = new Uint8Array(d.buffer);
    const str = (o, n) => String.fromCharCode(...u8.slice(o, o + n));
    if (str(0, 4) !== 'MThd') throw new Error('não é um arquivo MIDI (falta MThd)');
    const fmt = d.getUint16(8), ntr = d.getUint16(10), div = d.getUint16(12);
    if (div & 0x8000) throw new Error('MIDI com tempo SMPTE: não suportado neste spike');
    const out = { format: fmt, ppq: div, tempos: [], timesigs: [], markers: [], keysig: null, tracks: [] };
    let p = 8 + d.getUint32(4);
    for (let t = 0; t < ntr && p < u8.length; t++) {
      if (str(p, 4) !== 'MTrk') break;
      const len = d.getUint32(p + 4); let q = p + 8, end = q + len, tick = 0, rs = 0;
      const tr = { name: '', notes: [], channels: new Set(), program: null }, open = {};
      const vlq = () => { let v = 0, b; do { b = u8[q++]; v = (v << 7) | (b & 127); } while (b & 128); return v; };
      while (q < end) {
        tick += vlq(); let s = u8[q];
        if (s & 0x80) q++; else s = rs;
        if (s === 0xFF) {
          const type = u8[q++], n = vlq(), data = u8.slice(q, q + n); q += n;
          const txt = () => new TextDecoder('latin1').decode(data);
          if (type === 0x51) out.tempos.push({ tick, bpm: 60000000 / ((data[0] << 16) | (data[1] << 8) | data[2]) });
          else if (type === 0x58) out.timesigs.push({ tick, num: data[0], den: 1 << data[1] });
          else if (type === 0x06) out.markers.push({ tick, text: txt() });
          else if (type === 0x03 && !tr.name) tr.name = txt();
          else if (type === 0x59) out.keysig = { sf: (data[0] << 24) >> 24, minor: !!data[1] };
          continue;
        }
        if (s === 0xF0 || s === 0xF7) { const n = vlq(); q += n; continue; }
        rs = s; const ty = s & 0xF0, ch = s & 15, a = u8[q++], b = (ty === 0xC0 || ty === 0xD0) ? 0 : u8[q++];
        if (ty === 0x90 && b) { (open[ch * 128 + a] = open[ch * 128 + a] || []).push({ tick, vel: b }); tr.channels.add(ch); }
        else if (ty === 0x80 || (ty === 0x90 && !b)) { const st = (open[ch * 128 + a] || []).shift(); if (st) tr.notes.push({ n: a, t: st.tick, d: Math.max(1, tick - st.tick), v: st.vel, ch }); }
        else if (ty === 0xC0 && tr.program === null) tr.program = a;
      }
      tr.notes.sort((x, y) => x.t - y.t || x.n - y.n);
      tr.channels = [...tr.channels];
      out.tracks.push(tr); p = end;
    }
    return out;
  }
  /** Escreve um SMF formato 1. tracks: [{name, events:[{t, data:[...]}]}] (t em ticks absolutos). */
  function write(ppq, tracks) {
    const bytes = [], push = (...b) => bytes.push(...b);
    const u32 = v => [(v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255], u16 = v => [(v >> 8) & 255, v & 255];
    const vlq = v => { const o = [v & 127]; while ((v >>= 7)) o.unshift((v & 127) | 128); return o; };
    push(...[77, 84, 104, 100], ...u32(6), ...u16(1), ...u16(tracks.length), ...u16(ppq));
    for (const tr of tracks) {
      const ev = [...tr.events].sort((a, b) => a.t - b.t), body = [];
      if (tr.name) { const nm = [...new TextEncoder().encode(tr.name)]; body.push(0, 0xFF, 0x03, ...vlq(nm.length), ...nm); }
      let last = 0; for (const e of ev) { body.push(...vlq(e.t - last), ...e.data); last = e.t; }
      body.push(0, 0xFF, 0x2F, 0);
      push(...[77, 84, 114, 107], ...u32(body.length), ...body);
    }
    return new Uint8Array(bytes);
  }
  const meta = (type, data) => [0xFF, type, data.length, ...data];
  const text = s => [...new TextEncoder().encode(s)];

  /** Acorde provável de um conjunto de notas (classes 0..11 com peso). */
  const TPL = [['', [0, 4, 7]], ['m', [0, 3, 7]], ['7', [0, 4, 7, 10]], ['m7', [0, 3, 7, 10]], ['maj7', [0, 4, 7, 11]], ['dim', [0, 3, 6]], ['sus4', [0, 5, 7]]];
  const NM = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];
  function guessChord(w, bass) {
    let best = null;
    for (let r = 0; r < 12; r++) for (const [q, iv] of TPL) {
      const set = iv.map(i => (r + i) % 12); let s = 0;
      for (let pc = 0; pc < 12; pc++) s += set.includes(pc) ? w[pc] : -0.6 * w[pc];
      s -= set.filter(pc => !w[pc]).length * 0.4 * Math.max(...w);
      if (bass != null && bass === r) s += 0.3 * Math.max(...w);
      if (iv.length === 4) s -= 0.15 * Math.max(...w);
      if (!best || s > best.s) best = { s, name: NM[r] + q };
    }
    return best && best.s > 0 ? best.name : null;
  }
  return { read, write, meta, text, guessChord };
})();
