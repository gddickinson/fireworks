// Shared helpers of the realistic weather plug-ins (fw_wx_*.js, registered with fw_fx.js). Everything here is plain
// arithmetic except the canvas helpers, which return null in node (no DOM) so that update() can be tested there.
//   Units: positions in CSS px of the fx layers (env.cssW x env.cssH), time in s, wind in m/s (env.wind, gusty).
//   Depth: something z metres from the camera moves PXM(env, z) = 1.5 * cssH / z CSS px per metre (FOCAL = 1.5).
import { hash } from './fw_noise.js';

export const HAS_DOM = typeof document !== 'undefined';
export const canvas = (w, h) => {
  if (!HAS_DOM) return null;
  const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
  return c;
};
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const rgba = (c, a) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${+a.toFixed(3)})`;

// CSS px per metre at depth z (the pyro camera's focal length is 1.5 x the image height).
export const PXM = (env, z) => 1.5 * env.cssH / z;

// Particle budget: `base` at 1280 x 800 CSS px and full quality, scaled by area and env.quality, bounded.
export function budget(env, base, max = base * 2) {
  const area = (env.cssW * env.cssH) / (1280 * 800);
  return Math.max(4, Math.min(max, Math.round(base * clamp(area, 0.2, 2) * clamp(env.quality ?? 1, 0.2, 1))));
}

// Burst lights in CSS px: [{x, y, r, I, col}] (env.lights are device px).
export function cssLights(env) {
  const k = env.k || 1, out = [];
  for (const L of env.lights || []) out.push({ x: L.x * k, y: L.y * k, r: L.r * k, I: L.I, col: L.col });
  return out;
}

// Light falling on a point (same falloff as the renderer's lightAt): fills rgb (0..~1 per channel), returns the sum.
export function lightAt(lights, x, y, rgb, spread = 1) {
  let r = 0, g = 0, b = 0;
  for (const L of lights) {
    const s = L.r * spread, dx = (x - L.x) / s, dy = (y - L.y) / s, q = 1 + dx * dx + dy * dy, f = L.I / (q * q) / 255;
    r += L.col[0] * f; g += L.col[1] * f; b += L.col[2] * f;
  }
  rgb[0] = r; rgb[1] = g; rgb[2] = b;
  return r + g + b;
}

// Scene tone of the sky glow per scenery (fog, haze and cloud undersides take this colour).
export function skyTone(env) {
  const n = env.scenery?.name;
  if (n === 'Cityscape') return { fog: [74, 64, 62], haze: [70, 58, 52], under: [96, 66, 48], top: [30, 30, 38] };
  if (n === 'Beach') return { fog: [54, 58, 74], haze: [46, 50, 66], under: [56, 54, 72], top: [26, 28, 40] };
  return { fog: [60, 66, 80], haze: [44, 50, 64], under: [52, 56, 74], top: [24, 27, 38] };
}

// Draw a horizontally periodic texture scrolled by `off` px (fractional, wraps) without a seam: a repeating pattern.
export function drawScrolled(x, tex, off, dy, w, h) {
  const pat = tex._pat || (tex._pat = x.createPattern(tex, 'repeat-x'));
  pat.setTransform(new DOMMatrix([1, 0, 0, 1, off, dy]));
  x.fillStyle = pat; x.fillRect(0, Math.max(0, dy), w, Math.min(h, tex.height + dy) - Math.max(0, dy));
}

// Combine several plug-ins into one (Storm = clouds + rain + lightning). Parts may share state through `shared`.
export function combine(parts) {
  parts = parts.filter(Boolean);
  const each = (name, ...a) => { for (const p of parts) p[name]?.(...a); };
  const P = { parts,
    resize: env => each('resize', env),
    update: (dt, env) => each('update', dt, env) };
  if (parts.some(p => p.drawSky)) P.drawSky = (c, env) => { for (const p of parts) if (p.drawSky) { c.save(); p.drawSky(c, env); c.restore(); } };
  if (parts.some(p => p.drawOver)) P.drawOver = (c, env) => { for (const p of parts) if (p.drawOver) { c.save(); p.drawOver(c, env); c.restore(); } };
  return P;
}

// Periodic value noise / fbm (period px, py in lattice cells at the first octave; octaves double the frequency, so
// a texture of it tiles seamlessly). Used for fog and cloud textures.
const fade = t => t * t * (3 - 2 * t);
function noiseP(seed, x, y, px, py) {
  const i = Math.floor(x), j = Math.floor(y), fx = fade(x - i), fy = fade(y - j);
  const i0 = ((i % px) + px) % px, i1 = (i0 + 1) % px, j0 = ((j % py) + py) % py, j1 = (j0 + 1) % py;
  const a = hash(seed, i0, j0), b = hash(seed, i1, j0), c = hash(seed, i0, j1), d = hash(seed, i1, j1);
  return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
}
export function fbmP(seed, x, y, px, py, oct = 5, gain = 0.5) {
  let s = 0, a = 1, n = 0, f = 1;
  for (let o = 0; o < oct; o++) { s += a * noiseP(seed + o * 131, x * f, y * f, px * f, py * f); n += a; a *= gain; f *= 2; }
  return s / n;
}

// The scene's geometry seen from the sky, derived once per scenery and size from its material map (blue = open sky,
// red = albedo, green = water) and the front silhouettes' alpha, sampled at CSS px:
//   tops[x]  - first solid y (CSS px) per column (where a bolt ends, the skyline)
//   edges    - [x, y, slope, overWater] top edges of every silhouette (not solid above, solid below) for snow
//   mask(s)  - canvas at 1/s CSS px whose alpha is the open sky not hidden by the front (clouds, flashes)
const SCENE_CACHE = new WeakMap();
export function sceneGeometry(env) {
  const S = env.scenery, W = Math.max(1, Math.round(env.cssW)), H = Math.max(1, Math.round(env.cssH));
  if (!S || !HAS_DOM || !S.mat?.getContext) return { tops: new Float32Array(W).fill(H), edges: [], mask: () => null };
  const key = `${W}x${H}`;
  let per = SCENE_CACHE.get(S);
  if (!per) { per = {}; SCENE_CACHE.set(S, per); }
  if (per[key]) return per[key];
  const c = canvas(W, H), x = c.getContext('2d', { willReadFrequently: true });
  x.drawImage(S.mat, 0, 0, W, H);
  const m = x.getImageData(0, 0, W, H).data;
  x.clearRect(0, 0, W, H); x.drawImage(S.front, 0, 0, W, H);
  const f = x.getImageData(0, 0, W, H).data;
  const tops = new Float32Array(W).fill(H), cols = [];
  const solid = i => f[i + 3] > 128 || (m[i] > 12 && m[i + 1] < 128 && m[i + 2] < 128);
  const water = i => f[i + 3] <= 128 && m[i + 1] >= 128;
  for (let cx = 0; cx < W; cx++) {
    const list = [];
    let prev = false;
    for (let y = 0; y < H; y++) {
      const i = (y * W + cx) * 4, s = solid(i);
      if (s && !prev && y > 0) {                              // above water: a flag (only flat tops hold snow)
        if (tops[cx] === H) tops[cx] = y;
        if (list.length < 8) list.push(water(i - W * 4) ? -y : y);
      }
      if (!s && water(i) && tops[cx] === H) tops[cx] = y;       // the sea horizon also ends a bolt
      prev = s;                                               // (water above a quay: snow on the quay)
    }
    cols.push(list);
  }
  const edges = [];
  for (let cx = 0; cx < W; cx++) for (const v of cols[cx]) {   // slope: distance to the nearest edge next door
    const y = Math.abs(v), near = (l) => l ? l.reduce((d, u) => Math.min(d, Math.abs(Math.abs(u) - y)), 99) : 99;
    edges.push([cx, y, Math.min(near(cols[cx - 1]), near(cols[cx + 1])), v < 0]);
  }
  const masks = {};
  const mask = (s = 4) => {
    if (masks[s]) return masks[s];
    const w = Math.ceil(W / s), h = Math.ceil(H / s), mc = canvas(w, h), mx = mc.getContext('2d');
    const img = mx.createImageData(w, h), d = img.data;
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      let a = 0, n = 0;
      for (let v = j * s; v < Math.min(H, j * s + s); v += 2) for (let u = i * s; u < Math.min(W, i * s + s); u += 2) {
        const q = (v * W + u) * 4; a += (m[q + 2] / 255) * (1 - f[q + 3] / 255); n++;
      }
      const o = (j * w + i) * 4; d[o] = d[o + 1] = d[o + 2] = 255; d[o + 3] = n ? Math.round(255 * a / n) : 0;
    }
    mx.putImageData(img, 0, 0);
    return (masks[s] = mc);
  };
  return (per[key] = { tops, edges, mask });
}
