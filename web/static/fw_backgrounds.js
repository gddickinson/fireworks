// Port of effects/backgrounds.py and effects/mountains.py: the five scenes (generation and Qt painting -> canvas).
// Scene generation draws from a pyRand in the Python order (checked by fw_scenes.test.mjs).
const css = (r, g, b, a = 255) => `rgba(${r},${g},${b},${a / 255})`;

function grad(ctx, y0, y1, stops) {
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  for (const [t, c] of stops) g.addColorStop(t, css(...c));
  return g;
}
function stars(ctx, list) {                                   // 1 px points, alpha int(255 * brightness)
  for (const [x, y, b] of list) { ctx.fillStyle = css(255, 255, 255, Math.trunc(255 * b)); ctx.fillRect(Math.trunc(x), Math.trunc(y), 1, 1); }
}
function genStars(rand, w, h, top) {                          // _generate_stars of Beach/Forest/Mountains
  const out = [], n = Math.trunc((w * h) / 2000);
  for (let i = 0; i < n; i++) out.push([rand.uniform(0, w), rand.uniform(0, h * top), rand.uniform(0.3, 1.0)]);
  return out;
}

export class NightSkyBackground {
  constructor(w, h, rand) {
    this.width = w; this.height = h;
    const pos = []; for (let i = 0; i < 200; i++) pos.push([rand.uniform(0, w), rand.uniform(0, h * 0.7)]);
    const br = []; for (let i = 0; i < 200; i++) br.push(rand.uniform(0.3, 1.0));
    this.stars = pos.map((p, i) => [p[0], p[1], br[i]]);
  }
  draw(ctx) {
    ctx.fillStyle = grad(ctx, 0, this.height, [[0, [0, 0, 40]], [1, [20, 20, 60]]]); ctx.fillRect(0, 0, this.width, this.height);
    stars(ctx, this.stars);
  }
}

export class CityscapeBackground {
  constructor(w, h, rand) {
    this.width = w; this.height = h; this.buildings = []; this.windows = [];
    for (let x = 0; x < w;) {
      const bw = rand.randint(40, 100), bh = rand.randint(100, 300);
      this.buildings.push([x, h - bh, bw, bh]); x += bw;
    }
    for (const [x, y, bw, bh] of this.buildings) {
      for (let f = 0; f < Math.trunc(bh / 20); f++) {
        for (let k = 0; k < Math.trunc(bw / 15); k++) {
          if (rand.random() < 0.7) this.windows.push([x + k * 15 + 5, y + f * 20 + 5, 10, 15]);
        }
      }
    }
  }
  draw(ctx) {
    ctx.fillStyle = grad(ctx, 0, this.height, [[0, [0, 0, 40]], [1, [20, 20, 60]]]); ctx.fillRect(0, 0, this.width, this.height);
    ctx.fillStyle = css(30, 30, 40); for (const b of this.buildings) ctx.fillRect(...b);
    ctx.fillStyle = css(255, 255, 150, 100); for (const w of this.windows) ctx.fillRect(...w);
  }
}

// Python draws each range with a gradient from painter.pen().color() (whatever pen the stars/snow left: white,
// semi-transparent) and drops the colour passed to _generate_mountain_range. web: the passed colours are used.
const RANGE_SPECS = [[5, [0.3, 0.4], [40, 40, 60]], [4, [0.4, 0.5], [50, 50, 70]], [3, [0.45, 0.6], [60, 60, 80]]];
export class MountainsBackground {
  constructor(w, h, rand) {
    this.width = w; this.height = h; this.rand = rand;
    this.mountains = RANGE_SPECS.map(([n, hr]) => this.range(n, hr));
    this.stars = genStars(rand, w, h, 0.7);
  }
  range(peaks, [lo, hi]) {
    const R = this.rand, pts = [[0, this.height]], seg = this.width / (peaks - 1);
    for (let i = 0; i < peaks; i++) {
      const x = i * seg, hf = R.uniform(lo, hi);
      pts.push([x, this.height * (1 - hf)]);
      if (i < peaks - 1) {
        const sub = R.randint(2, 4);
        for (let j = 0; j < sub; j++) pts.push([x + seg * (j + 1) / (sub + 1), this.height * (1 - hf * R.uniform(0.7, 0.9))]);
      }
    }
    pts.push([this.width, this.height]);
    return pts.map((p, i) => [p, i]).sort((a, b) => a[0][0] - b[0][0] || a[1] - b[1]).map(a => a[0]);  // stable, by x
  }
  draw(ctx) {
    ctx.fillStyle = grad(ctx, 0, this.height, [[0, [0, 0, 40]], [0.5, [20, 20, 60]], [1, [40, 40, 80]]]);
    ctx.fillRect(0, 0, this.width, this.height);
    stars(ctx, this.stars);
    this.mountains.forEach((rng, k) => {
      const c = RANGE_SPECS[k][2];
      ctx.beginPath(); ctx.moveTo(...rng[0]); for (const p of rng.slice(1)) ctx.lineTo(...p);
      ctx.fillStyle = grad(ctx, 0, this.height, [[0, c.map(v => Math.min(255, Math.round(v * 1.2)))], [1, c.map(v => Math.round(v / 1.2))]]);
      ctx.fill();
      ctx.strokeStyle = css(255, 255, 255, 180); ctx.lineWidth = 2;
      for (let i = 1; i < rng.length - 1; i++) {
        const [x, y] = rng[i];
        if (y < rng[i - 1][1] && y < rng[i + 1][1]) {         // a peak: snow cap (width re-drawn every frame, as in Python)
          const sw = this.rand.uniform(20, 40);
          ctx.beginPath(); ctx.moveTo(x - sw / 2, y); ctx.quadraticCurveTo(x, y - sw / 4, x + sw / 2, y); ctx.stroke();
        }
      }
    });
  }
}

export class BeachBackground {
  constructor(w, h, rand) {
    this.width = w; this.height = h; this.time = 0;
    this.stars = genStars(rand, w, h, 0.6);
    this.waves = [];
    for (let i = 0; i < 5; i++) {
      const wave = []; for (let j = 0; j <= 20; j++) wave.push([(j / 20) * w, h * 0.7 + i * (h * 0.1)]);
      this.waves.push(wave);
    }
    this.palm_trees = [];
    const n = rand.randint(3, 5);
    for (let i = 0; i < n; i++) this.palm_trees.push([rand.uniform(0, w), h * 0.7, rand.uniform(0.8, 1.2)]);
  }
  draw(ctx) {
    const W = this.width, H = this.height;
    ctx.fillStyle = grad(ctx, 0, H * 0.7, [[0, [0, 0, 40]], [0.5, [20, 20, 80]], [1, [40, 40, 100]]]); ctx.fillRect(0, 0, W, H * 0.7);
    stars(ctx, this.stars);
    ctx.fillStyle = grad(ctx, H * 0.7, H, [[0, [0, 50, 100]], [1, [0, 100, 150]]]); ctx.fillRect(0, H * 0.7, W, H * 0.3);
    ctx.strokeStyle = css(200, 200, 255, 100); ctx.lineWidth = 2;
    this.time += 0.1;
    for (const wave of this.waves) {
      ctx.beginPath(); ctx.moveTo(...wave[0]);
      for (const [x, y] of wave.slice(1)) ctx.lineTo(x, y + Math.sin(x / 100 + this.time) * 5);
      ctx.stroke();
    }
    ctx.beginPath(); ctx.moveTo(0, H); ctx.lineTo(0, H * 0.75); ctx.quadraticCurveTo(W / 2, H * 0.68, W, H * 0.75);
    ctx.lineTo(W, H); ctx.fillStyle = css(255, 220, 170); ctx.fill();
    for (const [x, y, s] of this.palm_trees) this.palm(ctx, x, y, s);
  }
  palm(ctx, x, y, size) {
    const th = 100 * size;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.quadraticCurveTo(x - 10, y - th / 2, x + 20, y - th);
    ctx.strokeStyle = css(110, 80, 50); ctx.lineWidth = 15 * size; ctx.stroke();
    ctx.strokeStyle = css(0, 100, 0); ctx.lineWidth = 2; ctx.fillStyle = css(0, 120, 0);
    for (let i = 0; i < 5; i++) {
      const a = Math.PI / 6 + i * Math.PI / 4;
      ctx.beginPath(); ctx.moveTo(x + 20, y - th);
      ctx.quadraticCurveTo(x + 20 + Math.cos(a) * 40 * size, y - th + Math.sin(a) * 20 * size,
        x + 20 + Math.cos(a) * 80 * size, y - th + Math.sin(a) * 80 * size);
      ctx.fill(); ctx.stroke();
    }
  }
}

export class ForestBackground {
  constructor(w, h, rand) {
    this.width = w; this.height = h; this.time = 0;
    this.stars = genStars(rand, w, h, 0.5);
    const trees = [], count = Math.trunc(w / 50);
    for (let layer = 0; layer < 3; layer++) {
      const baseY = h * (0.6 + layer * 0.1);
      for (let i = 0; i < count - layer * 5; i++) {
        trees.push([rand.uniform(0, w), baseY, rand.uniform(0.8, 1.2) * (1 - layer * 0.2), rand.randint(0, 2)]);
      }
    }
    this.trees = trees.map((t, i) => [t, i]).sort((a, b) => a[0][1] - b[0][1] || a[1] - b[1]).map(a => a[0]);
    this.fireflies = [];
    for (let i = 0; i < Math.trunc(w / 100); i++) {
      this.fireflies.push([rand.uniform(0, w), rand.uniform(h * 0.5, h * 0.8), rand.uniform(0, 2 * Math.PI)]);
    }
  }
  draw(ctx) {
    const W = this.width, H = this.height;
    ctx.fillStyle = grad(ctx, 0, H, [[0, [0, 0, 40]], [0.5, [10, 10, 50]], [1, [20, 30, 60]]]); ctx.fillRect(0, 0, W, H);
    stars(ctx, this.stars);
    ctx.fillStyle = grad(ctx, H * 0.6, H, [[0, [20, 40, 20]], [1, [10, 30, 10]]]); ctx.fillRect(0, H * 0.6, W, H * 0.4);
    for (const [x, y, s, type] of this.trees) [this.pine, this.rounded, this.tall][type].call(this, ctx, x, y, s);
    this.time += 0.1;
    for (const [x, y, ph] of this.fireflies) {
      const b = (Math.sin(this.time + ph) + 1) / 2;
      if (b > 0.7) { ctx.fillStyle = css(255, 255, 100, Math.trunc(255 * b)); ctx.fillRect(Math.trunc(x) - 1, Math.trunc(y) - 1, 2, 2); }
    }
  }
  trunk(ctx, x, y, h, w) {
    ctx.strokeStyle = css(60, 40, 20); ctx.lineWidth = w;
    ctx.beginPath(); ctx.moveTo(Math.trunc(x), Math.trunc(y)); ctx.lineTo(Math.trunc(x), Math.trunc(y - h)); ctx.stroke();
  }
  pine(ctx, x, y, size) {
    const th = 40 * size, tw = 60 * size, tH = 100 * size;
    this.trunk(ctx, x, y, th, 4);
    ctx.fillStyle = css(20, 50, 20);
    for (let i = 0; i < 3; i++) {
      const sh = tH * (0.4 + i * 0.2), sw = tw * (0.4 + i * 0.3), sy = y - th - (tH * i / 3);
      ctx.beginPath(); ctx.moveTo(x, sy - sh); ctx.lineTo(x - sw / 2, sy); ctx.lineTo(x + sw / 2, sy); ctx.fill();
    }
  }
  rounded(ctx, x, y, size) {
    const th = 30 * size, r = 35 * size;
    this.trunk(ctx, x, y, th, 4);
    ctx.fillStyle = css(30, 60, 30); ctx.beginPath(); ctx.ellipse(x, y - th - r, r, r, 0, 0, 2 * Math.PI); ctx.fill();
  }
  tall(ctx, x, y, size) {
    const th = 80 * size, cw = 30 * size, ch = 100 * size, top = y - th - ch;
    this.trunk(ctx, x, y, th, 3);
    ctx.fillStyle = css(25, 55, 25); ctx.beginPath(); ctx.moveTo(x, top);
    ctx.quadraticCurveTo(x - cw, y - th - ch / 2, x - cw / 2, y - th);
    ctx.quadraticCurveTo(x, y - th - ch / 4, x + cw / 2, y - th);
    ctx.quadraticCurveTo(x + cw, y - th - ch / 2, x, top); ctx.fill();
    ctx.strokeStyle = css(35, 65, 35); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, top);
    ctx.quadraticCurveTo(x - cw * 0.7, y - th - ch / 2, x, y - th - ch / 4); ctx.stroke();
  }
}

export const BACKGROUNDS = { 'Night Sky': NightSkyBackground, Cityscape: CityscapeBackground,
  Mountains: MountainsBackground, Beach: BeachBackground, Forest: ForestBackground };

// FireworksCanvas.set_background (None or an unknown name clears it).
export function makeBackground(name, w, h, rand) {
  const cls = BACKGROUNDS[name];
  return cls ? new cls(w, h, rand) : null;
}
