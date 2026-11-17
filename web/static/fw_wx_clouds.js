// Realistic low cloud deck (weather plug-in, see fw_fx.js; also part of Storm and Lightning): two periodic fbm
// cloud textures (a high deck and lower, faster scud) shaded once per size at 1/4 CSS px - dark cores, thin edges
// lit by the moon/sky glow, undersides lit by the town - scrolled with the wind aloft. Every frame the bursts light
// the clouds from below/inside in their colour (tinting only where there is cloud), the Moon sky effect (when on,
// env.scenery.moon) silvers the cloud near it, a lightning flash (shared.flash)
// lights the deck, and the open-sky mask of the scenery hides the clouds behind the skyline, ridges and trees.
// The deck goes into the 'sky' layer (behind the fireworks); a thin copy in 'over' veils bursts inside the deck.
//
// update() logic (plain arithmetic, easy to port):
//   wind aloft = 2 x env.wind; layer i (depth z_i m) scrolls off_i += 2 * wind * 1.5 * H / z_i * dt / 4 (low-res px,
//   wrapping around the texture width).
import { prng } from './fw_noise.js';
import { registerWeather } from './fw_fx.js';
import { HAS_DOM, PXM, canvas, clamp, cssLights, drawScrolled, fbmP, rgba, sceneGeometry, skyTone, smooth } from './fw_wx_util.js';

const S = 4;                                                  // CSS px per cloud pixel

// opts: cover (0..1, fraction of the deck covered), base (deck bottom, fraction of the height), dark (0..1),
//       over (alpha of the copy in front of the fireworks), shared ({ flash, flashX, flashY } from the lightning)
export function makeClouds(env, opts = {}) {
  const o = { cover: 0.6, base: 0.34, dark: 0.3, over: 0.32, ...opts }, shared = opts.shared || {};
  const seed = (env.seed ^ 0xc10d) >>> 0, R = prng(seed);
  const layers = [
    { z: 2600, cells: 4, cover: o.cover, base: o.base, a: 1, off: R() * 1000, seed, tex: null },
    { z: 1100, cells: 8, cover: o.cover * 0.55, base: o.base * 1.08, a: 0.7, off: R() * 1000, seed: seed + 5003, tex: null },
  ];
  let W = 1, H = 1, vx = 0;
  const P = {
    layers, shared, opts: o,
    resize(env) { W = env.cssW; H = env.cssH; for (const L of layers) L.tex = null; P.wc = null; },
    update(dt, env) {
      if (env.cssW !== W || env.cssH !== H) P.resize(env);
      const wind = 2 * (env.wind ?? 0) * (env.reduced ? 0.5 : 1);
      let s = 0;
      for (const L of layers) { const v = wind * PXM(env, L.z) / S; L.off += v * dt; s += v; }
      vx = s / layers.length;
    },
    stats() { return { count: layers.length, vx }; },
    drawSky(c, env) { const wc = render(env, P, W, H); if (wc) c.drawImage(wc, 0, 0, wc.width * S, wc.height * S); },
    drawOver(c, env) {
      if (!P.wc || o.over <= 0) return;
      c.globalAlpha = o.over; c.drawImage(P.wc, 0, 0, P.wc.width * S, P.wc.height * S); c.globalAlpha = 1;
    },
  };
  P.resize(env);
  return P;
}

// A shaded cloud texture (w x h low-res px, periodic in x): rgb = shading, alpha = density.
function texture(L, w, h, H, o, tone) {
  const cv = canvas(w, h), x = cv.getContext('2d'), img = x.createImageData(w, h), d = img.data;
  const baseY = L.base * H / S, thr = 1 - L.cover, cellsY = Math.max(2, Math.round(L.cells * h / w * 2.2));
  const core = tone.top.map(v => v * (1 - 0.55 * o.dark)), edge = [74, 80, 100].map(v => v * (1 - 0.45 * o.dark));
  const under = tone.under.map(v => v * (1 - 0.3 * o.dark));
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    const u = i / w;
    const ragged = baseY * (0.82 + 0.3 * fbmP(L.seed + 77, u * L.cells * 2, 0.5, L.cells * 2, 1e6, 3));
    const p = j / ragged;                                     // 0 at the top, 1 at the (ragged) base
    const n = fbmP(L.seed, u * L.cells, j / h * cellsY, L.cells, 1e6, 5);
    const shape = n + 0.18 * (1 - p) - 0.6 * Math.max(0, p - 0.75) * 4;
    const a = smooth(thr - 0.12, thr + 0.22, shape) * L.a;
    const thick = smooth(thr, thr + 0.45, shape);              // thick cores are dark; thin edges catch the light
    const lit = smooth(0.55, 1.0, p) * 0.8;                   // underside lit by the ground and the town
    const q = (j * w + i) * 4;
    for (let k = 0; k < 3; k++) {
      const v = edge[k] + (core[k] - edge[k]) * thick;
      d[q + k] = Math.round(v + (under[k] - v) * lit * (0.4 + 0.6 * thick));
    }
    d[q + 3] = Math.round(255 * clamp(a, 0, 1));
  }
  x.putImageData(img, 0, 0);
  return cv;
}

// Cloud deck of this frame into P.wc (low-res): scrolled textures, burst light, lightning, open-sky mask.
function render(env, P, W, H) {
  if (!HAS_DOM) return null;
  const o = P.opts, w = Math.ceil(W / S), h = Math.ceil(H * Math.min(0.75, o.base * 1.5) / S), tone = skyTone(env);
  if (!P.wc || P.wc.width !== w || P.wc.height !== h) P.wc = canvas(w, h);
  const x = P.wc.getContext('2d');
  x.globalCompositeOperation = 'source-over'; x.clearRect(0, 0, w, h);
  for (const L of P.layers) {
    if (!L.tex) L.tex = texture(L, w, h, H, o, tone);
    drawScrolled(x, L.tex, L.off % w, 0, w, h);
  }
  // burst light from below / inside: tint (source-atop keeps the cloud's alpha), strongest at the base
  x.globalCompositeOperation = 'source-atop';
  for (const L of cssLights(env).slice(0, 6)) {
    if (L.I < 0.03) continue;
    const r = L.r * 1.0 / S, lx = L.x / S, ly = L.y / S, a = Math.min(0.6, 0.2 * L.I);
    const gr = x.createRadialGradient(lx, ly, 0, lx, ly, r);
    gr.addColorStop(0, rgba(L.col.map(v => Math.min(255, v * 0.6 + 90)), a)); gr.addColorStop(0.35, rgba(L.col, a * 0.35));
    gr.addColorStop(1, rgba(L.col, 0));
    x.fillStyle = gr; x.fillRect(lx - r, ly - r, 2 * r, 2 * r);
  }
  const M = env.scenery?.moon;                                // the Moon sky effect (when on): silvery moonlit rims
  if (M && M.time === env.time) {
    const r = Math.max(8, M.r * 7) / S, mx = M.x / S, my = M.y / S, gr = x.createRadialGradient(mx, my, 0, mx, my, r);
    gr.addColorStop(0, rgba([225, 230, 245], 0.75)); gr.addColorStop(0.25, rgba([170, 182, 210], 0.4)); gr.addColorStop(1, rgba([120, 130, 160], 0));
    x.fillStyle = gr; x.fillRect(mx - r, my - r, 2 * r, 2 * r);
  }
  const f = clamp(P.shared.flash || 0, 0, 1.5);
  if (f > 0.01) {                                             // lightning lights the deck from inside
    const fx = (P.shared.flashX ?? W / 2) / S, fy = (P.shared.flashY ?? H * 0.2) / S, r = w * 0.7;
    const gr = x.createRadialGradient(fx, fy, 0, fx, fy, r);
    gr.addColorStop(0, rgba([215, 220, 255], Math.min(0.85, 0.65 * f))); gr.addColorStop(1, rgba([150, 160, 215], Math.min(0.5, 0.3 * f)));
    x.fillStyle = gr; x.fillRect(0, 0, w, h);
  }
  // hide the deck behind the scenery (alpha of the open sky, not covered by the front)
  const mask = sceneGeometry(env).mask(S);
  if (mask) { x.globalCompositeOperation = 'destination-in'; x.drawImage(mask, 0, 0, w, h, 0, 0, w, h); }
  x.globalCompositeOperation = 'source-over';
  return P.wc;
}

registerWeather('Clouds', 'Clouds', env => makeClouds(env));
