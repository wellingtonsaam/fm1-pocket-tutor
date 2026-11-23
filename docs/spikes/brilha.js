// © 2026 Wellington Saam. Todos os direitos reservados (FM1 Pocket Tutor, app web; ver LICENSING.md).
// "Brilha brilha estrelinha" (melodia tradicional, domínio público), a música de exemplo dos spikes F2 e F3.
// Em tempos: a melodia (nota MIDI, duração), os acordes (cifra, duração) e as frases (nome, início, fim).
'use strict';
const BRILHA = (() => {
  const L = [[60,1],[60,1],[67,1],[67,1],[69,1],[69,1],[67,2]], M = [[65,1],[65,1],[64,1],[64,1],[62,1],[62,1],[60,2]],
        P = [[67,1],[67,1],[65,1],[65,1],[64,1],[64,1],[62,2]];
  const melody = [...L, ...M, ...P, ...P, ...L, ...M];
  const cA = [['C',2],['C',2],['F',2],['C',2],['F',2],['C',2],['G7',2],['C',2]], cB = [['C',2],['F',2],['C',2],['G7',2],['C',2],['F',2],['C',2],['G7',2]];
  const chords = [...cA, ...cB, ...cA];
  const phrases = [['Frase 1',0,8],['Frase 2',8,16],['Frase 3',16,24],['Frase 4',24,32],['Frase 5',32,40],['Frase 6',40,48]];
  return { title: 'Brilha brilha estrelinha', key: 'C', tempo: 96, time: [4,4], melody, chords, phrases };
})();
