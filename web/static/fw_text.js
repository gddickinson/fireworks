// Text for message shells: the message is drawn with a real font on an offscreen canvas, wrapped and fitted to the
// sky, and evenly spaced dots are picked from the letter shapes (a staggered grid over the inked pixels). Each dot
// becomes a star (fw_shells.js "message") that bursts out, glides into place, holds, sparkles and falls.
// Any Unicode the browser's fonts can draw works (accents, non-Latin scripts); emoji are drawn and sampled as
// silhouettes; characters without a glyph come out as whatever the font shows for them (usually a box or nothing).
import { FOCAL } from './fw_pyro.js';
import { PALETTE, SHOW_COLORS } from './fw_palette.js';

export const FONTS = {
  sans: ['Bold sans', '800 PXpx system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'],
  serif: ['Serif', '700 PXpx Georgia, "Times New Roman", Times, serif'],
  script: ['Script', 'italic 700 PXpx "Snell Roundhand", "Segoe Script", "Brush Script MT", "Apple Chancery", cursive'],
  rounded: ['Rounded', '800 PXpx "Arial Rounded MT Bold", "Varela Round", "Nunito", system-ui, sans-serif'],
  mono: ['Typewriter', '700 PXpx ui-monospace, Menlo, Consolas, "Courier New", monospace'],
};
export const COLOR_MODES = { rainbow: 'Rainbow', letter: 'A colour per letter', gradient: 'Gradient (two colours)', single: 'One colour' };
export const MAX_CHARS = 80, MAX_MESSAGES = 6;

// Printable text only, at most MAX_CHARS characters (code points), lines trimmed.
export function cleanText(s) {
  const t = String(s ?? '').replace(/[\u0000-\u0009\u000B-\u001F\u007F]/g, '').replace(/\r/g, '');
  return [...t].slice(0, MAX_CHARS).join('').split('\n').map(l => l.trim()).filter(Boolean).join('\n');
}
// Split the text area into the messages of a sequence (blank line between messages).
export function splitMessages(s) {
  return String(s ?? '').replace(/\r/g, '').split(/\n\s*\n/).map(cleanText).filter(Boolean).slice(0, MAX_MESSAGES);
}

const graphemes = s => (typeof Intl !== 'undefined' && Intl.Segmenter
  ? [...new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(s)].map(x => x.segment) : [...s]);

// Wrap words into at most n lines of roughly equal length (explicit newlines kept).
export function wrapLines(text, n) {
  const out = [];
  for (const para of text.split('\n')) {
    const words = para.split(/\s+/).filter(Boolean), total = [...para].length, target = Math.ceil(total / n);
    let line = '';
    for (const w of words) {
      if (line && [...line].length + 1 + [...w].length / 2 > target) { out.push(line); line = w; } else line = line ? line + ' ' + w : w;
    }
    if (line) out.push(line);
  }
  return out;
}

const hsv = (h, s, v) => {
  const f = (n, k = (n + h * 6) % 6) => v - v * s * Math.max(0, Math.min(k, 4 - k, 1));
  return [f(5) * 255, f(3) * 255, f(1) * 255].map(Math.round);
};

// Points [u, v, r, g, b] in metres around the message centre (v up) for a view of this aspect and horizon.
// opts: { font, mode, color, color2, size (0.4-1), density (stars per message, about), measure (canvas factory) }
export function textPoints(text, aspect, horizon, opts = {}) {
  const { font = 'sans', mode = 'rainbow', color = [255, 200, 80], color2 = [80, 160, 255], size = 0.85, density = 520 } = opts;
  const PX = 96, spec = (FONTS[font] || FONTS.sans)[1].replace('PX', PX);
  const cv = document.createElement('canvas'), c = cv.getContext('2d', { willReadFrequently: true });
  c.font = spec;
  const z = 450, widthM = 0.86 * z * aspect / FOCAL * size, heightM = 0.62 * z * horizon / FOCAL * size;
  let best = null;
  const paras = text.split('\n').length;
  for (let n = 1; n <= 4; n++) {                              // choose the wrapping that lets the letters be biggest
    const lines = n === 1 ? text.split('\n') : wrapLines(text, n);
    if (n > 1 && lines.length <= paras) continue;
    const w = Math.max(...lines.map(l => c.measureText(l).width)), h = lines.length * PX * 1.15;
    const k = Math.min(widthM / w, heightM / h);
    if (!best || k > best.k * 1.08) best = { lines, w, h, k };
  }
  const { lines, w, h, k } = best, pad = 8;
  cv.width = Math.ceil(w + 2 * pad); cv.height = Math.ceil(h + 2 * pad);
  c.font = spec; c.textBaseline = 'middle'; c.textAlign = 'center'; c.fillStyle = '#fff';
  const lineY = i => pad + (i + 0.5) * PX * 1.15;
  lines.forEach((l, i) => c.fillText(l, cv.width / 2, lineY(i)));
  const img = c.getImageData(0, 0, cv.width, cv.height).data, W = cv.width;
  let ink = 0;
  for (let i = 3; i < img.length; i += 4) if (img[i] > 128) ink++;
  if (!ink) return { points: [], lines };
  const step = Math.max(1.5, Math.sqrt(ink / density));
  // grapheme boundaries per line (for per-letter colours)
  c.textAlign = 'left';
  const bounds = lines.map(l => {
    const g = graphemes(l), lw = c.measureText(l).width, x0 = cv.width / 2 - lw / 2, xs = [];
    let acc = '';
    for (const ch of g) { acc += ch; xs.push(x0 + c.measureText(acc).width); }
    return { xs, letters: g.map(ch => ch.trim() ? 1 : 0) };
  });
  const pts = [];
  let row = 0;
  for (let y = step / 2; y < cv.height; y += step * 0.866, row++) {
    for (let x = (row % 2 ? step / 2 : 0) + step / 4; x < W; x += step) {
      if (img[(Math.floor(y) * W + Math.floor(x)) * 4 + 3] < 128) continue;
      const li = Math.min(lines.length - 1, Math.max(0, Math.floor((y - pad) / (PX * 1.15))));
      const t = x / W;
      let col;
      if (mode === 'single') col = color;
      else if (mode === 'gradient') col = color.map((v, i) => Math.round(v + (color2[i] - v) * t));
      else if (mode === 'letter') {
        const b = bounds[li], gi = Math.max(0, b.xs.findIndex(e => x < e)), n = b.letters.slice(0, gi + 1).reduce((a, v) => a + v, 0);
        col = PALETTE[SHOW_COLORS[(n + li * 3) % SHOW_COLORS.length]];
      } else col = hsv((t * 0.85 + li * 0.13) % 1, 0.75, 1);
      pts.push([(x - W / 2) * k, (cv.height / 2 - y) * k, col[0], col[1], col[2]]);
    }
  }
  return { points: pts, lines, scale: k };
}
