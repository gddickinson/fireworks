// Realistic snow (weather plug-in, see fw_fx.js): many small bright flakes at depths from 3 to 60 m in three layers
// (far: faint specks; middle: small dots; near: slightly larger with a soft bokeh edge), tumbling in turbulence and drifting with the gusty wind, settling slowly; lit in the
// colour of nearby bursts; and a thin layer of snow slowly building up on the top edges of the silhouettes (skyline,
// trees, ridges, ground), found once per size from the scenery's material map and front layer.
//
// update() logic (plain arithmetic, easy to port):
//   each flake: depth z (m, 3..63), px per metre m = 1.5 * H / z, fall speed vf (m/s, 0.6..1.4), phase ph;
//   turbulence u, w = noise1(seed + i, t * 0.5 + ph) - 0.5, noise1(seed + 7 * i, t * 0.4) - 0.5;
//   x += (wind + 1.6 u) * m * dt;  y += (vf + 0.5 w) * m * dt; below the bottom: respawn at the top (seeded x);
//   x wraps around the width. Accumulated depth (px at 800 px height): acc = 0.4 + 3 * (1 - exp(-t / 90)).
import { noise1, prng, hash } from './fw_noise.js';
import { registerWeather } from './fw_fx.js';
import { PXM, budget, canvas, clamp, cssLights, rgba, sceneGeometry, skyTone } from './fw_wx_util.js';

const BASE = 4200, FOCUS = 5;                                 // flakes at 1280 x 800; nearer than FOCUS m: soft bokeh

export function makeSnow(env, opts = {}) {
  const seed = (env.seed ^ 0x5e0f) >>> 0, R = prng(seed), dens = opts.density ?? 1;
  const flakes = [];
  let W = 1, H = 1, t = 0, vxMean = 0;
  const newFlake = top => {
    const u = R(), z = 3 + 60 * u ** 1.15;                      // most flakes far, a few close to the lens
    return { x: R() * W, y: top ? -10 - R() * 20 : R() * H, z, vf: 0.6 + R() * 0.8, ph: R() * 100, sz: 0.6 + R() * 0.8, id: (R() * 1e6) | 0 };
  };
  function fill(env) {
    const n = budget(env, BASE * dens * (env.intensity ?? 1), BASE * dens * 2.5);   // env.intensity: panel slider
    if (flakes.length > n) flakes.length = n;
    while (flakes.length < n) flakes.push(newFlake(false));
  }
  const P = {
    flakes, acc: 0,
    resize(env) { W = env.cssW; H = env.cssH; flakes.length = 0; fill(env); P.accCanvas = null; },
    update(dt, env) {
      if (env.cssW !== W || env.cssH !== H || !flakes.length) P.resize(env);
      fill(env);
      t += dt;
      const wind = env.wind ?? 0, calm = env.reduced ? 0.5 : 1;
      let sx = 0;
      for (const f of flakes) {
        const m = PXM(env, f.z);
        const u = noise1(seed + f.id, t * 0.5 + f.ph) - 0.5, w = noise1(seed + 7 * f.id, t * 0.4 + f.ph) - 0.5;
        const vx = (wind + 1.6 * u * calm) * m;
        f.x += vx * dt; f.y += (f.vf + 0.5 * w * calm) * m * dt * calm; sx += vx;
        if (f.y > H + 20) Object.assign(f, newFlake(true));
        if (f.x < -20) f.x += W + 40; else if (f.x > W + 20) f.x -= W + 40;
      }
      vxMean = flakes.length ? sx / flakes.length : 0;
      P.acc = 0.4 + 3 * (1 - Math.exp(-t / 90));
    },
    stats() { return { count: flakes.length, vx: vxMean, acc: P.acc }; },
    drawOver(c, env) { drawSnow(c, env, P, W, H, t); },
    // a faint veil and burst light scattered by the falling snow, drawn by the renderer (see fw_wx_rain.js)
    atmosphere(env) { return { veil: [...skyTone(env).haze.map(v => v * 1.2), 0.05, 0.06], scatter: 0.02 * (env.intensity ?? 1) }; },
  };
  P.resize(env);
  return P;
}

let SPRITE = null;                                            // soft white disc, 32 px
function sprite() {
  if (SPRITE) return SPRITE;
  SPRITE = canvas(32, 32);
  const x = SPRITE.getContext('2d'), g = x.createRadialGradient(16, 16, 0, 16, 16, 16);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.45, 'rgba(250,252,255,0.85)');
  g.addColorStop(0.75, 'rgba(245,248,255,0.25)'); g.addColorStop(1, 'rgba(245,248,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 32, 32);
  return SPRITE;
}

// The accumulated snow: thin white lines on the silhouettes' top edges (flat ones get more), cached and redrawn
// only when the depth has grown by a visible step.
function accumulation(env, P, W, H) {
  const want = Math.round(P.acc * 8) / 8;
  if (P.accCanvas && P.accDepth === want) return P.accCanvas;
  const geo = sceneGeometry(env), sc = H / 800;
  const c = P.accCanvas || canvas(W, H), x = c.getContext('2d');
  x.clearRect(0, 0, W, H);
  const seed = env.seed >>> 0;
  for (const [ex, ey, slope, overWater] of geo.edges) {
    const flat = overWater ? clamp(1 - slope / 1.2, 0, 1) : clamp(1 - (slope - 1) / 4, 0, 1);  // a quay, not a tree
    if (flat <= 0) continue;
    const vary = 0.55 + 0.9 * (0.6 * noise1(seed, ex / 9) + 0.4 * hash(seed, ex, ey));
    const th = want * sc * vary * flat;
    if (th < 0.25) continue;
    x.fillStyle = rgba([232, 238, 250], clamp(0.3 + th * 0.25, 0, 0.85));
    x.fillRect(ex, ey - th * 0.7, 1, th);
  }
  P.accCanvas = c; P.accDepth = want;
  return c;
}

function drawSnow(c, env, P, W, H, t) {
  const lights = cssLights(env).filter(L => L.I > 0.05).slice(0, 5), tone = skyTone(env);
  const acc = accumulation(env, P, W, H);
  if (acc) c.drawImage(acc, 0, 0);
  // three layers: far specks and middle dots in two paths, near flakes as small soft sprites (bokeh)
  const spr = sprite(), far = [], mid = [], near = [];
  for (const f of P.flakes) {
    const r = 0.006 * PXM(env, f.z) * f.sz;                // a ~1 cm flake (radius in px)
    (f.z < FOCUS * 2 ? near : r < 0.7 ? far : mid).push([f, r]);
  }
  c.fillStyle = 'rgba(240,244,255,0.45)';
  c.beginPath();
  for (const [f] of far) c.rect(f.x - 0.5, f.y - 0.5, 1, 1);
  c.fill();
  c.fillStyle = 'rgba(248,250,255,0.8)';
  c.beginPath();
  for (const [f, r] of mid) { const s = Math.min(1.6, Math.max(0.7, r)); c.moveTo(f.x + s, f.y); c.arc(f.x, f.y, s, 0, 6.283); }
  c.fill();
  for (const [f, r] of near) {
    const soft = f.z < FOCUS ? (FOCUS - f.z) / FOCUS : 0, d = Math.min(7, Math.max(2.4, r * 2.6 * (1 + 0.6 * soft)));
    const tumble = 0.8 + 0.2 * Math.sin(t * (2 + f.sz * 3) + f.ph);  // a turning flake glints
    c.globalAlpha = clamp(0.95 * tumble * (1 - 0.35 * soft), 0.3, 1);
    c.drawImage(spr, f.x - d / 2, f.y - d / 2, d, d);
  }
  c.globalAlpha = 1;
  // lit by bursts: flakes inside a light's radius get a dot of its colour
  for (const L of lights) {
    const r2 = (L.r * 0.8) ** 2, a = Math.min(0.9, 0.45 * L.I);
    if (a < 0.04) continue;
    c.fillStyle = rgba(L.col.map(v => Math.min(255, v * 0.7 + 90)), a);   // warm/coloured by the burst
    c.beginPath();
    for (const f of P.flakes) {
      const dx = f.x - L.x, dy = f.y - L.y;
      if (dx * dx + dy * dy > r2) continue;
      const s = Math.min(2.5, Math.max(0.7, 0.006 * PXM(env, f.z) * f.sz * 1.3));
      c.moveTo(f.x + s, f.y); c.arc(f.x, f.y, s, 0, 6.283);
    }
    c.fill();
  }
}

registerWeather('Snow', 'Snow', env => makeSnow(env));
