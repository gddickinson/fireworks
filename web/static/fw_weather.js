// Port of effects/weather.py: rain, snow, fog and lightning (state, update and Qt painting -> canvas 2D).
// Random numbers come from a pyRand (fw_rand.js) in the same order as the Python `random` calls.
const RAD = Math.PI / 180;                                    // math.radians

class WeatherParticle {
  constructor(x, y, speed, angle) { this.x = x; this.y = y; this.speed = speed; this.angle = angle; this.active = true; }
}

class WeatherEffect {
  constructor(width, height, rand) { this.width = width; this.height = height; this.rand = rand; this.particles = []; }
  update() {}
  draw() {}
  init_particles() {}
  // Rescale positions; top up (never beyond the previous count) with new particles if some fell outside.
  resize(width, height) {
    const ow = this.width, oh = this.height;
    this.width = width; this.height = height;
    const old = this.particles; this.particles = [];
    for (const p of old) {
      p.x = (p.x / ow) * width; p.y = (p.y / oh) * height;
      if (p.x >= 0 && p.x <= width && p.y >= 0 && p.y <= height) this.particles.push(p);
    }
    if (this.particles.length < old.length) { this.init_particles(); this.particles.length = old.length; }
  }
}

export class RainEffect extends WeatherEffect {
  constructor(width, height, rand, intensity = 1.0) {
    super(width, height, rand); this.intensity = intensity; this.droplet_count = Math.trunc(100 * intensity);
    this.init_particles();
  }
  init_particles() {
    for (let i = 0; i < this.droplet_count; i++) {
      const x = this.rand.uniform(0, this.width), y = this.rand.uniform(0, this.height);
      this.particles.push(new WeatherParticle(x, y, this.rand.uniform(10, 15), Math.PI * 0.25));
    }
  }
  update() {
    for (const p of this.particles) {
      if (!p.active) continue;
      p.x -= p.speed * Math.cos(p.angle); p.y += p.speed * Math.sin(p.angle);
      if (p.y > this.height || p.x < 0) { p.x = this.rand.uniform(0, this.width); p.y = 0; }
    }
  }
  draw(ctx) {
    ctx.strokeStyle = 'rgba(200,200,255,0.588)'; ctx.lineWidth = 1; ctx.beginPath();
    for (const p of this.particles) {
      const x0 = Math.trunc(p.x), y0 = Math.trunc(p.y);
      ctx.moveTo(x0 + 0.5, y0 + 0.5);
      ctx.lineTo(Math.trunc(p.x - 5 * Math.cos(p.angle)) + 0.5, Math.trunc(p.y + 5 * Math.sin(p.angle)) + 0.5);
    }
    ctx.stroke();
  }
}

export class SnowEffect extends WeatherEffect {
  constructor(width, height, rand, intensity = 1.0) {
    super(width, height, rand); this.intensity = intensity; this.flake_count = Math.trunc(50 * intensity);
    this.init_particles(); this.wind_offset = 0; this.wind_speed = 0.1;
  }
  init_particles() {
    for (let i = 0; i < this.flake_count; i++) {
      const x = this.rand.uniform(0, this.width), y = this.rand.uniform(0, this.height);
      this.particles.push(new WeatherParticle(x, y, this.rand.uniform(1, 3), Math.PI / 2));
    }
  }
  update() {
    this.wind_offset += this.wind_speed;
    for (const p of this.particles) {
      if (!p.active) continue;
      p.x += Math.sin(p.y * 0.05 + this.wind_offset) * 0.5; p.y += p.speed;
      if (p.y > this.height) { p.x = this.rand.uniform(0, this.width); p.y = 0; }
    }
  }
  draw(ctx) {
    ctx.fillStyle = 'rgba(255,255,255,0.784)';
    for (const p of this.particles) ctx.fillRect(Math.trunc(p.x) - 0.5, Math.trunc(p.y) - 0.5, 2, 2);
  }
}

class FogLayer {
  constructor(x, y, width, height, rand) {
    this.x = x; this.y = y; this.width = width; this.height = height;
    this.velocity = rand.uniform(-0.5, 0.5); this.opacity = rand.uniform(0.2, 0.6);
    this.control_points = [];
    for (let i = 0; i < 5; i++) {
      const px = this.x + (i * this.width / 4);
      this.control_points.push([px, this.y + rand.uniform(-this.height / 4, this.height / 4)]);
    }
  }
  update(width) {
    this.x += this.velocity;
    let shift = this.velocity;                                // the control points jump with the layer
    if (this.velocity > 0 && this.x > width) { shift += -this.width - this.x; this.x = -this.width; }
    else if (this.velocity < 0 && this.x + this.width < 0) { shift += width - this.x; this.x = width; }
    this.control_points = this.control_points.map(([x, y]) => [x + shift, y]);
  }
}

export class FogEffect extends WeatherEffect {
  constructor(width, height, rand) {
    super(width, height, rand); this.fog_layers = []; this.time = 0;
    const lh = this.height / 5;
    for (let i = 0; i < 5; i++) {
      const x = rand.uniform(-this.width / 2, 0);
      this.fog_layers.push(new FogLayer(x, i * lh, this.width * 1.5, lh, rand));
    }
  }
  update() { this.time += 0.01; for (const L of this.fog_layers) L.update(this.width); }
  resize(width, height) {
    const sx = width / this.width, sy = height / this.height;
    super.resize(width, height);
    for (const L of this.fog_layers) {
      L.width *= sx; L.height *= sy; L.x *= sx; L.y *= sy;
      L.control_points = L.control_points.map(([x, y]) => [x * sx, y * sy]);
    }
    this.width = width; this.height = height;
  }
  draw(ctx) {
    for (const L of this.fog_layers) {
      ctx.beginPath(); ctx.moveTo(L.x, L.y + L.height / 2);
      const cp = L.control_points;
      for (let i = 0; i < cp.length - 1; i++) {
        const y1 = cp[i][1] + Math.sin(this.time + i) * 5, y2 = cp[i + 1][1] + Math.sin(this.time + i + 1) * 5;
        ctx.quadraticCurveTo((cp[i][0] + cp[i + 1][0]) / 2, y1 + this.rand.uniform(-10, 10), cp[i + 1][0], y2);
      }
      ctx.lineTo(L.x + L.width, L.y + L.height); ctx.lineTo(L.x, L.y + L.height); ctx.closePath();
      const g = ctx.createLinearGradient(L.x, L.y, L.x, L.y + L.height), a = Math.trunc(255 * L.opacity) / 255;
      g.addColorStop(0, 'rgba(200,200,200,0)'); g.addColorStop(0.2, `rgba(200,200,200,${a})`);
      g.addColorStop(0.8, `rgba(200,200,200,${a})`); g.addColorStop(1, 'rgba(200,200,200,0)');
      ctx.fillStyle = g; ctx.fill();
    }
  }
}

export class LightningBolt {
  constructor(sx, sy, ex, ey, rand) {
    this.start = [sx, sy]; this.end = [ex, ey]; this.segments = []; this.branches = []; this.rand = rand;
    this.lifetime = rand.randint(3, 6); this.current_life = this.lifetime;
    this.generate_path();
  }
  generate_path() {
    const R = this.rand, target = this.end;
    this.segments = [];
    let cur = this.start, guard = 0;
    while (Math.hypot(cur[0] - target[0], cur[1] - target[1]) > 10 && guard++ < 100000) {
      let dx = target[0] - cur[0], dy = target[1] - cur[1];
      const length = Math.sqrt(dx * dx + dy * dy);
      dx /= length; dy /= length;
      const step = R.uniform(20, 50), dev = R.uniform(-30, 30);
      const angle = Math.atan2(dy, dx) + dev * RAD;
      const np = [cur[0] + Math.cos(angle) * step, cur[1] + Math.sin(angle) * step];
      this.segments.push([cur, np]); cur = np;
      if (R.random() < 0.2) {
        const bl = length * R.uniform(0.3, 0.7), ba = angle + R.uniform(-45, 45) * RAD;
        this.branches.push(new LightningBolt(cur[0], cur[1], cur[0] + Math.cos(ba) * bl, cur[1] + Math.sin(ba) * bl, R));
      }
    }
    this.segments.push([cur, this.end]);
  }
}

export class LightningEffect extends WeatherEffect {
  constructor(width, height, rand) {
    super(width, height, rand); this.active_bolts = []; this.flash_intensity = 0.0; this.time_since_last = 0;
    this.next_strike = rand.uniform(50, 200);
  }
  update() {
    this.time_since_last += 1;
    for (const b of [...this.active_bolts]) {
      b.current_life -= 1;
      if (b.current_life <= 0) this.active_bolts.splice(this.active_bolts.indexOf(b), 1);
    }
    if (this.time_since_last >= this.next_strike) {
      this.create_lightning(); this.time_since_last = 0; this.next_strike = this.rand.uniform(50, 200);
    }
    if (this.flash_intensity > 0) this.flash_intensity *= 0.9;
  }
  create_lightning() {
    const sx = this.rand.uniform(0, this.width), ex = sx + this.rand.uniform(-200, 200);
    const ey = this.rand.uniform(this.height * 0.5, this.height * 0.8);
    this.active_bolts.push(new LightningBolt(sx, 0, ex, ey, this.rand));
    this.flash_intensity = 1.0;
  }
  draw(ctx) {
    if (this.flash_intensity > 0) {
      ctx.fillStyle = `rgba(255,255,255,${Math.trunc(60 * this.flash_intensity) / 255})`;
      ctx.fillRect(0, 0, this.width, this.height);
    }
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (const b of this.active_bolts) this.drawBolt(ctx, b);
    ctx.lineCap = 'butt';
  }
  drawBolt(ctx, b) {
    const f = b.current_life / b.lifetime, op = Math.trunc(f * 255) / 255, th = 3 * f;
    for (const [s, e] of b.segments) {
      ctx.beginPath(); ctx.moveTo(Math.trunc(s[0]), Math.trunc(s[1])); ctx.lineTo(Math.trunc(e[0]), Math.trunc(e[1]));
      ctx.strokeStyle = `rgba(255,255,255,${op})`; ctx.lineWidth = Math.max(th, 0.5); ctx.stroke();
      ctx.strokeStyle = `rgba(200,225,255,${Math.trunc(f * 255 * 0.5) / 255})`; ctx.lineWidth = Math.max(th * 2, 0.5);
      ctx.stroke();
    }
    for (const br of b.branches) this.drawBolt(ctx, br);
  }
}

// FireworksCanvas.set_weather: build the effect, then resize() it to the canvas.
export function makeWeather(name, width, height, rand) {
  const cls = { Rain: RainEffect, Snow: SnowEffect, Fog: FogEffect, Lightning: LightningEffect }[name];
  if (!cls) return null;
  const eff = new cls(width, height, rand);
  eff.resize(width, height);
  return eff;
}
