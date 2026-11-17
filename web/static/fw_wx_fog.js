// Realistic fog and mist (weather plug-ins, see fw_fx.js): layered volumetric fog from periodic fbm noise textures
// (built once per size at 1/4 CSS px), scrolled with the gusty wind at their depths and blended in a low-resolution
// canvas that is scaled up smoothly. Denser towards the ground; bursts glow through it: their colour tints the fog
// around them (a soft diffuse halo) while the fog's alpha in the 'over' layer dims the sharp sparks behind it.
// Mist is the light version: thinner, hugging the ground and water.
//
// update() logic (plain arithmetic, easy to port):
//   each layer i (depth z_i m) scrolls by off_i += wind * 1.5 * H / z_i * dt / 4 (low-res px; wraps around the
//   texture width) and bobs vertically by 1.5 * sin(0.07 t + i). The textures tile horizontally.
import { prng } from './fw_noise.js';
import { registerWeather } from './fw_fx.js';
import { HAS_DOM, PXM, canvas, clamp, cssLights, drawScrolled, fbmP, rgba, skyTone, smooth } from './fw_wx_util.js';

const S = 4;                                                  // CSS px per fog pixel
// Layers: depth (m), noise scale (lattice cells across the width), contrast window, alpha, vertical band
// (fractions of the height: centre, half-width, below-horizon fill), seed offset.
const FOG = [
  { z: 900, cells: 3, lo: 0.3, hi: 0.75, a: 0.3, band: [0.35, 0.5, 0] },
  { z: 260, cells: 5, lo: 0.35, hi: 0.8, a: 0.45, band: [0.0, 0.2, 1] },   // centred on the horizon
  { z: 70, cells: 4, lo: 0.4, hi: 0.85, a: 0.5, band: [0.12, 0.25, 1] },
];
const MIST = [
  { z: 300, cells: 6, lo: 0.35, hi: 0.85, a: 0.4, band: [0.0, 0.1, 0.7] },
  { z: 80, cells: 5, lo: 0.45, hi: 0.9, a: 0.42, band: [0.06, 0.12, 0.8] },
];

export function makeFog(env, opts = {}) {
  const mist = !!opts.mist, specs = mist ? MIST : FOG, seed = (env.seed ^ (mist ? 0x3157 : 0xf06)) >>> 0;
  const R = prng(seed);
  const layers = specs.map((L, i) => ({ ...L, off: R() * 1000, seed: (seed + 977 * i) >>> 0, tex: null }));
  let W = 1, H = 1, t = 0, vx = 0;
  const P = {
    layers,
    resize(env) { W = env.cssW; H = env.cssH; for (const L of layers) L.tex = null; P.fc = null; },
    update(dt, env) {
      if (env.cssW !== W || env.cssH !== H) P.resize(env);
      t += dt;
      const wind = env.wind ?? 0, calm = env.reduced ? 0.5 : 1;
      let s = 0;
      for (const L of layers) { const v = wind * PXM(env, L.z) / S * calm; L.off += v * dt; s += v; }
      vx = s / layers.length;
    },
    stats() { return { count: layers.length, vx }; },
    drawOver(c, env) { drawFog(c, env, P, W, H, t, mist); },
  };
  P.resize(env);
  return P;
}

// One layer's texture: white, alpha = density (noise through a contrast window, times the vertical band).
function texture(L, w, h, hzFrac) {
  const cv = canvas(w, h), x = cv.getContext('2d'), img = x.createImageData(w, h), d = img.data;
  const [ctr, half, below] = L.band, cy = hzFrac - ctr, cellsY = Math.max(1, Math.round(L.cells * h / w * 2));
  for (let j = 0; j < h; j++) {
    const v = j / h, dv = (v - cy) / half;
    let band = Math.exp(-dv * dv);
    if (v > cy) band = Math.max(band, below * smooth(cy, cy + half, v));
    if (band < 0.01) { for (let i = 0; i < w; i++) d[(j * w + i) * 4 + 3] = 0; continue; }
    for (let i = 0; i < w; i++) {
      const n = fbmP(L.seed, i / w * L.cells, v * cellsY * 0.5, L.cells, 1e6, 4);
      const o = (j * w + i) * 4;
      d[o] = d[o + 1] = d[o + 2] = 255; d[o + 3] = Math.round(255 * L.a * band * smooth(L.lo, L.hi, n));
    }
  }
  x.putImageData(img, 0, 0);
  return cv;
}

function drawFog(c, env, P, W, H, t, mist) {
  if (!HAS_DOM) return;
  const w = Math.ceil(W / S), h = Math.ceil(H / S), hz = env.scenery?.horizon ?? 0.85, tone = skyTone(env);
  if (!P.fc) P.fc = canvas(w, h);
  const fc = P.fc, x = fc.getContext('2d');
  x.globalCompositeOperation = 'source-over'; x.clearRect(0, 0, w, h);
  // a smooth base veil, thicker towards the ground
  const base = mist ? [0.0, 0.07, 0.22] : [0.22, 0.32, 0.42], g = x.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, `rgba(255,255,255,${base[0]})`); g.addColorStop(clamp(hz - 0.1, 0.05, 0.9), `rgba(255,255,255,${base[1]})`);
  g.addColorStop(1, `rgba(255,255,255,${base[2]})`);
  x.fillStyle = g; x.fillRect(0, 0, w, h);
  P.layers.forEach((L, i) => {
    if (!L.tex) L.tex = texture(L, w, h, hz);
    drawScrolled(x, L.tex, L.off % w, 1.5 * Math.sin(0.07 * t + i), w, h);
  });
  // colour: the sky glow's tone, lighter near the horizon where it is lit by the town/skyglow
  x.globalCompositeOperation = 'source-in';
  const col = mist ? tone.fog.map(v => v * 1.15) : tone.fog, gc = x.createLinearGradient(0, 0, 0, h);
  gc.addColorStop(0, rgba(col.map(v => v * 0.75), 1)); gc.addColorStop(clamp(hz, 0.1, 0.95), rgba(col.map(v => v * 1.15), 1));
  gc.addColorStop(1, rgba(col.map(v => v * 0.9), 1));
  x.fillStyle = gc; x.fillRect(0, 0, w, h);
  // bursts glow through the fog: tint the fog around each light (keeps its alpha), plus a faint airlight halo
  const lights = cssLights(env).filter(L => L.I > 0.03).slice(0, 6);
  for (const [op, k, amax] of [['source-atop', 0.9, 0.6], ['source-over', 0.5, 0.14]]) {
    x.globalCompositeOperation = op;
    for (const L of lights) {
      const r = L.r * k / S, a = Math.min(amax, (mist ? 0.15 : 0.24) * L.I), lx = L.x / S, ly = L.y / S;
      const gr = x.createRadialGradient(lx, ly, 0, lx, ly, r);
      const hot = L.col.map(v => Math.min(255, v * 0.85 + 60));
      gr.addColorStop(0, rgba(hot, a)); gr.addColorStop(0.3, rgba(L.col, a * 0.45)); gr.addColorStop(1, rgba(L.col, 0));
      x.fillStyle = gr; x.fillRect(lx - r, ly - r, 2 * r, 2 * r);
    }
  }
  x.globalCompositeOperation = 'source-over';
  c.imageSmoothingEnabled = true; c.imageSmoothingQuality = 'high';
  c.drawImage(fc, 0, 0, w * S, h * S);
}

registerWeather('Fog', 'Fog', env => makeFog(env));
registerWeather('Mist', 'Mist', env => makeFog(env, { mist: true }));
