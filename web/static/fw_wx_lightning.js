// Realistic lightning (weather plug-in part, see fw_fx.js) and the two weathers that use it:
//   Storm     - dark low cloud deck + heavy rain + frequent strikes
//   Lightning - light broken cloud + rare strikes
// A strike is either a cloud-to-ground bolt (a jagged channel from the cloud base to the skyline/ground with
// branches) or a flash inside the cloud. Its brightness is a few return strokes, each a sharp spike decaying in
// ~50 ms, so the bolt flickers. The flash lights the cloud deck (shared.flash -> fw_wx_clouds.js), brightens the
// rain (fw_wx_rain.js) and the open sky behind the silhouettes ('sky' layer, masked by the scenery). With
// env.reduced (prefers-reduced-motion) there are no strikes and no flashes at all.
//
// update() logic (plain arithmetic, easy to port):
//   t += dt; when t >= next: new strike (seeded), next = t + interval (uniform in [lo, hi] s);
//   strike brightness b(t) = sum over its strokes k of amp_k * exp(-(t - t_k) / 0.05) for t >= t_k;
//   shared.flash = max over live strikes of b; a strike ends 0.4 s after its last stroke.
//   Bolt path: from (x0, y0) at the cloud base towards (x1, top of the scenery at x1) in n steps; each step goes
//   down (y1 - y0) / n * (0.6..1.4) and sideways towards the target plus a seeded jitter; branches leave with
//   probability 0.14 per step and walk 5..16 shorter steps at 0.35..1.1 rad off the vertical. Every segment then
//   gets a midpoint shifted sideways by (-0.25..0.25) x its length.
import { prng } from './fw_noise.js';
import { registerWeather } from './fw_fx.js';
import { HAS_DOM, canvas, clamp, combine, rgba, sceneGeometry } from './fw_wx_util.js';
import { makeClouds } from './fw_wx_clouds.js';
import { makeRain } from './fw_wx_rain.js';

// opts: interval [lo, hi] s, ground (probability of a bolt vs a cloud flash), deck (cloud base, fraction of H),
//       shared ({ flash, flashX, flashY } read by the clouds and the rain)
export function makeLightning(env, opts = {}) {
  const o = { interval: [6, 16], ground: 0.6, deck: 0.3, ...opts }, shared = opts.shared || {};
  const R = prng((env.seed ^ 0x1b0175) >>> 0);
  const strikes = [];
  let W = env.cssW, H = env.cssH, t = 0, next = 2 + R() * o.interval[0];
  shared.flash = 0;

  function walk(x, y, ty, tx, n, step, spread, out) {         // one jagged channel; returns its points
    const pts = [[x, y]];
    for (let i = 0; i < n && y < ty; i++) {
      const dy = step * (0.6 + R() * 0.8), pull = tx == null ? 0 : (tx - x) / Math.max(1, n - i);
      x += pull + (R() - 0.5) * 2 * spread * dy; y += dy;
      pts.push([x, y]);
      if (out && R() < 0.14 && i < n - 3) {                   // a branch, sometimes with a sub-branch
        const side = R() < 0.5 ? -1 : 1, ang = 0.35 + R() * 0.75, m = 5 + ((R() * 12) | 0);
        const br = branch(x, y, side, ang, m, step * 0.7);
        out.push(br);
        if (R() < 0.3 && br.length > 4) out.push(branch(...br[2], side * (R() < 0.5 ? 1 : -1), ang, 4 + ((R() * 6) | 0), step * 0.5));
      }
    }
    return refine(pts);
  }
  function refine(pts) {                                      // a kinked midpoint in every segment: fine tortuosity
    const out = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      const [ax, ay] = pts[i - 1], [bx, by] = pts[i], j = (R() - 0.5) * 0.5;
      out.push([(ax + bx) / 2 - (by - ay) * j, (ay + by) / 2 + (bx - ax) * j], pts[i]);
    }
    return out;
  }
  function branch(x, y, side, ang, n, step) {
    const pts = [[x, y]];
    for (let i = 0; i < n; i++) {
      const a = ang + (R() - 0.5) * 0.9, l = step * (0.6 + R() * 0.8);
      x += side * Math.sin(a) * l; y += Math.cos(a) * l;
      pts.push([x, y]);
    }
    return refine(pts);
  }
  function strike(env) {
    const x0 = W * (0.08 + R() * 0.84), y0 = H * o.deck * (0.55 + R() * 0.4);
    const strokes = [], k = 1 + ((R() * 3.2) | 0);
    let ts = t;
    for (let i = 0; i < k; i++) { strokes.push([ts, i === 0 ? 1 : 0.45 + R() * 0.55]); ts += 0.04 + R() * 0.12; }
    const s = { t0: t, strokes, end: ts + 0.4, x: x0, y: y0, bolt: null, branches: [] };
    if (R() < o.ground) {
      const x1 = clamp(x0 + (R() - 0.5) * W * 0.25, 2, W - 2), tops = sceneGeometry(env).tops;
      const y1 = Math.min(H, tops[Math.round(x1 * (tops.length - 1) / Math.max(1, W))] ?? H) + 1;
      const n = 26 + ((R() * 18) | 0);
      s.bolt = walk(x0, y0, y1, x1, n, (y1 - y0) / n, 0.55, s.branches);
    } else {
      for (const st of strokes) st[1] *= 0.55;                // a flash inside the cloud: dimmer, no channel
    }
    strikes.push(s);
  }
  const bright = s => s.strokes.reduce((b, [tk, a]) => b + (t >= tk ? a * Math.exp(-(t - tk) / 0.05) : 0), 0);

  const P = {
    strikes, shared,
    resize(env) { W = env.cssW; H = env.cssH; strikes.length = 0; P.fc = null; },
    update(dt, env) {
      if (env.cssW !== W || env.cssH !== H) P.resize(env);
      t += dt;
      if (env.reduced) { strikes.length = 0; shared.flash = 0; return; }
      if (t >= next) { strike(env); next = t + o.interval[0] + R() * (o.interval[1] - o.interval[0]); }
      let f = 0;
      for (const s of strikes) {
        const b = bright(s); s.b = b;
        if (b > f) { f = b; shared.flashX = s.x; shared.flashY = s.y; }
      }
      for (let i = strikes.length - 1; i >= 0; i--) if (t > strikes[i].end) strikes.splice(i, 1);
      shared.flash = f;
      if (HAS_DOM) globalThis.__fwFlash = { flash: f, bolt: strikes.some(s => s.bolt && s.b > 0.3) };  // screenshot tests
    },
    stats() { return { count: strikes.length, flash: shared.flash, bolts: strikes.filter(s => s.bolt).length }; },
    drawSky(c, env) {
      if (!strikes.length || !HAS_DOM) return;
      const sc = H / 800, f = clamp(shared.flash, 0, 1.5);
      // the open sky lights up behind the silhouettes (masked low-res glow)
      if (f > 0.02) {
        const s4 = 4, w = Math.ceil(W / s4), h = Math.ceil(H / s4);
        if (!P.fc) P.fc = canvas(w, h);
        const x = P.fc.getContext('2d');
        x.globalCompositeOperation = 'source-over'; x.clearRect(0, 0, w, h);
        const fx = (shared.flashX ?? W / 2) / s4, fy = (shared.flashY ?? H * 0.2) / s4;
        const g = x.createRadialGradient(fx, fy, 0, fx, fy, w * 0.9);
        g.addColorStop(0, rgba([190, 198, 240], Math.min(0.5, 0.38 * f))); g.addColorStop(1, rgba([120, 130, 180], Math.min(0.2, 0.12 * f)));
        x.fillStyle = g; x.fillRect(0, 0, w, h);
        const mask = sceneGeometry(env).mask(s4);
        if (mask) { x.globalCompositeOperation = 'destination-in'; x.drawImage(mask, 0, 0); }
        c.drawImage(P.fc, 0, 0, w * s4, h * s4);
      }
      // channels: wide violet glow, a bluish body and a white-hot core; branches thinner and dimmer
      c.lineCap = 'round'; c.lineJoin = 'round';
      for (const s of strikes) {
        if (!s.bolt) continue;
        const b = clamp(s.b * 1.4, 0, 1), after = clamp(1 - (t - s.t0) / (s.end - s.t0), 0, 1) * 0.25;
        const v = Math.max(b, after);
        if (v < 0.02) continue;
        for (const [width, col, a] of [[12, [140, 130, 255], 0.1], [4.5, [180, 190, 255], 0.35], [1.6, [255, 255, 255], 1]]) {
          c.strokeStyle = rgba(col, a * v);
          c.lineWidth = width * sc; poly(c, s.bolt);
          c.lineWidth = width * sc * 0.5; c.strokeStyle = rgba(col, a * v * 0.7);
          for (const br of s.branches) poly(c, br);
        }
      }
    },
    drawOver(c, env) {                                        // the whole scene catches a little of the flash
      const f = clamp(shared.flash || 0, 0, 1.5);
      if (f > 0.02) { c.fillStyle = rgba([170, 180, 230], 0.05 * f); c.fillRect(0, 0, W, H); }
    },
  };
  return P;
}
function poly(c, pts) {
  c.beginPath(); c.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) c.lineTo(pts[i][0], pts[i][1]);
  c.stroke();
}

registerWeather('Storm', 'Thunderstorm', env => {
  const shared = { flash: 0 };
  return combine([makeClouds(env, { cover: 0.92, base: 0.36, dark: 0.85, over: 0.4, shared }),
    makeLightning(env, { interval: [3, 9], ground: 0.65, deck: 0.36, shared }), makeRain(env, { heavy: 1.8, shared })]);
});
registerWeather('Lightning', 'Lightning', env => {
  const shared = { flash: 0 };
  return combine([makeClouds(env, { cover: 0.42, base: 0.3, dark: 0.5, over: 0.25, shared }),
    makeLightning(env, { interval: [5, 13], ground: 0.75, deck: 0.3, shared })]);
});
