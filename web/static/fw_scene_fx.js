// Animated objects of the scenes (always on, fw_fx.js registerSceneFx): bobbing boats and a sweeping lighthouse
// beam in the Harbour, chimney smoke drifting with the wind in the Snowy Village, blinking aviation lights on towers
// and bridge pylons, searchlights over the Waterfront, turning wind turbines in the Countryside. Positions come from
// the painter (S.boats / S.lighthouse / S.chimneys / S.beacons / S.turbines, device px; drawn in CSS px).
// update() is pure, seeded arithmetic (node-testable through state()); sprites are made lazily when drawing.
import { registerSceneFx } from './fw_fx.js';
import { hash, prng } from './fw_noise.js';
import { boat } from './fw_scenery_houses.js';
import { combine, cssK, horizonCss, isDuskEnv, masked, softSprite } from './fw_fx_masks.js';

// ---- Boats: pre-rendered sprites that bob and roll on the swell, with a wobbling reflection and light streaks.
function boats(env) {
  const S = env.scenery, list = (S.boats || []).map(([x, y, len, seed]) => {
    const r = prng(seed);
    return { x, y, len, seed, ph: r() * 6.28, w: 0.9 + r() * 0.6, roll: 0.025 + r() * 0.03, sail: r() < 0.5, bob: 0, ang: 0 };
  });
  const st = { t: 0 };
  let sprites = null, kOf = 0;
  const make = env => {
    const k = cssK(env); kOf = k;
    sprites = list.map(B => {
      const L = B.len * k, sc = env.cssH / 800, c = document.createElement('canvas');
      c.width = Math.ceil(L * 1.5); c.height = Math.ceil(L * 1.9);
      B.top = boat(c.getContext('2d'), c.width / 2, c.height * 0.85, L, sc, prng(B.seed + 1), { sail: B.sail, colour: isDuskEnv(env) ? [30, 34, 50] : [20, 22, 30] });
      return c;
    });
  };
  return {
    update(dt, env) {
      st.t += dt;
      const amp = (env.reduced ? 0.5 : 1) * (1 + Math.abs(env.wind || 0) * 0.1);
      for (const B of list) {
        B.bob = Math.sin(st.t * B.w + B.ph) * 1.6 * amp;           // CSS px
        B.ang = Math.sin(st.t * B.w * 0.8 + B.ph * 1.7) * B.roll * amp;
      }
    },
    drawSky(c, env) {
      if (!sprites || kOf !== cssK(env)) make(env);
      const k = kOf;
      list.forEach((B, i) => {
        const sp = sprites[i], x = B.x * k, y = B.y * k + B.bob, ox = sp.width / 2, oy = sp.height * 0.85;
        c.save(); c.translate(x, y); c.rotate(B.ang); c.scale(1, -0.8); c.globalAlpha = 0.28; c.drawImage(sp, -ox, -oy); c.restore();
        const lx = x + B.top[0] - B.top[1] * Math.sin(B.ang) * 0.8, len = B.len * k * 1.2;   // masthead light streaks
        c.fillStyle = 'rgb(255,240,210)';
        for (let j = 0; j < 7; j++) {
          const d = (j + 1) / 8, jit = (hash(B.seed, j, Math.floor(st.t * 5)) - 0.5) * 4 * (1 + d * 3);
          c.globalAlpha = 0.35 * (1 - d); c.fillRect(lx + jit - (1 + 4 * d), y + 3 + d * len, 2 + 8 * d, 1);
        }
        c.globalAlpha = 1; c.save(); c.translate(x, y); c.rotate(B.ang); c.drawImage(sp, -ox, -oy); c.restore();
      });
    },
    state: () => ({ t: st.t, boats: list.map(B => [B.bob, B.ang]) }),
  };
}

// ---- Lighthouse: a beam sweeping round; a flash when it points at the viewer.
function lighthouse(env) {
  const st = { t: 0, a: 0 };
  return {
    update(dt, env) { st.t += dt; st.a = (st.a + dt * (env.reduced ? 0.35 : 0.9)) % 6.2832; },
    drawSky(c, env) {
      const L = env.scenery.lighthouse; if (!L) return;
      const k = cssK(env), x = L[0] * k, y = L[1] * k, s = env.cssH / 800, ca = Math.cos(st.a), toward = Math.max(0, Math.sin(st.a));
      const len = env.cssW * 0.45 * Math.abs(ca) + 20 * s, ex = x + Math.sign(ca) * len, w = 6 * s + len * 0.06;
      const g = c.createLinearGradient(x, y, ex, y);
      g.addColorStop(0, `rgba(255,245,220,${0.22 + 0.2 * toward})`); g.addColorStop(1, 'rgba(255,245,220,0)');
      c.fillStyle = g; c.beginPath(); c.moveTo(x, y - 1.5 * s); c.lineTo(ex, y - w - 4 * s); c.lineTo(ex, y + w - 4 * s); c.lineTo(x, y + 1.5 * s); c.fill();
      const f = Math.pow(toward, 12), r = (8 + 40 * f) * s;
      c.globalAlpha = 0.5 + 0.5 * f; c.drawImage(softSprite([255, 245, 220], 0.1), x - r, y - r, 2 * r, 2 * r); c.globalAlpha = 1;
    },
    state: () => ({ t: st.t, a: st.a }),
  };
}

// ---- Chimney smoke: puffs rising, slowing, spreading and drifting downwind, fading out.
export function smoke(env) {
  const rnd = prng((env.seed ^ 0x5307e) >>> 0), S = env.scenery, st = { t: 0, list: [], next: 0 };
  const every = 0.32, life = 6;
  return {
    update(dt, env) {
      st.t += dt;
      const k = cssK(env), s = env.cssH / 800, wind = (env.wind || 0) * 5 * s;
      while (st.t >= st.next) {
        st.next += every;
        for (const [x, y, w] of S.chimneys || []) st.list.push({ x: x * k + (rnd() - 0.5) * w * k * 0.4, y: y * k, r: Math.max(1, w * k * 0.45), age: 0, vy: -(10 + rnd() * 6) * s, ph: rnd() * 6.28 });
      }
      for (const p of st.list) {
        p.age += dt; const f = Math.min(1, p.age / 3);
        p.y += p.vy * (1 - 0.6 * f) * dt; p.x += (wind * f + Math.sin(p.age * 0.8 + p.ph) * 2 * s) * dt; p.r += (2.2 + 1.5 * f) * s * dt;
      }
      st.list = st.list.filter(p => p.age < life);
    },
    drawSky(c, env) {
      const sp = softSprite(isDuskEnv(env) ? [150, 158, 182] : [118, 124, 142], 0.25);
      for (const p of st.list) {
        const a = p.age / life;
        c.globalAlpha = 0.22 * Math.min(1, p.age * 2) * (1 - a) * (1 - a);
        c.drawImage(sp, p.x - p.r * 1.6, p.y - p.r * 1.6, p.r * 3.2, p.r * 3.2);
      }
      c.globalAlpha = 1;
    },
    state: () => ({ t: st.t, n: st.list.length, list: st.list.map(p => [p.x, p.y, p.r]) }),
  };
}

// ---- Aviation warning lights: red flashes, nearly in step across a skyline (towers are often synchronised).
export function beacons(env) {
  const S = env.scenery, st = { t: 0 }, ph = (S.beacons || []).map((_, i) => hash(env.seed & 0xffff, i) * 0.25);
  const on = i => ((st.t + ph[i]) % 1.6) < 0.35;
  return {
    update(dt) { st.t += dt; },
    drawSky(c, env) {
      const k = cssK(env), sp = softSprite([255, 50, 35], 0.05);
      (S.beacons || []).forEach(([x, y, r], i) => {
        if (!on(i)) return;
        const R = Math.max(3, r * k * 4.5);
        c.globalAlpha = 0.7; c.drawImage(sp, x * k - R, y * k - R, 2 * R, 2 * R);
        c.globalAlpha = 1; c.fillStyle = 'rgb(255,90,70)'; c.fillRect(x * k - 0.8, y * k - 0.8, 1.6, 1.6);
      });
      c.globalAlpha = 1;
    },
    state: () => ({ t: st.t, on: (S.beacons || []).map((_, i) => on(i)) }),
  };
}

// ---- Searchlights sweeping slowly above the skyline (cut to the open sky).
function searchlights(env) {
  const rnd = prng((env.seed ^ 0x5ea7c4) >>> 0), beams = [0, 1].map(i => ({ x: 0.25 + i * 0.45 + rnd() * 0.1, ph: rnd() * 6.28, w: 0.13 + rnd() * 0.08, a: 0 }));
  const st = { t: 0 };
  return {
    update(dt, env) { st.t += dt * (env.reduced ? 0.4 : 1); for (const B of beams) B.a = Math.sin(st.t * B.w + B.ph) * 0.38; },
    drawSky(c, env) {
      const hz = horizonCss(env), L = hz * 1.1, k = isDuskEnv(env) ? 0.5 : 1;
      masked(c, env, 'sky', l => {
        for (const B of beams) {
          const x = B.x * env.cssW, ex = x + Math.sin(B.a) * L, ey = hz - Math.cos(B.a) * L, w = L * 0.022;
          const g = l.createLinearGradient(x, hz, ex, ey);
          g.addColorStop(0, `rgba(210,225,255,${0.09 * k})`); g.addColorStop(0.5, `rgba(210,225,255,${0.04 * k})`); g.addColorStop(1, 'rgba(210,225,255,0)');
          l.fillStyle = g; l.beginPath(); l.moveTo(x - 2, hz); l.lineTo(ex - w * Math.cos(B.a), ey - w * Math.sin(B.a));
          l.lineTo(ex + w * Math.cos(B.a), ey + w * Math.sin(B.a)); l.lineTo(x + 2, hz); l.fill();
        }
      });
    },
    state: () => ({ t: st.t, a: beams.map(B => B.a ?? 0) }),
  };
}

// ---- Wind turbines: three blades turning (speed with the wind), synchronised red lights on the nacelles.
function turbines(env) {
  const S = env.scenery, st = { t: 0, rot: (S.turbines || []).map((_, i) => hash(env.seed & 0xffff, i, 9) * 6.28) };
  return {
    update(dt, env) {
      st.t += dt;
      const w = (0.6 + 0.12 * Math.abs(env.wind || 0)) * (env.reduced ? 0.5 : 1);
      st.rot = st.rot.map((a, i) => (a + dt * w * (0.85 + 0.3 * hash(7, i))) % 6.2832);
    },
    drawSky(c, env) {
      const k = cssK(env), dusk = isDuskEnv(env), blink = (st.t % 2) < 0.6, sp = softSprite([255, 50, 35], 0.12);
      c.fillStyle = dusk ? 'rgb(70,78,104)' : 'rgb(46,50,66)';
      (S.turbines || []).forEach(([x, y, len], i) => {
        const X = x * k, Y = y * k, L = len * k;
        for (let b = 0; b < 3; b++) {
          const a = st.rot[i] + b * 2.0944, ca = Math.cos(a), sa = Math.sin(a), wd = Math.max(0.8, L * 0.04);
          c.beginPath(); c.moveTo(X - sa * wd, Y + ca * wd); c.lineTo(X + ca * L, Y + sa * L); c.lineTo(X + sa * wd * 0.6, Y - ca * wd * 0.6); c.fill();
        }
        if (blink) { const R = Math.max(3, L * 0.14); c.globalAlpha = 0.9; c.drawImage(sp, X - R, Y - R - 1, 2 * R, 2 * R); c.globalAlpha = 1; }
      });
    },
    state: () => ({ t: st.t, rot: [...st.rot] }),
  };
}

export const SCENE_MAKERS = {
  Harbour: env => combine(boats(env), lighthouse(env)),
  'Snowy Village': smoke,
  'River Bridge': beacons,
  Waterfront: env => combine(searchlights(env), beacons(env)),
  Cityscape: beacons,
  Countryside: turbines,
};
for (const [name, make] of Object.entries(SCENE_MAKERS)) registerSceneFx(name, make);
