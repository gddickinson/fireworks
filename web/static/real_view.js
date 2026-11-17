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
import { FxLayers, SCENE_FX, SKY_FX, WEATHER, gustyWind } from './fw_fx.js';
import './fw_fx_all.js';
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
    this.fx = new FxLayers(); this.skyFx = new Set(opts.skyFx || []); this.windBase = 1.5;
    this.timeOfDay = opts.timeOfDay || 'night';
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
    this.scenery = buildScenery(this.bgName, W, H, (this.seed % 1000) + 7, { time: this.timeOfDay });
    this.sim.horizon = this.scenery.horizon; this.cam.set(W, H, this.sim.horizon);
    this.R.setScenery(this.scenery);
    if (!keep) this.R.clearTrails?.();
    if (!keep) this.setFx();
  }
  setWeather(name) { this.weatherName = name || 'None'; this.setFx(); }
  sceneNames() { return Object.keys(SCENERY_HORIZON); }
  weatherNames() { return [...new Set(['None', ...Object.keys(WEATHER), 'Rain', 'Snow', 'Fog', 'Lightning'])]; }
  setTimeOfDay(t) { this.timeOfDay = t; this.setBackground(this.bgName); }
  setSkyFx(keys) { this.skyFx = new Set(keys); this.setFx(); }
  // (Re)build the plug-in layers: animated scene objects, sky effects, then the weather on top.
  setFx() {
    const env = this.env(), list = [];
    if (SCENE_FX[this.bgName]) list.push(SCENE_FX[this.bgName](env));
    for (const k of this.skyFx) if (SKY_FX[k]) list.push(SKY_FX[k].make(env));
    if (WEATHER[this.weatherName]) list.push(WEATHER[this.weatherName].make(env));
    else if (this.weatherName !== 'None') list.push(classicWeather(this.weatherName, env));
    this.fx.set(list, env);
  }
  env() {
    return { sim: this.sim, cam: this.cam, cssW: this.cssW, cssH: this.cssH, k: this.cssW / Math.max(1, this.cam.W),
      lights: this.lightsNow || [], time: this.sim.time, wind: this.sim.wind, scenery: this.scenery, seed: this.seed,
      reduced: this.reduced, quality: this.quality };
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
    m.lift_time = this.liftTime === undefined ? 3 : this.liftTime;
  }
  launch(xFrac = null, type = null) {
    this.sync();
    return this.sim.launch(this.director.recipe(type), xFrac === null ? null : xFrac, xFrac === null ? null : 450, null, 0);
  }
  finale() { this.sync(); this.director.startFinale(this.sim); }
  // Message show (fw_message_show.js); returns its duration in seconds.
  messages(list, opener = 'off', finale = false) {
    this.sync();
    return this.director.queueMessages(this.sim, list, opener, finale, this.reduced);
  }
  on(fn) { this.listeners.push(fn); }
  step() {
    this.sync();
    this.director.step(this.sim);
    this.sim.step();
    if (this.sim.events.length) { this.atmos.onEvents(this.sim.events, this.sim); for (const f of this.listeners) f(this.sim.events, this); }
    this.sim.wind = gustyWind(this.windBase, this.sim.time, this.seed);   // one wind for shells, smoke, weather
    this.atmos.update(DT, this.sim.wind);
    this.fx.update(DT, this.env());
    this.show.frame = this.sim.frame;
  }
  frameData() {
    const cam = this.cam, t = this.sim.time, S = this.scenery;
    const n = buildParticles(this.sim, cam, this.parts, { flashes: !this.reduced, pxScale: cam.H / 900,
      fireflies: S.fireflies.length ? S.fireflies : null, time: t });
    const lights = this.atmos.screenLights(cam, 8), total = lights.reduce((a, L) => a + L.I, 0);
    this.lightsNow = lights;
    const env = this.env();
    this.fx.resize(env);
    const { sky, over: weather } = this.fx.render(env);
    this.expo = (this.expo ?? 1) * 0.9 + 0.1 / (1 + 0.06 * total);   // eye/camera adapting to a bright finale
    const amb = S.name === 'Cityscape' ? [0.018, 0.012, 0.01] : [0.006, 0.007, 0.011];
    return { parts: this.parts, n, puffs: this.atmos.screenPuffs(cam, amb), lights,
      flash: this.reduced ? 0 : Math.min(3, this.atmos.flash), time: t, persist: this.reduced ? 0.55 : 0.8,
      exposure: this.expo, bloom: this.bloom ?? 0.75, grain: this.capturing ? 0 : 0.022, weather, sky,
      ...this.cameraState(t) };  // no grain in exports (GIFs compress)
  }
  // Camera options: handheld sway (smooth, small, deterministic in time) and the long-exposure photo mode, where the
  // trails accumulate for the length of the exposure at a lower gain (a still like a tripod photo).
  cameraState(t) {
    const out = {};
    if (this.longExposure) Object.assign(out, { persist: 0.994, fwGain: 0.22, grain: 0 });
    if (this.sway && !this.reduced && !this.longExposure) {
      const a = 0.0016;
      out.cam = [a * (Math.sin(t * 0.9) + 0.6 * Math.sin(t * 2.3 + 1.1)), a * (Math.sin(t * 1.3 + 0.4) + 0.5 * Math.sin(t * 3.1)), 1.012];
    }
    return out;
  }
  // Take a long-exposure photo: `seconds` of the show build up into one frame; resolves when done (paused).
  photo(seconds = 6) {
    this.R.clearTrails?.(); this.longExposure = true; this.paused = false;
    return new Promise(res => {
      const t0 = this.sim.time, wait = () => {
        if (this.sim.time - t0 >= seconds) { this.paused = true; this.draw(); res(); }   // stays a photo until resumed
        else setTimeout(wait, 100);
      };
      wait();
    });
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

// The classic weather effects (fw_weather.js, the verified port) as an "over" plug-in, for names without a
// realistic version.
function classicWeather(name, env) {
  const w = makeWeather(name, env.cssW, env.cssH, pyRand(env.seed ^ 77));
  return w && { update: () => w.update(), drawOver: c => w.draw(c) };
}
