// Replays the realistic-engine reference runs (web/reference_pyro.py) in JavaScript. Used by the Verify page and
// fw_pyro.test.mjs.
import { Sim } from './fw_pyro.js';
import { Director } from './fw_director.js';
import { TYPES } from './fw_shells.js';
import { HeartPattern } from './fw_patterns.js';
import { GLYPHS } from './fw_glyphs.js';
import { pyRand } from './fw_rand.js';

const glyphPoints = ch => {
  const out = [];
  (GLYPHS[ch.toUpperCase()] || []).forEach((line, r) => [...line].forEach((cell, c) => { if (cell === '#') out.push([c, r]); }));
  return out;
};

export function messagePoints(text, heightM = 40) {          // web/reference_pyro.py message_points
  const dots = [];
  [...text].forEach((ch, i) => { for (const [c, r] of glyphPoints(ch)) dots.push([i * 6 + c, r]); });
  const width = text.length * 6 - 1, k = heightM / 7;
  return dots.map(([c, r]) => {
    const hue = c / Math.max(1, width);
    return [(c - (width - 1) / 2) * k, ((7 - 1) / 2 - r) * k, 255, Math.trunc(120 + 135 * hue), Math.trunc(255 - 200 * hue)];
  });
}

const fsum = xs => {                                          // exact-ish sum like math.fsum (Neumaier)
  let s = 0, c = 0;
  for (const x of xs) { const t = s + x; c += Math.abs(s) >= Math.abs(x) ? (s - t) + x : (x - t) + s; s = t; }
  return s + c;
};

function snap(sim, counts) {
  const kinds = {};
  for (const s of sim.stars) (kinds[s.kind] ||= []).push(s);
  const out = {};
  for (const k of Object.keys(kinds).sort()) {
    const v = kinds[k];
    out[k] = { n: v.length, x: fsum(v.map(s => s.x)), y: fsum(v.map(s => s.y)), z: fsum(v.map(s => s.z)),
      vx: fsum(v.map(s => s.vx)), vy: fsum(v.map(s => s.vy)) };
  }
  return { frame: sim.frame, events: { ...counts }, kinds: out };
}

export function runPyro(c) {
  const rand = pyRand(c.seed), sim = new Sim(rand, { aspect: c.aspect ?? 16 / 9 });
  sim.gravity_scale = c.gravity ?? 1; sim.height_scale = c.height ?? 1; sim.star_scale = c.stars ?? 1;
  sim.lift_time = 'lift' in c ? c.lift : 3;
  const d = new Director(rand);
  d.ground = c.ground ?? false; d.niagara_height = c.niagara ?? null; d.rate = c.rate ?? d.rate;
  const devices = {};                                         // mode "ground": step -> devices lit before that step
  for (const dev of c.devices || []) (devices[Math.trunc(dev[0] * 60 + 0.5)] ||= []).push(dev);
  if (c.mode === 'finale') d.startFinale(sim);
  if (c.mode === 'pattern') d.pattern = new HeartPattern();
  let duration = null;
  if (c.mode === 'message') {
    const msgs = c.text.split('|').map(t => ({ points: messagePoints(t), hold: 2 }));
    duration = d.queueMessages(sim, msgs, c.opener ?? 'off', c.finale ?? false);
  }
  else if (c.mode === 'types') {
    d.auto = false;
    [...TYPES, 'salute'].forEach((t, i) => sim.launch(d.recipe(t), -0.9 + i * 0.15, null, null, 0));
  } else if (c.mode === 'ground') d.auto = false;
  const counts = { launch: 0, burst: 0, crackle: 0 }, snapshots = [], steps = Math.trunc(c.seconds * 60);
  for (let step = 0; step <= steps; step++) {
    if (step % c.snap_every === 0) snapshots.push(snap(sim, counts));
    for (const [, kind, x, z, opts] of devices[step] || []) sim.ground(kind, x, z, opts);
    d.step(sim); sim.step();
    for (const e of sim.events) counts[e[0]] = (counts[e[0]] ?? 0) + 1;
  }
  return { snapshots, duration };
}
