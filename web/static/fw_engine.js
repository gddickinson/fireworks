// Port of models/particle.py, models/firework.py and the animation logic of gui/canvas.py (FireworksCanvas).
// Field names follow the Python. With the default options a seeded run reproduces the Python models exactly
// (checked by fw_engine.test.mjs), including pattern bursts, gravity, launch speed and auto launch.
import { makePattern, RandomPattern } from './fw_patterns.js';
import { randomColor } from './fw_color.js';
import { pyRand } from './fw_rand.js';

// config.py FireworkConfig (checked against the Python by the node test and served by /api/defaults).
export const CONFIG = Object.freeze({
  MIN_PARTICLES: 20, MAX_PARTICLES: 200, DEFAULT_PARTICLES: 50, GRAVITY: 0.1,
  LAUNCH_SPEED_MIN: 8.0, LAUNCH_SPEED_MAX: 12.0, PARTICLE_SPEED_MIN: 2.0, PARTICLE_SPEED_MAX: 5.0,
  SPAWN_RATE: 0.1, FRAME_RATE: 60,
});
export const DEFAULT_COLOR = [255, 0, 0];
export const BACKGROUND_COLOR = [0, 0, 20];
export const DEFAULT_LAUNCH_SPEED = 10.0;  // the desktop Launch Speed slider default (100 / 10)

export class Particle {
  constructor(x, y, angle, speed, color, lifetime = 100, gravity = CONFIG.GRAVITY) {
    this.x = x; this.y = y; this.angle = angle; this.speed = speed; this.color = color;
    this.lifetime = lifetime; this.current_life = lifetime; this.gravity = gravity;
    this.velocity_x = Math.cos(angle) * speed;
    this.velocity_y = Math.sin(angle) * speed;
  }
  update() {
    this.velocity_y += this.gravity;
    this.x += this.velocity_x;
    this.y += this.velocity_y;
    this.current_life -= 1;
    return this.current_life > 0;
  }
  alpha() { return Math.trunc(255 * (this.current_life / this.lifetime)); }  // get_color().alpha()
}

export class Firework {
  constructor(x, y, color, particle_count, rand, { gravity = CONFIG.GRAVITY, launchSpeed = DEFAULT_LAUNCH_SPEED,
    pattern = null } = {}) {
    this.x = x; this.y = y; this.color = color; this.particles = []; this.exploded = false;
    this.rand = rand; this.gravity = gravity; this.pattern = pattern;
    this.velocity_y = -rand.uniform(CONFIG.LAUNCH_SPEED_MIN, CONFIG.LAUNCH_SPEED_MAX);
    if (launchSpeed !== DEFAULT_LAUNCH_SPEED) this.velocity_y *= launchSpeed / DEFAULT_LAUNCH_SPEED;
    this.particle_count = particle_count;
  }
  explode() {
    this.exploded = true;
    if (this.pattern && this.explodePattern()) return;
    for (let i = 0; i < this.particle_count; i++) {
      const angle = this.rand.uniform(0, 2 * Math.PI);
      const speed = this.rand.uniform(CONFIG.PARTICLE_SPEED_MIN, CONFIG.PARTICLE_SPEED_MAX);
      this.particles.push(new Particle(this.x, this.y, angle, speed, this.color, 100, this.gravity));
    }
  }
  // Firework._explode_pattern: one particle per pattern point, moving outwards so the burst grows into the shape;
  // the outermost point moves at PARTICLE_SPEED_MAX x pattern scale. No points -> plain burst.
  explodePattern() {
    const pts = this.pattern.get_points(this.x, this.y);
    const r = Math.max(0, ...pts.map(([px, py]) => Math.hypot(px - this.x, py - this.y)));
    if (!pts.length || r === 0) return false;
    const k = CONFIG.PARTICLE_SPEED_MAX * this.pattern.scale / r;
    for (const [px, py] of pts) {
      const dx = px - this.x, dy = py - this.y;
      this.particles.push(new Particle(this.x, this.y, Math.atan2(dy, dx), Math.hypot(dx, dy) * k, this.color, 100,
        this.gravity));
    }
    return true;
  }
  update() {
    if (!this.exploded) {
      this.y += this.velocity_y;
      this.velocity_y += this.gravity;
      if (this.velocity_y >= 0) this.explode();
    } else {
      this.particles = this.particles.filter(p => p.update());
    }
    return this.particles.length > 0 || !this.exploded;
  }
}

// The state and animation step of FireworksCanvas (drawing is in fw_draw.js).
export class Show {
  constructor(width, height, { rand = pyRand(), background = null, weather = null } = {}) {
    this.width = width; this.height = height; this.rand = rand;
    this.fireworks = [];
    this.particle_count = CONFIG.DEFAULT_PARTICLES;
    this.firework_color = DEFAULT_COLOR;
    this.use_random_colors = false;
    this.pattern = null; this.patternName = 'None';
    this.pattern_scale = 1.0; this.pattern_rotation = 0.0;
    this.pattern_options = { star_points: 5, spiral_arms: 3, text: '' };
    this.use_random_patterns = false;
    this.gravity = CONFIG.GRAVITY; this.launchSpeed = DEFAULT_LAUNCH_SPEED;
    this.autoLaunch = true;
    this.background = background; this.weather_effect = weather;
    this.frame = 0;
  }
  update() {                                                  // update_animation
    this.fireworks = this.fireworks.filter(fw => fw.update() && (fw.exploded || fw.y > -this.height));
    if (this.autoLaunch && this.rand.random() < CONFIG.SPAWN_RATE) this.add_firework();
    if (this.weather_effect) this.weather_effect.update();
    this.frame++;
  }
  add_firework(x = null) {
    if (x === null) x = this.rand.randint(0, this.width);
    const color = this.use_random_colors ? randomColor(this.rand) : this.firework_color;
    const fw = new Firework(x, this.height, color, this.particle_count, this.rand,
      { gravity: this.gravity, launchSpeed: this.launchSpeed });
    if (this.pattern) fw.pattern = this.use_random_patterns ? new RandomPattern(this.rand) : this.pattern;  // after, as in Python
    this.fireworks.push(fw);
    return fw;
  }
  set_pattern(name) {
    this.patternName = name;
    this.pattern = this.use_random_patterns ? new RandomPattern(this.rand)
      : makePattern(name, { scale: this.pattern_scale, rotation: this.pattern_rotation, ...this.pattern_options }, this.rand);
  }
  set_pattern_scale(s) { this.pattern_scale = s; if (this.pattern && !this.use_random_patterns) this.pattern.scale = s; }
  set_pattern_rotation(r) {
    this.pattern_rotation = r; if (this.pattern && !this.use_random_patterns) this.pattern.rotation = r;
  }
  set_pattern_option(option, value) {
    this.pattern_options[option] = value;
    if (option === 'star_points' && this.patternName === 'Star' && this.pattern) this.pattern.num_points = value;
    if (option === 'spiral_arms' && this.patternName === 'Spiral' && this.pattern) this.pattern.arms = value;
    if (option === 'text' && this.patternName === 'Text') this.set_pattern('Text');
  }
  set_random_patterns(on) {
    this.use_random_patterns = on;
    if (on) this.pattern = new RandomPattern(this.rand);  // as the desktop: unticking keeps the current pattern
  }
  particleCount() { return this.fireworks.reduce((n, fw) => n + (fw.exploded ? fw.particles.length : 1), 0); }
}
