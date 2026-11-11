// Port of utils/color.py ColorUtils.random_color (with Python's colorsys.hsv_to_rgb) as used by the canvas.

export function hsvToRgb(h, s, v) {                           // colorsys.hsv_to_rgb
  if (s === 0) return [v, v, v];
  let i = Math.trunc(h * 6.0);
  const f = (h * 6.0) - i;
  const p = v * (1.0 - s), q = v * (1.0 - s * f), t = v * (1.0 - s * (1.0 - f));
  i = ((i % 6) + 6) % 6;
  return [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i];
}

// ColorUtils.random_color(min_saturation=0.7, min_value=0.8): FireworksCanvas.add_firework with random colours.
export function randomColor(rand, { minHue = 0, maxHue = 1, minSat = 0.7, maxSat = 1, minVal = 0.8, maxVal = 1 } = {}) {
  const h = rand.uniform(minHue, maxHue), s = rand.uniform(minSat, maxSat), v = rand.uniform(minVal, maxVal);
  return hsvToRgb(h, s, v).map(c => Math.trunc(c * 255));
}

export const rgbCss = ([r, g, b], a = 1) => a >= 1 ? `rgb(${r},${g},${b})` : `rgba(${r},${g},${b},${a})`;
export const hexToRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
export const rgbToHex = c => '#' + c.map(v => v.toString(16).padStart(2, '0')).join('');
