// Copy of models/pyro.py: realistic firework physics in 3-D metres (x right, y up, z away from the viewer),
// gravity and quadratic air drag relative to the wind, fixed step DT = 1/60 s. Random numbers are drawn in the same
// order as the Python, so a seeded run matches web/reference.py (fw_pyro.test.mjs). Shell recipes: fw_shells.js.
import { burst } from './fw_shells.js';

export const DT = 1 / 60, G = 9.81, FOCAL = 1.5, SHELL_DEPTH = [300, 600], SHELL_DRAG = 0.006;

export class Star {
  constructor(kind, x, y, z, vx, vy, vz, k, life, color, bright = 1, size = 1) {
    this.kind = kind; this.x = x; this.y = y; this.z = z; this.vx = vx; this.vy = vy; this.vz = vz; this.k = k;
    this.age = 0; this.life = life; this.color = color; this.color2 = null; this.change = 1;
    this.bright = bright; this.size = size;
    this.trail = 0; this.trail_color = color; this.trail_life = 0.6; this.acc = 0;
    this.glitter = false; this.strobe = 0; this.phase = 0;
    this.end = null; this.recipe = null; this.target = null; this.glide = 0; this.hold = 0; this.nograv = false;
    this.theta0 = 0;                                          // rising shell: exact drag trajectory (0: integrate)
    this.rate = 1;                                            // rising shell: playback rate of its climb (Lift time)
  }
}

export function sphereDirs(n, rot) {                          // Fibonacci lattice turned by rot about the vertical
  const golden = Math.PI * (3 - Math.sqrt(5)), out = [];
  for (let i = 0; i < n; i++) {
    const y = 1 - 2 * (i + 0.5) / n, r = Math.sqrt(Math.max(0, 1 - y * y)), a = i * golden + rot;
    out.push([r * Math.cos(a), y, r * Math.sin(a)]);
  }
  return out;
}

export class Sim {
  constructor(rand, { aspect = 16 / 9, horizon = 0.86, quality = 1, budget = 1e6 } = {}) {
    this.rand = rand; this.aspect = aspect; this.horizon = horizon; this.quality = quality; this.budget = budget;
    this.stars = []; this.events = []; this.time = 0; this.frame = 0;
    this.wind = 1.5; this.gravity_scale = 1; this.height_scale = 1; this.star_scale = 1;
    this.lift_time = 3;                                       // s to the burst at most; longer climbs play faster (null: real)
    this._new = []; this._pending = [];                        // launches between frames, reported by the next step
  }
  x_max(z) { return z * this.aspect / (2 * FOCAL); }
  y_top(z) { return z * this.horizon / FOCAL; }
  count(n) { return Math.max(4, Math.trunc(n * this.star_scale * this.quality)); }

  launch(recipe, x = null, z = null, height = null, tilt = 0) {
    const R = this.rand;
    if (z === null) z = R.uniform(SHELL_DEPTH[0], SHELL_DEPTH[1]);
    x = x === null ? R.uniform(-0.85, 0.85) * this.x_max(z) : x * this.x_max(z);
    if (height === null) height = R.uniform(0.4, 0.75);
    const h = height * this.y_top(z) * this.height_scale, g = G * this.gravity_scale, k = SHELL_DRAG;
    const vy = g > 0 ? Math.sqrt(g / k * (Math.exp(2 * k * h) - 1)) : 60;
    const vx = R.uniform(-1.5, 1.5) + tilt * vy;
    const s = new Star('shell', x, 0, z, vx, vy, 0, k, g > 0 ? 30 : h / vy, [255, 160, 70], 1, 1.4);
    if (g > 0) {
      s.theta0 = Math.atan(vy * Math.sqrt(k / g));
      const climb = s.theta0 / Math.sqrt(g * k);              // physical time to the top
      if (this.lift_time !== null && this.lift_time < climb) s.rate = climb / this.lift_time;
    }
    s.trail = (recipe.type === 'palm' ? 110 : 55) * this.quality;
    s.trail_color = [255, 150, 52]; s.trail_life = 0.55; s.end = 'burst'; s.recipe = recipe;
    this.stars.push(s);
    this._pending.push(['launch', x, z, recipe.type]);
    return s;
  }

  step() {
    this.events = this._pending; this._pending = [];
    const R = this.rand, g = G * this.gravity_scale, wind = this.wind, alive = [], born = [];
    const crowded = this.stars.length > this.budget;
    for (const s of this.stars) {
      if (s.age < 0) { s.age += DT; alive.push(s); continue; }
      if (s.theta0 > 0) {                                     // rising shell: exact solution of the climb against drag
        const th = Math.max(0, s.theta0 - Math.sqrt(g * s.k) * (s.age + DT) * s.rate);
        s.vy = Math.sqrt(g / s.k) * Math.tan(th);
        s.x += s.vx * DT * s.rate;
        s.y = Math.log(Math.cos(th) / Math.cos(s.theta0)) / s.k;
      } else if (s.target !== null && s.glide <= s.age && s.age < s.hold) {
        const w = 5.5;
        s.vx += (w * w * (s.target[0] - s.x) - 2 * w * s.vx) * DT;
        s.vy += (w * w * (s.target[1] - s.y) - 2 * w * s.vy) * DT;
        s.vz += (-2 * w * s.vz) * DT;
        s.x += s.vx * DT; s.y += s.vy * DT; s.z += s.vz * DT;
      } else {
        const rx = s.vx - wind, sp = Math.sqrt(rx * rx + s.vy * s.vy + s.vz * s.vz), d = s.k * sp * DT;
        s.vx -= d * rx; s.vy -= d * s.vy; s.vz -= d * s.vz;
        if (!(s.nograv && s.age < s.glide)) s.vy -= g * DT;
        s.x += s.vx * DT; s.y += s.vy * DT; s.z += s.vz * DT;
      }
      s.age += DT;
      if (s.trail > 0 && !crowded) {
        s.acc += s.trail * DT;
        while (s.acc >= 1) { s.acc -= 1; born.push(this._spark(s)); }
      }
      if (s.kind === 'shell' && s.vy <= 0) s.age = s.life;
      if (s.age >= s.life) {
        if (s.end === 'burst') burst(this, s);
        else if (s.end === 'split') this._split(s, born);
        else if (s.end === 'crackle') {
          const p = new Star('pop', s.x, s.y, s.z, s.vx * 0.3, s.vy * 0.3, s.vz * 0.3, 0.5, 0.07, s.color, 1, 1.6);
          p.age = -R.uniform(0, 0.6);
          born.push(p);
          this.events.push(['crackle', s.x, s.y, s.z]);
        }
        continue;
      }
      alive.push(s);
    }
    this.stars = alive.concat(born, this._new);
    this._new = [];
    this.time += DT; this.frame++;
  }
  add(star) { this._new.push(star); return star; }
  _spark(s) {
    const R = this.rand, [f, j] = s.kind !== 'shell' ? [0.15, 6] : [0, 3];   // a shell's tail stays behind it
    const vx = s.vx * f + R.uniform(-j, j), vy = s.vy * f + R.uniform(-j, j);
    const sp = new Star('spark', s.x, s.y, s.z, vx, vy, s.vz * f, 1.2, s.trail_life * R.uniform(0.5, 1),
      s.trail_color, s.glitter ? 0.8 : 0.55, 0.7);
    sp.glitter = s.glitter; sp.phase = s.age * 13;
    return sp;
  }
  _split(s, born) {
    const a0 = this.rand.uniform(0, 2 * Math.PI);
    for (let i = 0; i < 4; i++) {
      const a = a0 + i * Math.PI / 2;
      const c = new Star('star', s.x, s.y, s.z, s.vx + 16 * Math.cos(a), s.vy + 16 * Math.sin(a), s.vz, s.k,
        s.life * 0.55, s.color, s.bright, s.size * 0.8);
      c.trail = s.trail; c.trail_color = s.trail_color; c.trail_life = s.trail_life * 0.7; c.phase = a;
      born.push(c);
    }
    this.events.push(['crackle', s.x, s.y, s.z]);
  }
}
