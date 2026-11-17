// Realistic rain (weather plug-in, see fw_fx.js): motion-blurred streaks in three depth layers, slanted by the gusty
// wind, glinting in the colour of nearby bursts; ripple rings on water or crown splashes on the ground; a wet sheen
// with light reflections near the bottom; a thin haze that lowers the contrast and scatters the burst light.
//
// update() logic (plain arithmetic, easy to port):
//   layer z (m from the camera): px per metre m = 1.5 * H / z; drop velocity (px/s) = (wind, 9 m/s * speed) * m,
//   so the slant dx/dy = wind / 9 at every depth (like the smoke and the shells); streak length = speed * 0.022 s
//   (camera shutter). Drops below the bottom respawn above the top at a seeded random x; x wraps around the width.
//   Splashes spawn at a fixed rate per second (rings on water between the waterline and the bottom, crowns in the
//   bottom band otherwise) with a seeded position; a ring's radius grows with its age, alpha fades out.
import { prng } from './fw_noise.js';
import { registerWeather } from './fw_fx.js';
import { PXM, budget, clamp, cssLights, rgba, skyTone } from './fw_wx_util.js';

const LAYERS = [                                              // near = longer, faster, brighter, thicker
  { z: 4.5, n: 90, width: 1.5, alpha: 0.34, col: [200, 208, 224] },
  { z: 12, n: 300, width: 0.95, alpha: 0.22, col: [176, 186, 206] },
  { z: 32, n: 700, width: 0.6, alpha: 0.13, col: [150, 160, 182] },
];
const SHUTTER = 0.022, FALL = 9;                              // s, m/s

export function makeRain(env, opts = {}) {
  const heavy = opts.heavy ?? 1, shared = opts.shared || {};
  const R = prng((env.seed ^ 0x52a1) >>> 0);
  const layers = LAYERS.map(L => ({ ...L, drops: [] }));
  const splashes = [];
  let W = 1, H = 1, wl = null, spawnAcc = 0, vxMean = 0;

  function newDrop(L, top) {
    return { x: R() * W, y: top ? -R() * H * 0.15 : R() * H, s: 0.8 + R() * 0.4 };
  }
  function fill(env) {                                        // keep each layer at its budget (quality may change)
    for (const L of layers) {
      const n = budget(env, L.n * heavy * (env.intensity ?? 1), L.n * heavy * 2.5);   // env.intensity: panel slider
      if (L.drops.length > n) L.drops.length = n;
      while (L.drops.length < n) L.drops.push(newDrop(L, false));
    }
  }
  const P = {
    shared, layers, splashes,
    resize(env) {
      W = env.cssW; H = env.cssH;
      const S = env.scenery;
      wl = S && S.water != null ? S.water * (env.k || 1) : null;
      for (const L of layers) L.drops.length = 0;
      fill(env);
    },
    update(dt, env) {
      if (env.cssW !== W || env.cssH !== H || !layers[0].drops.length) P.resize(env);
      fill(env);
      const wind = env.wind ?? 0, calm = env.reduced ? 0.6 : 1;
      let sx = 0, n = 0;
      for (const L of layers) {
        const m = PXM(env, L.z) * calm;
        for (const d of L.drops) {
          const vx = wind * m, vy = FALL * d.s * m;
          d.x += vx * dt; d.y += vy * dt; sx += vx; n++;
          if (d.y > H + vy * SHUTTER) { d.x = R() * W; d.y = -R() * H * 0.1; d.s = 0.8 + R() * 0.4; }
          if (d.x < -20) d.x += W + 40; else if (d.x > W + 20) d.x -= W + 40;
        }
      }
      vxMean = n ? sx / n : 0;
      // splashes: rate per second scaled like the drops
      const rate = budget(env, (wl != null ? 140 : 90) * heavy, 400) * calm;
      spawnAcc += rate * dt;
      const maxS = budget(env, 160 * heavy, 400);
      while (spawnAcc >= 1) {
        spawnAcc -= 1;
        if (splashes.length >= maxS) continue;
        if (wl != null) {
          const u = R(), y = wl + 2 + (H - wl - 2) * (u * u * 0.4 + u * 0.6);  // fewer near the far waterline
          splashes.push({ x: R() * W, y, age: 0, life: 0.45 + R() * 0.35, s: 0.15 + 0.85 * (y - wl) / Math.max(1, H - wl), ring: true });
        } else {
          const y = H * (0.9 + R() * 0.1);
          splashes.push({ x: R() * W, y, age: 0, life: 0.1 + R() * 0.08, s: 0.5 + (y / H - 0.9) * 5, ring: false, a: R() * 6.283 });
        }
      }
      for (const s of splashes) s.age += dt;
      for (let i = splashes.length - 1; i >= 0; i--) if (splashes[i].age >= splashes[i].life) splashes.splice(i, 1);
    },
    stats() { return { count: layers.reduce((a, L) => a + L.drops.length, 0), splashes: splashes.length, vx: vxMean }; },
    drawOver(c, env) { drawRain(c, env, P, { W, H, wl, heavy }); },
    // haze veil (thicker towards the bottom) and the share of burst light scattered by the rain, for the renderer
    atmosphere(env) { const v = 0.05 + 0.04 * heavy; return { veil: [...skyTone(env).haze, v * 0.6, v * 1.4], scatter: 0.05 * heavy }; },
  };
  P.resize(env);
  return P;
}

function drawRain(c, env, P, { W, H, wl, heavy }) {
  const lights = cssLights(env).filter(L => L.I > 0.05).slice(0, 5), tone = skyTone(env);
  const flash = clamp(P.shared.flash || 0, 0, 1.5), wind = env.wind ?? 0, sc = H / 800;
  // (the haze veil and the burst light scattered by the rain are drawn by the renderer: atmosphere() below, because a
  // faint full-screen gradient in an 8-bit overlay shows dithering lines once composited)
  // streaks, far to near; the streak is the drop's path during the shutter time
  c.lineCap = 'round';
  for (let li = P.layers.length - 1; li >= 0; li--) {
    const L = P.layers[li], m = PXM(env, L.z), ex = -wind * m * SHUTTER, ey = -FALL * m * SHUTTER;
    c.lineWidth = L.width * Math.max(0.7, sc);
    c.strokeStyle = rgba(L.col.map(v => Math.min(255, v + 30 * flash)), Math.min(0.9, L.alpha * (1 + 0.8 * flash)));
    c.beginPath();
    for (const d of L.drops) { c.moveTo(d.x, d.y); c.lineTo(d.x + ex * d.s, d.y + ey * d.s); }
    c.stroke();
    for (const Lt of lights) {                                 // glints: drops near a burst catch its colour
      const r = Lt.r * 0.9, r2 = r * r, inner = r2 * 0.2, a = Math.min(0.85, L.alpha * 2.2 * Lt.I);
      if (a < 0.03) continue;
      for (const [lo, hi, f] of [[0, inner, 1], [inner, r2, 0.35]]) {
        c.strokeStyle = rgba(Lt.col.map(v => Math.min(255, v * 0.7 + 90)), a * f);
        c.beginPath();
        let any = false;
        for (const d of L.drops) {
          const dx = d.x - Lt.x, dy = d.y - Lt.y, q = dx * dx + dy * dy;
          if (q < lo || q >= hi) continue;
          c.moveTo(d.x, d.y); c.lineTo(d.x + ex * d.s, d.y + ey * d.s); any = true;
        }
        if (any) c.stroke();
      }
    }
  }
  // wet sheen: a faint lighter band at the bottom and stretched reflections of the bursts on wet ground
  if (wl == null) {
    const top = H * 0.86, gs = c.createLinearGradient(0, top, 0, H);
    gs.addColorStop(0, rgba(tone.haze, 0)); gs.addColorStop(1, rgba(tone.haze.map(v => v * 1.6), 0.16));
    c.fillStyle = gs; c.fillRect(0, top, W, H - top);
    for (const L of lights) {
      const a = Math.min(0.3, 0.1 * L.I), rx = Math.max(10, L.r * 0.18);
      c.save(); c.translate(L.x, H); c.scale(1, (H - top) / rx);
      const gr = c.createRadialGradient(0, 0, 0, 0, 0, rx);
      gr.addColorStop(0, rgba(L.col, a)); gr.addColorStop(1, rgba(L.col, 0));
      c.fillStyle = gr; c.fillRect(-rx, -rx, 2 * rx, rx); c.restore();
    }
  }
  // splashes
  c.lineWidth = Math.max(0.6, 0.8 * sc);
  const lit = [0, 0, 0];
  for (const s of P.splashes) {
    const t = s.age / s.life, fadeA = (1 - t) * (1 - t);
    let col = [190, 198, 215];
    if (lights.length) {                                       // nearest strong light tints the splash
      let best = 0;
      for (const L of lights) { const d = Math.hypot(s.x - L.x, s.y - L.y) / L.r, w = L.I / (1 + d * d * 4); if (w > best) { best = w; lit[0] = L.col[0]; lit[1] = L.col[1]; lit[2] = L.col[2]; } }
      if (best > 0.08) col = col.map((v, i) => v + (lit[i] - v) * Math.min(0.8, best));
    }
    if (s.ring) {
      const rx = (1.5 + 9 * t) * s.s * sc * 1.2, ry = rx * (0.1 + 0.18 * s.s);   // subtle rings
      c.lineWidth = 0.7;
      c.strokeStyle = rgba(col, 0.22 * fadeA * (0.5 + s.s));
      c.beginPath(); c.ellipse(s.x, s.y, rx, ry, 0, 0, 6.283); c.stroke();
    } else {
      const h = (2 + 5 * Math.sin(t * Math.PI)) * s.s * sc, w = (1.5 + 4 * t) * s.s * sc;
      c.strokeStyle = rgba(col, 0.45 * fadeA);
      c.beginPath(); c.moveTo(s.x - w, s.y - h); c.lineTo(s.x - w * 0.3, s.y); c.moveTo(s.x + w, s.y - h); c.lineTo(s.x + w * 0.3, s.y);
      c.moveTo(s.x, s.y - h * 1.3); c.lineTo(s.x, s.y - h * 0.4); c.stroke();
    }
  }
}

registerWeather('Rain', 'Rain', env => makeRain(env));
