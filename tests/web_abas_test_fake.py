"""FM-1 MIDI simulado (o mesmo de web_abas_test.py)."""
FAKE_MIDI = """
(() => {
  const sent = [];
  const input = { id: 'in1', name: 'FM1 Pocket Tutor', type: 'input', state: 'connected', onmidimessage: null,
                  addEventListener() {}, removeEventListener() {} };
  const output = { id: 'out1', name: 'FM1 Pocket Tutor', type: 'output', state: 'connected',
                   send(d) { sent.push(Array.from(d)); }, addEventListener() {}, removeEventListener() {} };
  window.__fm1 = { sent, input,
    key(n, on) { if (input.onmidimessage) input.onmidimessage({ data: new Uint8Array([on ? 0x90 : 0x80, n, on ? 100 : 0]) }); } };
  navigator.requestMIDIAccess = async () => ({ inputs: new Map([['in1', input]]), outputs: new Map([['out1', output]]),
    sysexEnabled: true, onstatechange: null, addEventListener() {}, removeEventListener() {} });
})();
"""
