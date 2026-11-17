// The Messages page's shareable link: message text and options <-> URL hash query. Everything decoded is checked
// (known fonts/modes/scenes, colours as 6 hex digits, numbers clamped, text length limited); the page only ever
// inserts it with esc()/textContent, so a link cannot inject HTML.
import { FONTS, COLOR_MODES, MAX_CHARS } from './fw_text.js';
import { OPENERS } from './fw_message_show.js';

export const BGS = ['Cityscape', 'Beach', 'Mountains', 'Forest', 'Night Sky', 'None'];
const hex = s => (/^[0-9a-f]{6}$/i.test(s || '') ? '#' + s : null);
const clamp = (v, lo, hi, d) => (Number.isFinite(+v) && v !== '' ? Math.min(hi, Math.max(lo, +v)) : d);

export function decodeQuery(q) {
  return {
    text: String(q.m ?? 'Happy New Year!\n\n2027').slice(0, MAX_CHARS * 6), name: String(q.n ?? '').slice(0, 30),
    font: FONTS[q.f] ? q.f : 'sans', mode: COLOR_MODES[q.c] ? q.c : 'rainbow',
    c1: hex(q.c1) || '#ffc83d', c2: hex(q.c2) || '#5cc8ff', size: clamp(q.s, 40, 100, 85), hold: clamp(q.h, 1, 8, 3),
    bg: BGS.includes(q.bg) ? q.bg : 'Cityscape',
    opener: Object.hasOwn(OPENERS, q.o ?? '') ? q.o : 'short', finale: q.fin === '1',
  };
}
export function encodeQuery(o) {
  const p = new URLSearchParams({ m: o.text, f: o.font, c: o.mode, s: o.size, h: o.hold, bg: o.bg });
  if (o.name) p.set('n', o.name);
  if (o.opener !== 'short') p.set('o', o.opener);
  if (o.finale) p.set('fin', '1');
  if (o.mode === 'single' || o.mode === 'gradient') { p.set('c1', o.c1.slice(1)); if (o.mode === 'gradient') p.set('c2', o.c2.slice(1)); }
  return '#/messages?' + p.toString().replace(/\+/g, '%20');
}


// Seed of a message show from its link (FNV-1a): the same link always plays the same show.
export function showSeed(hash) {
  let h = 0x811c9dc5;
  for (const ch of String(hash)) { h ^= ch.codePointAt(0); h = Math.imul(h, 0x01000193) >>> 0; }
  return h;
}
