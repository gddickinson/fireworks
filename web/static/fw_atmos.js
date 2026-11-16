// What the realistic renderers draw besides the scenery, in screen pixels: the camera projection, the particle list
// (position, size, HDR colour per star), burst lights (that light the scene, the sky haze and the smoke) and smoke
// puffs left by every burst and launch. Shared by the WebGL renderer (fw_render_gl.js) and the 2D fallback.
import { FOCAL } from './fw_pyro.js';
import { starRGB } from './fw_palette.js';

export const STRIDE = 7;                                     // x, y, size, r, g, b, a(core weight)

export class Camera {
  constructor(W, H, horizon) { this.set(W, H, horizon); }
  set(W, H, horizon) { this.W = W; this.H = H; this.F = FOCAL * H; this.hz = horizon * H; }
  sx(x, z) { return this.W / 2 + this.F * x / z; }
  sy(y, z) { return this.hz - this.F * y / z; }
}

const C = [0, 0, 0, 0];
// Fill buf with the visible stars; returns the count. haze: atmospheric extinction per metre of distance.
export function buildParticles(sim, cam, buf, { flashes = true, pxScale = 1, fireflies = null, time = 0 } = {}) {
  let n = 0;
  const max = buf.length / STRIDE, k = 1 / 255, F = cam.F, W = cam.W, H = cam.H;
  for (const s of sim.stars) {
    if (n >= max) break;
    starRGB(s, C, flashes);
    const I = C[3];
    if (I <= 0.004) continue;
    const z = s.z, x = W / 2 + F * s.x / z, y = cam.hz - F * s.y / z;
    if (x < -40 || x > W + 40 || y < -40 || y > H + 40) continue;
    const ext = Math.exp(-(z - 300) / 2600) * 1.6 * I * k;
    const core = Math.max(1.1 * pxScale, F * 0.42 * s.size / z);
    const o = n * STRIDE;
    buf[o] = x; buf[o + 1] = y; buf[o + 2] = core;
    buf[o + 3] = C[0] * ext; buf[o + 4] = C[1] * ext; buf[o + 5] = C[2] * ext;
    buf[o + 6] = s.kind === 'spark' ? 0.6 : 1;
    n++;
  }
  if (fireflies) for (const [fx, fy, ph, sp] of fireflies) {
    if (n >= max) break;
    const b = Math.max(0, Math.sin(time * sp * 1.7 + ph)) ** 8;
    if (b < 0.02) continue;
    const o = n * STRIDE;
    buf[o] = fx * W + Math.sin(time * 0.3 + ph) * 6; buf[o + 1] = fy * H + Math.cos(time * 0.4 + ph) * 4;
    buf[o + 2] = 1.2 * pxScale; buf[o + 3] = 0.5 * b; buf[o + 4] = 0.7 * b; buf[o + 5] = 0.15 * b; buf[o + 6] = 1;
    n++;
  }
  return n;
}

// Lights and smoke, driven by the sim's events.
export class Atmos {
  constructor(rand = Math.random) {
    this.rand = rand; this.lights = []; this.puffs = []; this.maxPuffs = 220; this.flash = 0;
  }
  clear() { this.lights = []; this.puffs = []; }
  onEvents(events, sim) {
    const R = this.rand;
    for (const e of events) {
      if (e[0] === 'burst') {
        const [, x, y, z, col, strength] = e;
        this.lights.push({ x, y, z, col, s: strength, t: 0 });
        const n = Math.round(5 + 5 * strength);
        for (let i = 0; i < n; i++) this.puff(x + (R() - 0.5) * 50, y + (R() - 0.5) * 40, z + (R() - 0.5) * 30, 7 + R() * 8, 0.1);
      } else if (e[0] === 'launch') {
        const [, x, z] = e;
        this.lights.push({ x, y: 2, z, col: [255, 170, 90], s: 0.35, t: 0, launch: true });
        for (let i = 0; i < 3; i++) this.puff(x + (R() - 0.5) * 6, 2 + R() * 6, z, 4 + R() * 3, 0.12);
      } else if (e[0] === 'crackle' && R() < 0.2) {
        this.lights.push({ x: e[1], y: e[2], z: e[3], col: [255, 235, 200], s: 0.15, t: 0 });
      }
    }
    if (this.puffs.length > this.maxPuffs) this.puffs.splice(0, this.puffs.length - this.maxPuffs);
  }
  puff(x, y, z, r, a) { this.puffs.push({ x, y, z, r, a, a0: a, age: 0, rot: this.rand() * 6.28, lit: [0, 0, 0] }); }
  // Intensity of a light now: a sharp flash plus the glow of the burning stars.
  static intensity(L) {
    if (L.launch) return L.s * Math.exp(-L.t / 0.6);
    return L.s * (2.4 * Math.exp(-L.t / 0.09) + 0.45 * Math.exp(-L.t / 1.1));
  }
  update(dt, wind) {
    for (const L of this.lights) L.t += dt;
    this.lights = this.lights.filter(L => L.t < 4);
    for (const p of this.puffs) {
      p.age += dt; p.x += wind * dt; p.y += 0.35 * dt; p.r += (1.6 / (1 + p.age * 0.15)) * dt;
      p.a = p.a0 * Math.exp(-p.age / 22) * Math.min(1, p.age * 3);
    }
    this.puffs = this.puffs.filter(p => p.a > 0.004);
    let f = 0;
    for (const L of this.lights) if (!L.launch) f += L.s * Math.exp(-L.t / 0.09);
    this.flash = f;
  }
  // The strongest n lights in screen space: [{x, y, r (px), rgb (HDR)}].
  screenLights(cam, n = 8) {
    const out = [];
    for (const L of this.lights) {
      const I = Atmos.intensity(L);
      if (I < 0.01) continue;
      out.push({ x: cam.sx(L.x, L.z), y: cam.sy(L.y, L.z), r: cam.F * 140 / L.z, I, col: L.col });
    }
    out.sort((a, b) => b.I - a.I);
    return out.slice(0, n);
  }
  // Smoke colour: dim ambient plus the light falling on each puff; returns [{x, y, r, rgb, a, rot}] in px.
  screenPuffs(cam, ambient) {
    const lights = this.screenLights(cam, 8), out = [];
    for (const p of this.puffs) {
      const x = cam.sx(p.x, p.z), y = cam.sy(p.y, p.z), r = cam.F * p.r / p.z;
      let lr = ambient[0], lg = ambient[1], lb = ambient[2];
      for (const L of lights) {
        const dx = (L.x - x) / (L.r * 0.8), dy = (L.y - y) / (L.r * 0.8), q = 1 + dx * dx + dy * dy, f = 0.18 * L.I / (q * q) / 255;
        lr += L.col[0] * f; lg += L.col[1] * f; lb += L.col[2] * f;
      }
      out.push({ x, y, r, rgb: [lr, lg, lb], a: p.a, rot: p.rot });
    }
    return out;
  }
}
