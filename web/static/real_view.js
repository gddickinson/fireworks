// The realistic display: the 3-D engine (fw_pyro/fw_shells/fw_director) drawn over lit scenery (fw_scenery) by the
// WebGL2 renderer, or the 2D-canvas fallback. Same interface as ShowView (show_view.js), so the control panel works
// with either: `show` is a classic Show used as the settings store (pattern, colours, sliders), read at each launch.
// Fixed 60 Hz simulation steps; the drawing resolution and particle budget adapt to keep the frame rate up.
import { animate } from './core.js';
import { Show } from './fw_engine.js';
import { DT, Sim } from './fw_pyro.js';
import { Director } from './fw_director.js';
import { Atmos, Camera, STRIDE, buildParticles } from './fw_atmos.js';
import { SCENERY_HORIZON, buildScenery } from './fw_scenery.js';
import { makeWeather } from './fw_weather.js';
import { pyRand } from './fw_rand.js';
import { prng } from './fw_noise.js';
import { GLRenderer } from './fw_render_gl.js';
import { Canvas2DRenderer } from './fw_render_2d.js';

const FRAME_MS = 1000 / 60;
export const reducedMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export class RealView {
  // opts: { seed, background, weather, label, onFrame, renderer: 'auto' | '2d', interactive }
  constructor(canvas, opts = {}) {
    this.canvas = canvas; this.opts = opts;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', opts.label || 'Animated realistic fireworks display');
    this.seed = opts.seed ?? Math.floor(Math.random() * 2 ** 32);
    this.reduced = reducedMotion();
    try { if (opts.renderer === '2d') throw new Error('2d asked'); this.R = new GLRenderer(canvas); }
    catch { this.R = new Canvas2DRenderer(canvas); }
    this.scale = 1; this.quality = 1; this.slow = 0; this.fast = 0;
    this.parts = new Float32Array(STRIDE * 40000);
    this.bgName = opts.background || 'Night Sky'; this.weatherName = opts.weather || 'None';
    this.wx = null; this.wxCanvas = document.createElement('canvas');
    this.paused = false; this.listeners = [];
    this.reset(this.seed);
    if (opts.interactive !== false) canvas.addEventListener('pointerdown', e => {
      const r = canvas.getBoundingClientRect();
      this.launch((e.clientX - r.left) / r.width * 2 - 1);
    });
    this.ro = new ResizeObserver(() => this.fit());
    this.ro.observe(canvas);
  }
  reset(seed = this.seed) {                                   // a fresh deterministic run (recording uses this)
    this.seed = seed;
    const rand = pyRand(seed), old = this.show;
    this.show = new Show(1, 1, { rand });
    if (old) for (const k of ['particle_count', 'firework_color', 'use_random_colors', 'pattern', 'patternName',
      'pattern_scale', 'pattern_rotation', 'pattern_options', 'use_random_patterns', 'gravity', 'launchSpeed', 'autoLaunch']) this.show[k] = old[k];
    this.sim = new Sim(rand, { aspect: 16 / 9, horizon: SCENERY_HORIZON[this.bgName] ?? 0.9 });
    this.director = new Director(rand);
    this.atmos = new Atmos(prng(seed ^ 0x5bd1e995));
    this.cam = new Camera(1, 1, this.sim.horizon);
    this.fit(true);
  }
  size() {
    const r = this.canvas.getBoundingClientRect();
    return { w: Math.max(1, Math.round(r.width)), h: Math.max(1, Math.round(r.height)) };
  }
  fit(force = false) {
    const { w, h } = this.size(), dpr = Math.min(window.devicePixelRatio || 1, 2) * this.scale;
    const W = Math.max(2, Math.round(w * dpr)), H = Math.max(2, Math.round(h * dpr));
    this.cssW = w; this.cssH = h;
    if (!force && W === this.canvas.width && H === this.canvas.height) return;
    this.canvas.width = W; this.canvas.height = H;
    this.R.resize(W, H);
    this.sim.aspect = W / H;
    this.cam.set(W, H, this.sim.horizon);
    this.setBackground(this.bgName, true);
    this.setWeather(this.weatherName);
    this.draw();
  }
  setBackground(name, keep = false) {
    this.bgName = name || 'None';
    const W = this.canvas.width, H = this.canvas.height;
    this.scenery = buildScenery(this.bgName, W, H, (this.seed % 1000) + 7);
    this.sim.horizon = this.scenery.horizon; this.cam.set(W, H, this.sim.horizon);
    this.R.setScenery(this.scenery);
    if (!keep) this.R.clearTrails?.();
  }
  setWeather(name) {
    this.weatherName = name || 'None';
    this.wxCanvas.width = this.cssW; this.wxCanvas.height = this.cssH;
    this.wx = makeWeather(this.weatherName, this.cssW, this.cssH, pyRand(this.seed ^ 77));
  }
  // Settings from the panel's Show (read every frame; they apply to new shells).
  sync() {
    const s = this.show, d = this.director, m = this.sim;
    d.color = s.use_random_colors ? null : s.firework_color;
    d.pattern = s.pattern || null; d.pattern_scale = s.pattern_scale;
    d.auto = s.autoLaunch;
    m.star_scale = (0.5 + s.particle_count / 100) * this.quality;
    m.gravity_scale = s.gravity / 0.1;
    m.height_scale = Math.min(1.3, Math.max(0.35, (s.launchSpeed / 10) ** 2));
    m.budget = Math.round(30000 * this.quality);
  }
  launch(xFrac = null, type = null) {
    this.sync();
    return this.sim.launch(this.director.recipe(type), xFrac === null ? null : xFrac, xFrac === null ? null : 450, null, 0);
  }
  finale() { this.sync(); this.director.startFinale(this.sim); }
  messages(list) { this.sync(); this.director.queueMessages(this.sim, list); }
  on(fn) { this.listeners.push(fn); }
  step() {
    this.sync();
    this.director.step(this.sim);
    this.sim.step();
    if (this.sim.events.length) { this.atmos.onEvents(this.sim.events, this.sim); for (const f of this.listeners) f(this.sim.events, this); }
    this.atmos.update(DT, this.sim.wind);
    if (this.wx) this.wx.update();
    this.show.frame = this.sim.frame;
  }
  frameData() {
    const cam = this.cam, t = this.sim.time, S = this.scenery;
    const n = buildParticles(this.sim, cam, this.parts, { flashes: !this.reduced, pxScale: cam.H / 900,
      fireflies: S.fireflies.length ? S.fireflies : null, time: t });
    let weather = null;
    if (this.wx) {
      const c = this.wxCanvas.getContext('2d'); c.clearRect(0, 0, this.wxCanvas.width, this.wxCanvas.height);
      this.wx.draw(c); weather = this.wxCanvas;
    }
    const lights = this.atmos.screenLights(cam, 8), total = lights.reduce((a, L) => a + L.I, 0);
    this.expo = (this.expo ?? 1) * 0.9 + 0.1 / (1 + 0.06 * total);   // eye/camera adapting to a bright finale
    const amb = S.name === 'Cityscape' ? [0.018, 0.012, 0.01] : [0.006, 0.007, 0.011];
    return { parts: this.parts, n, puffs: this.atmos.screenPuffs(cam, amb), lights,
      flash: this.reduced ? 0 : Math.min(3, this.atmos.flash), time: t, persist: this.reduced ? 0.55 : 0.8,
      exposure: this.expo, bloom: 0.75, grain: this.capturing ? 0 : 0.022, weather };  // no grain in exports (GIFs compress)
  }
  draw() { this.R.render(this.frameData()); this.lastN = this.parts && this.sim.stars.length; }
  adapt(ms) {                                                 // keep ~60 fps: drop resolution, then particles
    if (ms > 24) { this.slow++; this.fast = 0; } else if (ms < 15) { this.fast++; this.slow = 0; } else { this.slow = 0; this.fast = 0; }
    if (this.slow > 45) {
      this.slow = 0;
      if (this.scale > 0.55) { this.scale = Math.max(0.5, this.scale - 0.15); this.fit(true); }
      else this.quality = Math.max(0.35, this.quality - 0.15);
    } else if (this.fast > 240 && (this.scale < 1 || this.quality < 1)) {
      this.fast = 0;
      if (this.quality < 1) this.quality = Math.min(1, this.quality + 0.15);
      else { this.scale = Math.min(1, this.scale + 0.15); this.fit(true); }
    }
  }
  stats() {
    return { renderer: this.R.kind, scale: +this.scale.toFixed(2), quality: +this.quality.toFixed(2),
      stars: this.sim.stars.length, frameMs: +(this.ema || 0).toFixed(1), workMs: +(this.work || 0).toFixed(2) };
  }
  start() {
    let last = performance.now(), acc = 0;
    this.stop = animate(t => {
      const dt = t - last; last = t;
      this.ema = this.ema ? this.ema * 0.95 + dt * 0.05 : dt;
      if (this.paused || document.hidden) return;
      acc = Math.min(acc + dt, FRAME_MS * 4);
      let n = 0;
      const w0 = performance.now();
      while (acc >= FRAME_MS) { this.step(); acc -= FRAME_MS; n++; }
      if (n) { this.draw(); this.opts.onFrame?.(this); }
      const work = performance.now() - w0;                    // CPU time of simulation + draw calls this frame
      this.work = this.work ? this.work * 0.95 + work * 0.05 : work;
      this.adapt(dt);
      window.__fwStats = this.stats();
    });
    return this;
  }
  toPNG() { this.draw(); return this.canvas.toDataURL('image/png'); }
}
