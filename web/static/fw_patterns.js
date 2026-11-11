// Port of models/patterns.py: the explosion shapes. get_points(x, y) returns [px, py] pairs around (x, y),
// rotated by `rotation` radians. RandomPattern draws its parameters from a pyRand (fw_rand.js) in Python's order.
import { COLS, GLYPHS, ROWS } from './fw_glyphs.js';

class Pattern {
  constructor(scale = 1.0, rotation = 0.0) { this.scale = scale; this.rotation = rotation; }
  _rotate(x, y, cx, cy) {
    const dx = x - cx, dy = y - cy, c = Math.cos(this.rotation), s = Math.sin(this.rotation);
    return [cx + (dx * c - dy * s), cy + (dx * s + dy * c)];
  }
}

export class CirclePattern extends Pattern {
  constructor(scale = 1.0, rotation = 0.0, num_points = 36) { super(scale, rotation); this.num_points = num_points; }
  get_points(x, y) {
    const pts = [];
    for (let i = 0; i < this.num_points; i++) {
      const a = 2 * Math.PI * i / this.num_points;
      pts.push(this._rotate(x + Math.cos(a) * (50 * this.scale), y + Math.sin(a) * (50 * this.scale), x, y));
    }
    return pts;
  }
}

export class HeartPattern extends Pattern {
  constructor(scale = 1.0, rotation = 0.0, num_points = 36) { super(scale, rotation); this.num_points = num_points; }
  get_points(x, y) {
    const pts = [], step = Math.floor(360 / this.num_points);
    for (let t = 0; t < 360; t += step) {
      const a = t * (Math.PI / 180);                         // math.radians
      const px = x + this.scale * (16 * Math.sin(a) ** 3);
      const py = y - this.scale * (13 * Math.cos(a) - 5 * Math.cos(2 * a) - 2 * Math.cos(3 * a) - Math.cos(4 * a));
      pts.push(this._rotate(px, py, x, y));
    }
    return pts;
  }
}

export class StarPattern extends Pattern {
  constructor(scale = 1.0, rotation = 0.0, points = 5, inner_radius = 0.4) {
    super(scale, rotation); this.num_points = points; this.inner_radius = inner_radius;
  }
  get_points(x, y) {
    const pts = [];
    for (let i = 0; i < this.num_points * 2; i++) {
      const a = Math.PI * i / this.num_points;
      const r = i % 2 === 0 ? (50 * this.scale) : (50 * this.scale * this.inner_radius);
      pts.push(this._rotate(x + Math.cos(a) * r, y + Math.sin(a) * r, x, y));
    }
    return pts;
  }
}

export class SpiralPattern extends Pattern {
  constructor(scale = 1.0, rotation = 0.0, arms = 3, rotations = 2.0) {
    super(scale, rotation); this.arms = arms; this.rotations = rotations;
  }
  get_points(x, y) {
    const pts = [], maxR = 50 * this.scale, steps = 50;
    for (let arm = 0; arm < this.arms; arm++) {
      const off = 2 * Math.PI * arm / this.arms;
      for (let i = 0; i < steps; i++) {
        const t = i / (steps - 1), a = t * 2 * Math.PI * this.rotations + off, r = t * maxR;
        pts.push(this._rotate(x + Math.cos(a) * r, y + Math.sin(a) * r, x, y));
      }
    }
    return pts;
  }
}

export class DoubleRingPattern extends Pattern {
  constructor(scale = 1.0, rotation = 0.0, inner_points = 12, outer_points = 24) {
    super(scale, rotation); this.inner_points = inner_points; this.outer_points = outer_points;
  }
  get_points(x, y) {
    const pts = [];
    for (const [n, r] of [[this.inner_points, 25], [this.outer_points, 50]]) {
      for (let i = 0; i < n; i++) {
        const a = 2 * Math.PI * i / n;
        pts.push(this._rotate(x + Math.cos(a) * (r * this.scale), y + Math.sin(a) * (r * this.scale), x, y));
      }
    }
    return pts;
  }
}

export class RandomPattern extends Pattern {
  constructor(rand) {
    const scale = rand.uniform(0.5, 1.5), rotation = rand.uniform(0, 2 * Math.PI);
    super(scale, rotation);
    this.patterns = [
      new CirclePattern(scale, rotation, rand.randint(24, 48)),
      new HeartPattern(scale, rotation, rand.randint(24, 48)),
      new StarPattern(scale, rotation, rand.randint(4, 8), rand.uniform(0.3, 0.6)),
      new SpiralPattern(scale, rotation, rand.randint(2, 5), rand.uniform(1.5, 3.0)),
      new DoubleRingPattern(scale, rotation, rand.randint(8, 16), rand.randint(16, 32)),
    ];
    this.selected_pattern = rand.choice(this.patterns);
  }
  get_points(x, y) { return this.selected_pattern.get_points(x, y); }
}

// Text as 5 x 7 dot-matrix glyphs (fw_glyphs.js, generated from models/glyphs.py: A-Z, 0-9), centred on the burst.
export class TextPattern extends Pattern {
  constructor(text, scale = 1.0, spacing = 30.0) {
    super(scale); this.text = text; this.spacing = spacing;
    this.dot_pitch = 5 * scale; this.char_width = spacing * scale; this.total_width = text.length * this.char_width;
  }
  get_points(x, y) {
    const pts = [], start = x - this.total_width / 2;
    [...this.text].forEach((ch, i) => pts.push(...this._char(ch, start + (i + 0.5) * this.char_width, y)));
    return pts;
  }
  _char(ch, x, y) {
    const rows = GLYPHS[ch.toUpperCase()] || [], cx = (COLS - 1) / 2, cy = (ROWS - 1) / 2, pts = [];
    rows.forEach((line, r) => [...line].forEach((cell, c) => {
      if (cell === '#') pts.push([x + (c - cx) * this.dot_pitch, y + (r - cy) * this.dot_pitch]);
    }));
    return pts;
  }
}

// Build a pattern the way FireworksCanvas.set_pattern does (name from the Pattern combo box).
export function makePattern(name, { scale = 1.0, rotation = 0.0, star_points = 5, spiral_arms = 3, text = '' } = {}, rand) {
  switch (name) {
    case 'Random': return new RandomPattern(rand);
    case 'Circle': return new CirclePattern(scale, rotation);
    case 'Heart': return new HeartPattern(scale, rotation);
    case 'Star': return new StarPattern(scale, rotation, star_points);
    case 'Spiral': return new SpiralPattern(scale, rotation, spiral_arms);
    case 'Double Ring': return new DoubleRingPattern(scale, rotation);
    case 'Text': return new TextPattern(text, scale);
    default: return null;
  }
}

export const PATTERN_CLASSES = {
  Circle: (k = {}) => new CirclePattern(k.scale, k.rotation, k.num_points),
  Heart: (k = {}) => new HeartPattern(k.scale, k.rotation, k.num_points),
  Star: (k = {}) => new StarPattern(k.scale, k.rotation, k.points, k.inner_radius),
  Spiral: (k = {}) => new SpiralPattern(k.scale, k.rotation, k.arms, k.rotations),
  'Double Ring': (k = {}) => new DoubleRingPattern(k.scale, k.rotation, k.inner_points, k.outer_points),
  Text: (k = {}) => new TextPattern(k.text, k.scale, k.spacing),
};
