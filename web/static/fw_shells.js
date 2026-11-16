// Copy of models/shell_types.py: what each shell type does when it bursts (see the Python docstring for the types).
// Random numbers are drawn in the same order as the Python (checked by fw_pyro.test.mjs).
import { Star, sphereDirs } from './fw_pyro.js';
import { PALETTE, TAIL_GOLD, TAIL_SILVER, pickColor } from './fw_palette.js';

export const TYPES = ['peony', 'chrysanthemum', 'willow', 'kamuro', 'palm', 'crossette', 'ring', 'horsetail', 'crackle',
  'strobe', 'multibreak'];
export const LABELS = { peony: 'Peony', chrysanthemum: 'Chrysanthemum', willow: 'Willow', kamuro: 'Kamuro', palm: 'Palm',
  crossette: 'Crossette', ring: 'Ring', horsetail: 'Horsetail', crackle: 'Crackle', strobe: 'Strobe',
  multibreak: 'Multi-break', salute: 'Salute' };

export function makeRecipe(rand, type, color = null) {
  if (color === null) color = pickColor(rand);
  const second = pickColor(rand);
  const r = { type, color: [...color], color2: null, pistil: null, size: rand.uniform(0.85, 1.15) };
  const roll = rand.random();
  if (['peony', 'ring', 'chrysanthemum'].includes(type) && roll < 0.4) r.pistil = second;
  else if (['peony', 'crossette'].includes(type) && roll < 0.7) r.color2 = second;
  return r;
}

const event = (sim, s, color, strength) => sim.events.push(['burst', s.x, s.y, s.z, color, strength]);

function sphere(sim, s, n, speed, k, life, color, spread = 0.08) {
  const R = sim.rand, out = [];
  for (const [dx, dy, dz] of sphereDirs(n, R.uniform(0, 2 * Math.PI))) {
    const v = speed * R.uniform(1 - spread, 1 + spread * 0.5);
    const st = new Star('star', s.x, s.y, s.z, s.vx * 0.3 + dx * v, s.vy * 0.3 + dy * v, dz * v, k,
      life * R.uniform(0.88, 1.08), color);
    st.phase = R.uniform(0, 6.2832);
    out.push(sim.add(st));
  }
  return out;
}
function tails(stars, rate, color, life, glitter = false) {
  for (const st of stars) { st.trail = rate; st.trail_color = color; st.trail_life = life; st.glitter = glitter; }
}
function change(stars, rec) { if (rec.color2) for (const st of stars) { st.color2 = rec.color2; st.change = 0.55; } }

export function burst(sim, s) {
  const rec = s.recipe, t = rec.type, R = sim.rand, q = sim.quality, size = rec.size ?? 1, c = rec.color;
  let st;
  if (t === 'peony') { st = sphere(sim, s, sim.count(110), 52 * size, 0.034, R.uniform(1.6, 2.1), c); change(st, rec); }
  else if (t === 'chrysanthemum') {
    st = sphere(sim, s, sim.count(95), 52 * size, 0.034, R.uniform(1.7, 2.2), c);
    tails(st, 22 * q, R.random() < 0.6 ? TAIL_GOLD : TAIL_SILVER, 0.55);
  } else if (t === 'willow') {
    st = sphere(sim, s, sim.count(70), 40 * size, 0.09, R.uniform(3.6, 4.6), PALETTE.gold);
    for (const x of st) x.bright = 0.55;
    tails(st, 30 * q, TAIL_GOLD, 1.3);
  } else if (t === 'kamuro') {
    st = sphere(sim, s, sim.count(85), 44 * size, 0.07, R.uniform(3.0, 3.8), [255, 205, 130]);
    for (const x of st) x.bright = 0.8;
    tails(st, 38 * q, [255, 214, 150], 1.0, true);
  } else if (t === 'palm') {
    st = sphere(sim, s, Math.max(6, Math.trunc(9 * sim.star_scale)), 60 * size, 0.02, R.uniform(2.0, 2.5), c);
    for (const x of st) x.size = 1.8;
    tails(st, 90 * q, TAIL_GOLD, 0.8);
  } else if (t === 'crossette') {
    st = sphere(sim, s, Math.max(6, Math.trunc(14 * sim.star_scale)), 44 * size, 0.03, R.uniform(1.0, 1.2), c);
    for (const x of st) { x.end = 'split'; x.size = 1.3; }
    tails(st, 28 * q, TAIL_GOLD, 0.5);
    change(st, rec);
  } else if (t === 'ring') ring(sim, s, sim.count(64), 54 * size, c);
  else if (t === 'horsetail') {
    st = sphere(sim, s, sim.count(34), 20 * size, 0.03, R.uniform(2.8, 3.4), c);
    tails(st, 48 * q, R.random() < 0.5 ? TAIL_SILVER : TAIL_GOLD, 1.5);
  } else if (t === 'crackle') {
    st = sphere(sim, s, sim.count(80), 48 * size, 0.04, R.uniform(1.3, 1.7), PALETTE.gold);
    for (const x of st) x.end = 'crackle';
    tails(st, 14 * q, TAIL_GOLD, 0.4);
  } else if (t === 'strobe') {
    st = sphere(sim, s, sim.count(70), 44 * size, 0.05, R.uniform(2.4, 3.0), PALETTE.white);
    for (const x of st) x.strobe = R.uniform(0.08, 0.16);
  } else if (t === 'multibreak') {
    const n = 4 + Math.trunc(R.random() * 3);
    for (const [dx, dy, dz] of sphereDirs(n, R.uniform(0, 6.2832))) {
      const sub = new Star('sub', s.x, s.y, s.z, dx * 30, dy * 30 + 6, dz * 30, 0.01, R.uniform(0.45, 0.8),
        [255, 190, 110], 0.6, 0.9);
      sub.end = 'burst'; sub.trail = 25 * q; sub.trail_color = TAIL_GOLD; sub.trail_life = 0.4;
      sub.recipe = { type: 'peony', color: pickColor(R), color2: null, pistil: null, size: 0.5 };
      sim.add(sub);
    }
    event(sim, s, [255, 200, 140], 0.6);
    return;
  } else if (t === 'salute') {
    st = sphere(sim, s, sim.count(36), 65, 0.1, R.uniform(0.3, 0.45), PALETTE.white);
    for (const x of st) { x.bright = 1.6; x.end = 'crackle'; }
    event(sim, s, [255, 245, 230], 2.5);
    return;
  } else if (t === 'pattern') pattern(sim, s, rec);
  else if (t === 'message') message(sim, s, rec);
  if (rec.pistil) sphere(sim, s, sim.count(26), 20 * size, 0.04, R.uniform(1.1, 1.4), rec.pistil);
  event(sim, s, c, size * (t === 'willow' || t === 'horsetail' ? 0.7 : 1));
}

function ring(sim, s, n, speed, c) {
  const R = sim.rand, tilt = R.uniform(0.3, 1.3), turn = R.uniform(0, 2 * Math.PI), life = R.uniform(1.6, 2.0);
  const ct = Math.cos(tilt), st = Math.sin(tilt), cu = Math.cos(turn), su = Math.sin(turn);
  for (let i = 0; i < n; i++) {
    const a = 2 * Math.PI * i / n, px = Math.cos(a), py = Math.sin(a);
    const y = py * ct, z0 = py * st, x = px * cu - z0 * su, z = px * su + z0 * cu;
    const v = speed * R.uniform(0.97, 1.02);
    const star = new Star('star', s.x, s.y, s.z, s.vx * 0.3 + x * v, s.vy * 0.3 + y * v, z * v, 0.034,
      life * R.uniform(0.95, 1.05), c);
    star.phase = a;
    sim.add(star);
  }
}

function pattern(sim, s, rec) {
  const pts = rec.points, r = Math.max(...pts.map(([px, py]) => Math.hypot(px, py)), 1e-9);
  const speed = 50 * (rec.scale ?? 1), life = sim.rand.uniform(1.8, 2.2);
  pts.forEach(([px, py], i) => {
    const st = new Star('star', s.x, s.y, s.z, s.vx * 0.2 + px / r * speed, s.vy * 0.2 - py / r * speed, 0, 0.03,
      life, rec.color, 1, 1.1);
    st.phase = i * 0.7;
    sim.add(st);
  });
}

function message(sim, s, rec) {
  const R = sim.rand, hold = rec.hold ?? 2.5;
  rec.points.forEach((p, i) => {
    const [u, v] = p, a = R.uniform(0, 2 * Math.PI), e = R.uniform(-1, 1), sp = R.uniform(18, 34), r = Math.sqrt(1 - e * e);
    const col = [p[2], p[3], p[4]];
    const st = new Star('star', s.x, s.y, s.z, r * Math.cos(a) * sp + u * 0.8, e * sp + v * 0.8, r * Math.sin(a) * sp,
      0.06, 0, col, 1, 0.9);
    st.target = [s.x + u, s.y + v];
    st.glide = R.uniform(0.25, 0.45);
    st.hold = st.glide + 1.1 + hold;
    st.life = st.hold + R.uniform(1.4, 2.0);
    st.nograv = true; st.glitter = true; st.phase = i * 0.37;
    st.trail = 3 * sim.quality; st.trail_color = col; st.trail_life = 0.5;
    sim.add(st);
  });
}
