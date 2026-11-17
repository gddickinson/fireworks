// Sky effects (user-toggled plug-ins, fw_fx.js registerSkyFx): the moon, shooting stars and sky lanterns. All
// drawing is cut to the open sky (and to the water for reflections) with the scenery's material map
// (fw_fx_masks.js). update() only advances numbers (seeded, no canvas, no Math.random), so it is node-testable;
// state() returns those numbers. The aurora lives in fw_sky_aurora.js.
// Moon: S.moon = { x, y, r (CSS px), time } is published on the scenery each update, so a cloud plug-in that runs
// later in the same step can light its cloud edges when S.moon.time === env.time.
import { registerSkyFx } from './fw_fx.js';
import { fbm2, hash, prng } from './fw_noise.js';
import { expWait, horizonCss, isDuskEnv, masked, softSprite, waterCss } from './fw_fx_masks.js';

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// ---- Moon: a phase lit by a sun direction (per-pixel normal . light, with earthshine and limb darkening), a halo
// and moonlit sky, a glitter path on water. Painted once per size; only the glitter is animated.
export function moonDisc(R, seed, phase, side, tilt) {     // ImageData-free RGBA array (also used by the tests)
  const n = Math.ceil(2 * R) + 2, px = new Uint8ClampedArray(n * n * 4);
  const lx0 = Math.sin(phase) * side, lz = Math.cos(phase), lx = lx0 * Math.cos(tilt), ly = lx0 * Math.sin(tilt);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const nx = (i + 0.5 - n / 2) / R, ny = (j + 0.5 - n / 2) / R, r2 = nx * nx + ny * ny;
    const a = Math.min(1, Math.max(0, (1 - Math.sqrt(r2)) * R + 0.5));
    if (a <= 0) continue;
    const nz = Math.sqrt(Math.max(0, 1 - r2)), lit = smooth(-0.05, 0.1, nx * lx + ny * ly + nz * lz);
    const maria = fbm2(seed, nx * 1.8 + 3, ny * 1.8 + 1, 4), alb = 0.72 + 0.28 * smooth(0.38, 0.62, maria);
    const limb = 0.8 + 0.2 * nz, k = (j * n + i) * 4;
    px[k] = 240 * alb * limb * lit + 38 * (1 - lit); px[k + 1] = 236 * alb * limb * lit + 44 * (1 - lit);
    px[k + 2] = 222 * alb * limb * lit + 60 * (1 - lit); px[k + 3] = 255 * a;
  }
  return { n, px };
}

function moon(env) {
  const rnd = prng((env.seed ^ 0x6d6f6f6e) >>> 0);
  const fx = 0.18 + rnd() * 0.64, fy = 0.22 + rnd() * 0.25, side = rnd() < 0.5 ? 1 : -1, tilt = (rnd() - 0.5) * 0.9;
  const phase = [0.75, 1.05, 2.05, 2.35][Math.floor(rnd() * 4)];   // gibbous or crescent (radians from full)
  const st = { t: 0 };
  let img = null;
  const geo = env => { const R = Math.max(7, 0.024 * Math.min(env.cssH, env.cssW * 1.2)); return { x: fx * env.cssW, y: fy * horizonCss(env), R }; };
  const render = env => {
    const { x, y, R } = geo(env), dusk = isDuskEnv(env), lum = (1 + Math.cos(phase)) / 2;
    const c = document.createElement('canvas'); c.width = env.cssW; c.height = env.cssH;
    const g = c.getContext('2d');
    masked(g, env, 'sky', l => {
      const big = Math.max(env.cssW, env.cssH) * 0.6, k = 0.4 + lum;       // moonlit sky, then the halo
      for (const [r, col, a, core] of [[big, '150,175,230', (dusk ? 0.05 : 0.11) * k, 0.02], [R * 8, '205,218,242', 0.28 * k, 0.1]]) {
        const g = l.createRadialGradient(x, y, 0, x, y, r);
        g.addColorStop(0, `rgba(${col},${a})`); g.addColorStop(core, `rgba(${col},${a * 0.7})`);
        g.addColorStop(0.4, `rgba(${col},${a * 0.18})`); g.addColorStop(1, `rgba(${col},0)`);
        l.fillStyle = g; l.fillRect(x - r, y - r, 2 * r, 2 * r);
      }
      l.globalAlpha = 1;
      const { n, px } = moonDisc(R, env.seed & 0xffff, phase, side, tilt), d = document.createElement('canvas');
      d.width = d.height = n; d.getContext('2d').putImageData(new ImageData(px, n, n), 0, 0);
      l.drawImage(d, x - n / 2, y - n / 2);
    });
    const wl = waterCss(env);
    if (wl !== null) masked(g, env, 'water', l => {           // the moon's broad reflected column
      const gr = l.createLinearGradient(0, wl, 0, env.cssH);
      gr.addColorStop(0, 'rgba(200,210,235,0.05)'); gr.addColorStop(1, 'rgba(200,210,235,0)');
      l.fillStyle = gr; l.save(); l.translate(x, 0); l.scale(1, 1);
      l.beginPath(); l.moveTo(-R * 0.8, wl); l.lineTo(R * 0.8, wl); l.lineTo(R * 3, env.cssH); l.lineTo(-R * 3, env.cssH); l.fill(); l.restore();
    }, 0.4 + lum * 0.6);
    return c;
  };
  return {
    resize() { img = null; },
    update(dt, env) {
      st.t += dt;
      if (env.scenery && env.cssW) { const { x, y, R } = geo(env); env.scenery.moon = { x, y, r: R, time: env.time }; }
    },
    drawSky(c, env) {
      if (!img || img.width !== env.cssW || img.height !== env.cssH) img = render(env);
      c.drawImage(img, 0, 0);
      const wl = waterCss(env);
      if (wl === null) return;
      const { x, R } = geo(env), H = env.cssH, seed = env.seed & 0xffff, t = st.t * (env.reduced ? 2 : 6);
      masked(c, env, 'water', l => {                         // glitter: dashes that switch on and off
        l.fillStyle = 'rgb(235,238,250)';
        for (let i = 0; i < 110; i++) {
          const u = hash(seed, i, 1), y = wl + Math.pow(u, 1.25) * (H - wl), d = (y - wl) / Math.max(1, H - wl);
          const spread = R * (0.5 + d * 4.5), ph = hash(seed, i, 2);
          const on = hash(seed + 7, i, Math.floor(t + ph * 10));
          if (on < 0.45) continue;
          const xx = x + (hash(seed, i, 3) - 0.5) * 2 * spread, w = 1 + d * 6 * on;
          l.globalAlpha = Math.min(1, (on - 0.45) * 1.8) * (1 - Math.abs(xx - x) / (spread + 1) * 0.8);
          l.fillRect(xx - w / 2, y, w, 0.6 + d * 1.4);
        }
      });
    },
    state: () => ({ t: st.t, fx, fy, phase, side, tilt }),
  };
}

// ---- Shooting stars: rare, seeded arrivals (exponential waiting times); slower and rarer with reduced motion.
function meteors(env) {
  const rnd = prng((env.seed ^ 0x5eed5eed) >>> 0), mean = env.reduced ? 20 : 7;
  const st = { t: 0, next: expWait(rnd(), mean * 0.4), list: [] };
  const spawn = env => {
    const W = env.cssW, hz = horizonCss(env), dir = rnd() < 0.5 ? 1 : -1, a = 0.25 + rnd() * 0.7;
    const sp = (0.3 + 0.45 * rnd()) * Math.max(W, env.cssH) * (env.reduced ? 0.4 : 1);
    st.list.push({ x: rnd() * W, y: rnd() * hz * 0.5, vx: Math.cos(a) * sp * dir, vy: Math.sin(a) * sp,
      age: 0, life: (0.35 + rnd() * 0.55) * (env.reduced ? 2 : 1), len: sp * (0.1 + rnd() * 0.08), b: 0.5 + 0.5 * rnd(), green: rnd() < 0.3 });
    if (st.list.length > 6) st.list.shift();
  };
  return {
    update(dt, env) {
      st.t += dt;
      while (st.t >= st.next) { spawn(env); st.next += expWait(rnd(), mean); }
      for (const m of st.list) m.age += dt;
      st.list = st.list.filter(m => m.age < m.life);
    },
    drawSky(c, env) {
      if (!st.list.length) return;
      const k = isDuskEnv(env) ? 0.4 : 1;
      masked(c, env, 'sky', l => {
        for (const m of st.list) {
          const p = m.age / m.life, a = Math.sin(Math.PI * p) * m.b * k, hx = m.x + m.vx * m.age, hy = m.y + m.vy * m.age;
          const v = Math.hypot(m.vx, m.vy), tx = hx - m.vx / v * m.len, ty = hy - m.vy / v * m.len;
          // one continuous, tapering streak: bright head, fading tail (a thin wedge, no dots)
          const g = l.createLinearGradient(tx, ty, hx, hy), col = m.green ? '215,250,235' : '238,243,255';
          g.addColorStop(0, `rgba(${col},0)`); g.addColorStop(0.7, `rgba(${col},${a * 0.45})`); g.addColorStop(1, `rgba(${col},${a})`);
          const nx = -m.vy / v, ny = m.vx / v, w = 0.9;                     // half-width at the head (px)
          l.fillStyle = g; l.beginPath();
          l.moveTo(tx, ty); l.lineTo(hx + nx * w, hy + ny * w); l.lineTo(hx - nx * w, hy - ny * w); l.closePath(); l.fill();
          l.globalAlpha = a * 0.8; l.drawImage(softSprite([240, 245, 255]), hx - 2.5, hy - 2.5, 5, 5); l.globalAlpha = 1;
        }
      });
    },
    state: () => ({ t: st.t, next: st.next, list: st.list.map(m => ({ ...m })) }),
  };
}

// ---- Sky lanterns: warm paper lanterns rising from behind the horizon, drifting with the wind, flickering;
// reflected on water. Farther lanterns are smaller and slower.
function lanterns(env) {
  const rnd = prng((env.seed ^ 0x1a77e125) >>> 0), N = 18, st = { t: 0, list: [] };
  const born = (L, env, first) => {
    const hz = horizonCss(env);
    L.z = rnd(); L.x = rnd() * env.cssW; L.y = first ? hz - rnd() * hz * 0.85 : hz + 4;
    L.vy = (10 + rnd() * 10) * (1 - 0.5 * L.z) * env.cssH / 800; L.ph = rnd() * 6.28; L.sway = 0.5 + rnd();
  };
  for (let i = 0; i < N; i++) { const L = {}; born(L, env, true); st.list.push(L); }
  return {
    update(dt, env) {
      st.t += dt;
      const k = env.reduced ? 0.6 : 1, wind = (env.wind || 0) * env.cssH / 800 * 4;
      for (const L of st.list) {
        L.y -= L.vy * dt * k;
        L.x += (wind * (1 - 0.5 * L.z) + Math.sin(st.t * 0.4 * L.sway + L.ph) * 3) * dt * k;
        if (L.y < -20 || L.x < -60 || L.x > env.cssW + 60) born(L, env, false);
      }
    },
    drawSky(c, env) {
      const s0 = env.cssH / 800, hz = horizonCss(env), wl = waterCss(env), dusk = isDuskEnv(env);
      const draw = (l, flip) => {
        for (const L of st.list) {
          const y = flip ? wl + (wl - L.y) * 0.85 : L.y;
          if (flip && (y > env.cssH || L.y > wl)) continue;
          const sz = (1.6 + 2.2 * (1 - L.z)) * s0 * (0.6 + 0.4 * Math.min(1, Math.max(0, L.y / hz)));
          const fl = 0.8 + 0.2 * Math.sin(st.t * 9 + L.ph * 5) * Math.sin(st.t * 5.3 + L.ph);
          l.globalAlpha = (dusk ? 0.4 : 0.55) * fl * (flip ? 0.4 : 1);
          l.drawImage(softSprite([255, 140, 50], 0.06), L.x - sz * 3.5, y - sz * 3.5, sz * 7, sz * 7);
          l.globalAlpha = fl * (flip ? 0.5 : 1); l.fillStyle = 'rgb(255,205,130)';
          l.fillRect(L.x - sz * 0.5, y - sz * 0.7, sz, sz * 1.3);
        }
        l.globalAlpha = 1;
      };
      masked(c, env, 'sky', l => draw(l, false));
      if (wl !== null) masked(c, env, 'water', l => draw(l, true));
    },
    state: () => ({ t: st.t, list: st.list.map(L => ({ ...L })) }),
  };
}

registerSkyFx('moon', 'Moon', moon);
registerSkyFx('meteors', 'Shooting stars', meteors);
registerSkyFx('lanterns', 'Sky lanterns', lanterns);
export const SKY_MAKERS = { moon, meteors, lanterns };
