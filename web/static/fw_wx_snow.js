// Realistic snow (weather plug-in, see fw_fx.js): flakes at depths from 1.5 to 27 m (near ones large, soft and out
// of focus, far ones tiny), tumbling in turbulence and drifting with the gusty wind, settling slowly; lit in the
// colour of nearby bursts; and a thin layer of snow slowly building up on the top edges of the silhouettes (skyline,
// trees, ridges, ground), found once per size from the scenery's material map and front layer.
//
// update() logic (plain arithmetic, easy to port):
//   each flake: depth z (m, 1.5..27.5), px per metre m = 1.5 * H / z, fall speed vf (m/s, 0.6..1.4), phase ph;
//   turbulence u, w = noise1(seed + i, t * 0.5 + ph) - 0.5, noise1(seed + 7 * i, t * 0.4) - 0.5;
//   x += (wind + 1.6 u) * m * dt;  y += (vf + 0.5 w) * m * dt; below the bottom: respawn at the top (seeded x);
//   x wraps around the width. Accumulated depth (px at 800 px height): acc = 0.4 + 3 * (1 - exp(-t / 90)).
import { noise1, prng, hash } from './fw_noise.js';
import { registerWeather } from './fw_fx.js';
import { PXM, budget, canvas, clamp, cssLights, rgba, sceneGeometry, skyTone } from './fw_wx_util.js';

const BASE = 900, FOCUS = 3.2;                                // flakes at 1280 x 800; nearer than FOCUS m is blurred

export function makeSnow(env, opts = {}) {
  const seed = (env.seed ^ 0x5e0f) >>> 0, R = prng(seed), dens = opts.density ?? 1;
  const flakes = [];
  let W = 1, H = 1, t = 0, vxMean = 0;
  const newFlake = top => {
    const u = R(), z = 1.5 + 26 * u ** 1.4;                    // many far flakes, a few close to the lens
    return { x: R() * W, y: top ? -10 - R() * 20 : R() * H, z, vf: 0.6 + R() * 0.8, ph: R() * 100, sz: 0.6 + R() * 0.8, id: (R() * 1e6) | 0 };
  };
  function fill(env) {
    const n = budget(env, BASE * dens, BASE * dens * 2);
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
  };
  P.resize(env);
  return P;
}

let SPRITE = null;                                            // soft white disc, 32 px
function sprite() {
  if (SPRITE) return SPRITE;
  SPRITE = canvas(32, 32);
  const x = SPRITE.getContext('2d'), g = x.createRadialGradient(16, 16, 0, 16, 16, 16);
  g.addColorStop(0, 'rgba(215,220,235,1)'); g.addColorStop(0.35, 'rgba(215,220,235,0.75)');
  g.addColorStop(0.7, 'rgba(215,220,235,0.22)'); g.addColorStop(1, 'rgba(215,220,235,0)');
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
    x.fillStyle = rgba([196, 204, 222], clamp(0.25 + th * 0.25, 0, 0.8));
    x.fillRect(ex, ey - th * 0.7, 1, th);
  }
  P.accCanvas = c; P.accDepth = want;
  return c;
}

function drawSnow(c, env, P, W, H, t) {
  const lights = cssLights(env).filter(L => L.I > 0.05).slice(0, 5), tone = skyTone(env);
  // a faint veil, and burst light scattered by the falling snow
  c.fillStyle = rgba(tone.haze.map(v => v * 1.2), 0.05); c.fillRect(0, 0, W, H);
  for (const L of lights) {
    const r = L.r * 1.2, a = Math.min(0.2, 0.06 * L.I), g = c.createRadialGradient(L.x, L.y, 0, L.x, L.y, r);
    g.addColorStop(0, rgba(L.col, a)); g.addColorStop(1, rgba(L.col, 0));
    c.fillStyle = g; c.fillRect(L.x - r, L.y - r, 2 * r, 2 * r);
  }
  const acc = accumulation(env, P, W, H);
  if (acc) c.drawImage(acc, 0, 0);
  // far flakes: tiny squares in one path; near ones: soft sprites (out of focus nearer than FOCUS)
  const spr = sprite(), small = [], big = [];
  for (const f of P.flakes) {
    const r = 0.01 * PXM(env, f.z) * f.sz;                 // a ~1 cm flake
    (r < 1.1 ? small : big).push([f, r]);
  }
  c.fillStyle = 'rgba(205,212,228,0.6)';
  c.beginPath();
  for (const [f, r] of small) { const s = Math.max(1.3, r * 1.8); c.rect(f.x - s / 2, f.y - s / 2, s, s); }
  c.fill();
  for (const [f, r] of big) {
    const blur = f.z < FOCUS ? (FOCUS - f.z) / FOCUS : 0, d = (r * (1 + 2 * blur) + 0.8) * 2.4;
    const tumble = 0.75 + 0.25 * Math.sin(t * (2 + f.sz * 3) + f.ph);  // a turning flake glints
    c.globalAlpha = clamp(0.7 * tumble * (1 - 0.8 * blur), 0.06, 1);  // out of focus: spread and faint
    c.drawImage(spr, f.x - d / 2, f.y - d / 2, d, d);
  }
  c.globalAlpha = 1;
  // lit by bursts: flakes inside a light's radius get a dot of its colour
  for (const L of lights) {
    const r2 = (L.r * 0.8) ** 2, a = Math.min(0.9, 0.45 * L.I);
    if (a < 0.04) continue;
    c.fillStyle = rgba(L.col.map(v => Math.min(255, v * 0.8 + 70)), a);
    c.beginPath();
    for (const f of P.flakes) {
      const dx = f.x - L.x, dy = f.y - L.y;
      if (f.z < FOCUS || dx * dx + dy * dy > r2) continue;      // (blurred near flakes stay soft)
      const s = Math.max(0.7, 0.01 * PXM(env, f.z) * f.sz * 1.2);
      c.moveTo(f.x + s, f.y); c.arc(f.x, f.y, s, 0, 6.283);
    }
    c.fill();
  }
}

registerWeather('Snow', 'Snow', env => makeSnow(env));
