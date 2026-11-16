// Copy of models/director.py: random auto-launch, the choreographed finale and message shows.
import { TYPES, makeRecipe } from './fw_shells.js';

export const FINALE_SECONDS = 42;

export function finaleCues(R) {
  const cues = [];
  let t = 0.5;
  for (let i = 0; i < 3; i++) {
    const typ = ['peony', 'chrysanthemum', 'ring'][i], x = R.uniform(0.35, 0.75);
    cues.push([t, typ, -x, 0.6, 0], [t, typ, x, 0.6, 0]);
    t += 1.8;
  }
  t += 0.6;
  for (let i = 0; i < 5; i++) cues.push([t + i * 0.25, 'palm', 0, 0.7, (i - 2) * 0.12]);
  t += 4;
  for (let i = 0; i < 8; i++) cues.push([t + i * 0.5, i % 2 === 0 ? 'crossette' : 'ring', R.uniform(-0.8, 0.8), null, 0]);
  t += 5;
  for (let i = 0; i < 6; i++) cues.push([t + i * 0.12, i % 2 === 0 ? 'willow' : 'kamuro', -0.8 + i * 0.32, 0.72, 0]);
  t += 4.5;
  for (let i = 0; i < 4; i++) cues.push([t + i * 0.6, 'strobe', R.uniform(-0.7, 0.7), null, 0]);
  t += 3;
  const n = 26;
  for (let i = 0; i < n; i++) {
    const typ = ['chrysanthemum', 'peony', 'crackle', 'multibreak', 'horsetail'][Math.trunc(R.random() * 5)];
    cues.push([t, typ, R.uniform(-0.9, 0.9), null, 0]);
    t += 0.45 - 0.3 * i / n;
  }
  t += 0.4;
  for (let i = 0; i < 10; i++) cues.push([t + i * 0.15, 'salute', R.uniform(-0.8, 0.8), R.uniform(0.5, 0.8), 0]);
  for (let i = 0; i < 3; i++) cues.push([t + 1.2 + i * 0.1, 'kamuro', -0.5 + i * 0.5, 0.78, 0]);
  return cues.map((c, i) => [c, i]).sort((a, b) => a[0][0] - b[0][0] || a[1] - b[1]).map(a => a[0]);  // stable
}

export class Director {
  constructor(rand) {
    this.rand = rand; this.mode = 'auto'; this.auto = true; this.rate = 1.1; this.shell_type = 'mixed';
    this.color = null; this.pattern = null; this.pattern_scale = 1; this.cues = []; this.t0 = 0;
  }
  recipe(type = null) {
    const R = this.rand;
    if (type === null) {
      if (this.pattern) type = 'pattern';
      else if (this.shell_type === 'mixed') type = TYPES[Math.trunc(R.random() * TYPES.length)];
      else type = this.shell_type;
    }
    const rec = makeRecipe(R, type === 'pattern' ? 'peony' : type, this.color);
    if (type === 'pattern') {
      rec.type = 'pattern'; rec.points = this.pattern.get_points(0, 0).map(p => [...p]); rec.scale = this.pattern_scale;
    }
    return rec;
  }
  startFinale(sim) { this.mode = 'finale'; this.t0 = sim.time; this.cues = finaleCues(this.rand); }
  queueMessages(sim, messages, gap = 2.5) {
    this.mode = 'finale'; this.t0 = sim.time; this.cues = [];
    let t = 0.3;
    for (const m of messages) { this.cues.push([t, 'message', m]); t += 3 + (m.hold ?? 2.5) + gap; }
  }
  step(sim) {
    if (this.mode === 'finale') {
      const now = sim.time - this.t0;
      while (this.cues.length && this.cues[0][0] <= now) {
        const cue = this.cues.shift();
        if (cue[1] === 'message') {
          const m = cue[2];
          sim.launch({ type: 'message', color: [255, 240, 220], color2: null, pistil: null, size: 1, points: m.points,
            hold: m.hold ?? 2.5 }, 0, 450, m.height ?? 0.62, 0);
        } else {
          const [, typ, x, h, tilt] = cue;
          sim.launch(this.recipe(typ), x, null, h, tilt);
        }
      }
      if (!this.cues.length && now > 1) this.mode = 'auto';
      return;
    }
    if (this.auto && this.rand.random() < this.rate / 60) sim.launch(this.recipe());
  }
}
