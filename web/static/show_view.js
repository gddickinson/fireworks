// The display: port of FireworksCanvas.paintEvent / resizeEvent plus the 60 fps timer, on an HTML canvas.
// Paint order as in Python: background colour, background scene, weather, then rockets (4 px) and particles (2 px,
// alpha fading with remaining life). Click/tap launches a firework at that x (described in the README).
import { animate } from './core.js';
import { BACKGROUND_COLOR, CONFIG, Show } from './fw_engine.js';
import { makeBackground } from './fw_backgrounds.js';
import { makeWeather } from './fw_weather.js';
import { pyRand } from './fw_rand.js';

const FRAME_MS = Math.floor(1000 / CONFIG.FRAME_RATE);       // QTimer interval 1000 // FRAME_RATE = 16 ms

export function paint(ctx, show) {
  const [r, g, b] = BACKGROUND_COLOR;
  ctx.fillStyle = `rgb(${r},${g},${b})`; ctx.fillRect(0, 0, show.width, show.height);
  if (show.background) show.background.draw(ctx);
  if (show.weather_effect) show.weather_effect.draw(ctx);
  for (const fw of show.fireworks) {
    const [cr, cg, cb] = fw.color;
    if (!fw.exploded) {
      ctx.fillStyle = `rgb(${cr},${cg},${cb})`; ctx.fillRect(Math.trunc(fw.x) - 2, Math.trunc(fw.y) - 2, 4, 4);
    } else {
      for (const p of fw.particles) {
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.alpha() / 255})`;
        ctx.fillRect(Math.trunc(p.x) - 1, Math.trunc(p.y) - 1, 2, 2);
      }
    }
  }
}

export class ShowView {
  // opts: { seed, background, weather, label, onFrame }
  constructor(canvas, opts = {}) {
    this.canvas = canvas; this.opts = opts;
    this.ctx = canvas.getContext('2d');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', opts.label || 'Animated fireworks display');
    const { w, h } = this.size();
    this.show = new Show(w, h, { rand: pyRand(opts.seed) });
    this.bgName = 'None'; this.weatherName = 'None';
    this.setBackground(opts.background || 'None');
    this.setWeather(opts.weather || 'None');
    this.fit();
    this.paused = false;
    canvas.addEventListener('pointerdown', e => {
      const r = canvas.getBoundingClientRect();
      this.show.add_firework(Math.round(e.clientX - r.left));
    });
    this.ro = new ResizeObserver(() => this.fit());
    this.ro.observe(canvas);
  }
  size() {
    const r = this.canvas.getBoundingClientRect();
    return { w: Math.max(1, Math.round(r.width)), h: Math.max(1, Math.round(r.height)) };
  }
  fit() {                                                     // resizeEvent: new size, background rebuilt
    const { w, h } = this.size(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (this.canvas.width !== Math.round(w * dpr) || this.canvas.height !== Math.round(h * dpr)) {
      this.canvas.width = Math.round(w * dpr); this.canvas.height = Math.round(h * dpr);
    }
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (w !== this.show.width || h !== this.show.height) {
      this.show.width = w; this.show.height = h;
      if (this.show.background) this.setBackground(this.bgName);
    }
    this.draw();
  }
  setBackground(name) {
    this.bgName = name; this.show.background = makeBackground(name, this.show.width, this.show.height, this.show.rand);
  }
  setWeather(name) {
    this.weatherName = name; this.show.weather_effect = makeWeather(name, this.show.width, this.show.height, this.show.rand);
  }
  draw() { paint(this.ctx, this.show); }
  step() { this.show.update(); }
  start() {
    let last = performance.now(), acc = 0;
    this.stop = animate(t => {
      if (this.paused) { last = t; return; }
      acc = Math.min(acc + (t - last), FRAME_MS * 6); last = t;
      let n = 0;
      while (acc >= FRAME_MS) { this.step(); acc -= FRAME_MS; n++; }
      if (n) { this.draw(); if (this.opts.onFrame) this.opts.onFrame(this.show); }
    });
    return this;
  }
  toPNG() { return this.canvas.toDataURL('image/png'); }
}
