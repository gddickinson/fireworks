// Copy of models/pyro_colors.py: pyrotechnic star colours and a burning star's colour/brightness over its life.
export const PALETTE = {
  red: [255, 38, 28], green: [64, 255, 96], blue: [52, 110, 255], purple: [190, 70, 255],
  yellow: [255, 226, 70], orange: [255, 128, 30], aqua: [60, 230, 255], pink: [255, 90, 190],
  gold: [255, 172, 68], silver: [226, 232, 255], white: [255, 250, 240],
};
export const SHOW_COLORS = ['red', 'green', 'blue', 'purple', 'yellow', 'orange', 'aqua', 'pink', 'gold', 'silver'];
export const TAIL_GOLD = [255, 150, 52], TAIL_SILVER = [220, 228, 255], EMBER = [255, 70, 12];

export const pickColor = rand => PALETTE[rand.choice(SHOW_COLORS)];

const smooth = (e0, e1, x) => { const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };

// Writes [r, g, b, intensity] (0-255 colour, intensity ~1 normal, >1 flashes, 0 invisible) into out; returns out.
export function starRGB(s, out, flashes = true) {
  if (s.age < 0) { out[0] = out[1] = out[2] = out[3] = 0; return out; }
  const t = s.life > 0 ? s.age / s.life : 1;
  const base = s.color2 && t > s.change ? s.color2 : s.color;
  let r, g, b, i, m;
  if (s.kind === 'pop') { out[0] = 255; out[1] = 245; out[2] = 225; out[3] = 3 * (1 - t); return out; }
  if (s.kind === 'spark') {
    m = smooth(0.3, 1, t);
    r = base[0] + (EMBER[0] - base[0]) * m; g = base[1] + (EMBER[1] - base[1]) * m; b = base[2] + (EMBER[2] - base[2]) * m;
    i = (1 - t) * (1 - t) * s.bright;
    if (s.glitter && flashes) i *= 0.35 + 1.6 * (0.5 + 0.5 * Math.sin(s.phase + s.age * 47)) ** 6;
    out[0] = r; out[1] = g; out[2] = b; out[3] = i; return out;
  }
  if (s.kind === 'shell') { out[0] = TAIL_GOLD[0]; out[1] = TAIL_GOLD[1]; out[2] = TAIL_GOLD[2]; out[3] = 0.9 * s.bright; return out; }
  m = smooth(0, 0.12, t);
  r = 255 + (base[0] - 255) * m; g = 250 + (base[1] - 250) * m; b = 240 + (base[2] - 240) * m;
  m = smooth(0.78, 1, t);
  r += (EMBER[0] - r) * m; g += (EMBER[1] - g) * m; b += (EMBER[2] - b) * m;
  i = s.bright * (1 + 1.2 * (1 - smooth(0, 0.08, t))) * (1 - smooth(0.82, 1, t));
  if (s.strobe > 0 && flashes) i *= ((s.age + s.phase) % s.strobe) < s.strobe * 0.35 ? 1 : 0.05;
  else if (s.glitter && flashes) i *= 0.55 + 0.9 * (0.5 + 0.5 * Math.sin(s.phase + s.age * 31)) ** 4;
  else i *= 0.9 + 0.1 * Math.sin(s.phase + s.age * 23);
  out[0] = r; out[1] = g; out[2] = b; out[3] = i; return out;
}
