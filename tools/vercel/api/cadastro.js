// © 2026 Wellington Saam. Todos os direitos reservados (FM1 Pocket Tutor, app web; ver LICENSING.md).
// T203: recebe o cadastro do modal do FLASH FM1 (nome, email, consentimento) e grava um JSON no Blob privado fm1-cadastros.
// Não guarda IP. Campo "site" é armadilha para robô: preenchido, responde ok e não grava.
import { put } from '@vercel/blob';
import { randomUUID } from 'node:crypto';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const txt = (v, n) => String(v ?? '').replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, n);

export default async function handler(req, res) {
  if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); return res.status(405).json({ ok: false }); }
  let b = req.body;
  if (typeof b === 'string') { try { b = JSON.parse(b); } catch { b = null; } }
  if (!b || typeof b !== 'object') return res.status(400).json({ ok: false, erro: 'corpo' });
  if (b.site) return res.status(201).json({ ok: true });
  const nome = txt(b.nome, 80), email = txt(b.email, 120).toLowerCase();
  if (nome.length < 2 || !EMAIL.test(email) || b.ok !== true) return res.status(400).json({ ok: false, erro: 'dados' });
  const quando = new Date().toISOString();
  const reg = { nome, email, quando, consentimento: true, idioma: txt(b.idioma, 5), firmware: txt(b.firmware, 20), fm1: txt(b.fm1, 40) };
  try {
    await put(`cadastros/${quando.slice(0, 10)}/${quando.replace(/[:.]/g, '-')}-${randomUUID().slice(0, 8)}.json`,
      JSON.stringify(reg), { access: 'private', contentType: 'application/json', addRandomSuffix: false });
  } catch (e) {
    console.error('cadastro', e && e.message);
    return res.status(500).json({ ok: false, erro: 'gravar' });
  }
  return res.status(201).json({ ok: true });
}
