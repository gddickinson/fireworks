// Copy of models/ground_effects.py: ground devices (gerb, roman candle, mine, cake, niagara) as emitters that
// Sim.step() advances before the stars move (see the Python docstring for the physics). Random numbers are drawn in
// the same order as the Python (checked by fw_pyro.test.mjs).
import { Star, SHELL_DRAG } from './fw_pyro.js';
import { PALETTE, TAIL_GOLD, TAIL_SILVER, pickColor } from './fw_palette.js';

export const DEVICES = ['gerb', 'candle', 'mine', 'cake', 'niagara'];
export const LABELS = { gerb: 'Gerb (fountain)', candle: 'Roman candle', mine: 'Mine', cake: 'Cake (barrage)',
  niagara: 'Niagara falls' };
export const AUTO_DEVICES = ['gerb', 'candle', 'mine', 'cake'];   // niagara needs a bridge: finale only
export const GROUND_DEPTH = [110, 180];
const CAKE_STYLES = ['peony', 'chrysanthemum', 'crackle'];

const opt = (opts, key, fn) => (key in opts ? opts[key] : fn());

export class Emitter {
  constructor(kind, x, y, z, life) {
    this.kind = kind; this.x = x; this.y = y; this.z = z; this.age = 0; this.life = life; this.acc = 0;
    this.rate = 0; this.speed = 0; this.color = TAIL_GOLD; this.glitter = false;
    this.n = 0; this.fired = 0; this.every = 0; this.width = 0; this.style = 'peony'; this.tilt = 0;
  }
}

export function makeDevice(sim, kind, x = null, z = null, opts = null) {
  if (!DEVICES.includes(kind)) throw new Error(`unknown ground device ${kind}`);
  const R = sim.rand, q = sim.quality;
  opts = opts || {};
  if (z === null || z === undefined) z = R.uniform(GROUND_DEPTH[0], GROUND_DEPTH[1]);
  const xm = x === null || x === undefined ? R.uniform(-0.7, 0.7) * sim.x_max(z) : x * sim.x_max(z);
  let e;
  if (kind === 'gerb') {
    e = new Emitter(kind, xm, 0.5, z, opt(opts, 'duration', () => R.uniform(4, 8)));
    const silver = opt(opts, 'color', () => (R.random() < 0.4 ? 'silver' : 'gold')) === 'silver';
    e.color = silver ? TAIL_SILVER : TAIL_GOLD;
    e.glitter = !!opt(opts, 'glitter', () => R.random() < 0.35);
    e.rate = 240 * q; e.speed = R.uniform(17, 22);
  } else if (kind === 'candle') {
    e = new Emitter(kind, xm, 0.5, z, 0);
    e.n = Math.trunc(opts.shots ?? 8); e.every = 0.45; e.tilt = +(opts.tilt ?? 0);
    e.life = 0.1 + e.n * e.every;
  } else if (kind === 'mine') {
    e = new Emitter(kind, xm, 0.5, z, 0);
    e.color = pickColor(R);
  } else if (kind === 'cake') {
    e = new Emitter(kind, xm, 0.3, z, 0);
    e.n = Math.trunc(opts.shots ?? 16); e.every = 0.18;
    e.style = opt(opts, 'style', () => CAKE_STYLES[Math.trunc(R.random() * CAKE_STYLES.length)]);
    e.life = 0.1 + e.n * e.every;
  } else {
    e = new Emitter(kind, xm, +(opts.height ?? 18), z, opt(opts, 'duration', () => R.uniform(9, 12)));
    e.width = +(opts.width ?? 0.8) * sim.x_max(z);
    e.n = Math.max(6, Math.trunc(e.width / 2.5));
    e.rate = 24 * e.n * q;
    e.color = PALETTE.gold;
  }
  if (kind === 'gerb' || kind === 'niagara') sim._pending.push(['ground', e.x, e.y + 0.5, e.z, e.color, kind === 'gerb' ? 0.15 : 0.4, e.life]);
  return e;
}

function envelope(e, ramp) {                                  // lights over `ramp` s, dies away over the last 15 %
  const up = Math.min(1, e.age / ramp), tail = 0.15 * e.life;
  return up * Math.min(1, Math.max(0, (e.life - e.age) / tail));
}

export function stepDevice(sim, e, dt, crowded) {            // false when the device has finished
  e.age += dt;
  if (e.kind === 'gerb' || e.kind === 'niagara') {
    e.acc += e.rate * envelope(e, e.kind === 'gerb' ? 0.4 : 1) * dt;
    while (e.acc >= 1) {
      e.acc -= 1;
      if (!crowded) (e.kind === 'gerb' ? gerbSpark : niagaraSpark)(sim, e);
    }
  } else if (e.kind === 'mine') { mine(sim, e); return false; }
  else {
    while (e.fired < e.n && e.age >= 0.1 + e.fired * e.every) {
      (e.kind === 'candle' ? candleShot : cakeShot)(sim, e);
      e.fired++;
    }
  }
  return e.age < e.life;
}

function star(sim, kind, e, x, y, vx, vy, vz, k, life, color, bright = 1, size = 1) {
  const s = new Star(kind, x, y, e.z, vx, vy, vz, k, life, color, bright, size);
  s.ground = true;
  return sim.add(s);
}

function cone(R, half, speed) {                               // uniform over the cap of half-angle `half`
  const th = half * Math.sqrt(R.random()), ph = R.uniform(0, 2 * Math.PI);
  return [Math.sin(th) * Math.cos(ph) * speed, Math.cos(th) * speed, Math.sin(th) * Math.sin(ph) * speed];
}

function gerbSpark(sim, e) {
  const R = sim.rand, [vx, vy, vz] = cone(R, 0.16, e.speed * R.uniform(0.75, 1.1));
  const s = star(sim, 'spark', e, e.x, e.y, vx, vy, vz, 0.07, R.uniform(0.9, 1.6), e.color, e.glitter ? 0.75 : 0.6, 0.8);
  s.glitter = e.glitter;
  s.phase = R.uniform(0, 6.2832);
}

function niagaraSpark(sim, e) {
  const R = sim.rand, i = Math.trunc(R.random() * e.n), x = e.x - e.width / 2 + (i + 0.5) * e.width / e.n;
  const vx = R.uniform(-0.6, 0.6), vy = R.uniform(-1.5, 0.3), vz = R.uniform(-0.4, 0.4);
  const s = star(sim, 'spark', e, x, e.y, vx, vy, vz, 0.3, R.uniform(2.2, 3.4), e.color, 0.8, 0.75);
  s.phase = R.uniform(0, 6.2832);
}

function candleShot(sim, e) {
  const R = sim.rand, a = e.tilt + R.uniform(-0.05, 0.05), v = R.uniform(28, 34), vz = R.uniform(-1, 1);
  const life = R.uniform(1.6, 2.0);
  const s = star(sim, 'star', e, e.x, e.y, Math.sin(a) * v, Math.cos(a) * v, vz, 0.035, life, pickColor(R), 1.1, 1.25);
  s.trail = 18 * sim.quality; s.trail_color = TAIL_GOLD; s.trail_life = 0.35;
  s.phase = e.fired * 0.9;
  sim.events.push(['launch', e.x, e.z, 'candle']);
}

function mine(sim, e) {
  const R = sim.rand, n = sim.count(60);
  for (let i = 0; i < n; i++) {
    const [vx, vy, vz] = cone(R, 0.35, R.uniform(38, 58));
    const s = star(sim, 'star', e, e.x, e.y, vx, vy, vz, 0.035, R.uniform(1.4, 2.0), e.color);
    s.phase = i * 0.37;
  }
  for (let i = 0; i < 6; i++) {
    const [vx, vy, vz] = cone(R, 0.3, R.uniform(48, 62));
    const s = star(sim, 'star', e, e.x, e.y, vx, vy, vz, 0.025, R.uniform(1.8, 2.3), PALETTE.gold, 0.7, 1.4);
    s.trail = 40 * sim.quality; s.trail_color = TAIL_GOLD; s.trail_life = 0.6;
  }
  sim.events.push(['burst', e.x, 2, e.z, e.color, 0.8]);
}

function cakeShot(sim, e) {
  const R = sim.rand, m = 8, j = e.fired % (2 * m - 2), p = j < m ? j : 2 * m - 2 - j;
  const a = 0.45 * (2 * p / (m - 1) - 1), v = R.uniform(44, 50);
  const s = new Star('shell', e.x, e.y, e.z, Math.sin(a) * v, Math.cos(a) * v, 0, SHELL_DRAG * 1.6, 30, [255, 160, 70], 1, 1);
  s.trail = 30 * sim.quality; s.trail_color = TAIL_GOLD; s.trail_life = 0.4;
  s.end = 'burst';
  s.recipe = { type: e.style, color: pickColor(R), color2: null, pistil: null, size: 0.42 };
  sim.add(s);
  sim.events.push(['launch', e.x, e.z, 'cake']);
}
