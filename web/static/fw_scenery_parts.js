// Painting primitives for the realistic scenery (fw_scenery.js): night-sky gradient with airglow and light
// pollution, star field with a magnitude distribution, Milky Way, fractal ridgelines with haze, city skylines,
// trees and palms, and rippled water reflections. Every painter draws colour into `c` (a 2D context) and, where it
// matters for lighting, material into `m`: red = how strongly firework light brightens the surface (albedo),
// green = water (reflects fireworks), blue = open sky (scatters light).
import { fbm1, fbm2, ridged1 } from './fw_noise.js';

export const rgb = (r, g, b, a = 1) => `rgba(${r | 0},${g | 0},${b | 0},${a})`;
export const mat = (albedo, water = 0, sky = 0) => rgb(albedo * 255, water * 255, sky * 255);
export const mixc = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);

export function sky(c, W, H, { top, mid, low, glow = null, glowH = 0.25, horizon }) {
  const g = c.createLinearGradient(0, 0, 0, horizon);
  g.addColorStop(0, rgb(...top)); g.addColorStop(0.55, rgb(...mid)); g.addColorStop(1, rgb(...low));
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  if (glow) {                                                 // light pollution / last twilight above the horizon
    const gg = c.createLinearGradient(0, horizon - H * glowH, 0, horizon);
    gg.addColorStop(0, rgb(...glow, 0)); gg.addColorStop(0.7, rgb(...glow, 0.35)); gg.addColorStop(1, rgb(...glow, 0.75));
    c.fillStyle = gg; c.fillRect(0, horizon - H * glowH, W, H * glowH);
  }
  const ag = c.createLinearGradient(0, horizon - H * 0.16, 0, horizon - H * 0.02);  // faint green airglow band
  ag.addColorStop(0, rgb(40, 90, 60, 0)); ag.addColorStop(0.5, rgb(40, 90, 60, 0.07)); ag.addColorStop(1, rgb(40, 90, 60, 0));
  c.fillStyle = ag; c.fillRect(0, horizon - H * 0.16, W, H * 0.14);
}

// Stars: counts grow steeply towards faint magnitudes; colours from blue-white to orange; extinction near the horizon.
export function stars(c, W, H, rnd, { n, horizon, dim = 1, milky = null }) {
  const s = Math.max(1, H / 900);
  for (let i = 0; i < n; i++) {
    const x = rnd() * W, y = Math.pow(rnd(), 1.25) * horizon;
    let m = Math.pow(rnd(), 5.5);                              // most stars faint, a few bright
    if (milky && Math.abs(milky(x, y)) < 0.12 * H) m = Math.max(m, Math.pow(rnd(), 3.5) * 0.6);
    const ext = Math.min(1, (horizon - y) / (horizon * 0.35));
    const a = (0.12 + 0.88 * m) * ext * dim;
    if (a < 0.03) continue;
    const t = rnd(), col = t < 0.2 ? [170, 195, 255] : t < 0.75 ? [235, 238, 255] : t < 0.93 ? [255, 236, 205] : [255, 200, 160];
    const r = (0.35 + 0.95 * m) * s;
    c.fillStyle = rgb(...col, a);
    c.beginPath(); c.arc(x, y, r, 0, 6.2832); c.fill();
    if (m > 0.9) {
      const g = c.createRadialGradient(x, y, 0, x, y, r * 6);
      g.addColorStop(0, rgb(...col, 0.18 * a)); g.addColorStop(1, rgb(...col, 0));
      c.fillStyle = g; c.fillRect(x - r * 6, y - r * 6, r * 12, r * 12);
    }
  }
}

// The Milky Way: a diffuse band with mottled star clouds and dark dust lanes, painted at low resolution and scaled up.
// Returns a function giving a point's signed distance (px) from the band's centre line.
export function milkyWay(c, W, H, seed, { horizon, angle = -0.5, cx = 0.6, strength = 1 }) {
  const lw = 256, lh = Math.max(32, Math.round(256 * horizon / W)), off = document.createElement('canvas');
  off.width = lw; off.height = lh;
  const o = off.getContext('2d'), img = o.createImageData(lw, lh), d = img.data;
  const ca = Math.cos(angle), sa = Math.sin(angle), x0 = cx * W, y0 = horizon * 0.45, width = H * 0.16;
  const dist = (x, y) => -(x - x0) * sa + (y - y0) * ca;
  for (let j = 0; j < lh; j++) for (let i = 0; i < lw; i++) {
    const x = (i + 0.5) * W / lw, y = (j + 0.5) * horizon / lh, u = dist(x, y) / width;
    const along = ((x - x0) * ca + (y - y0) * sa) / width;
    const band = Math.exp(-u * u * 1.6);
    const cloud = fbm2(seed, along * 0.9, u * 1.4, 5);
    const lane = Math.max(0, 1 - 2.2 * Math.abs(u + 0.25 * (fbm2(seed + 9, along * 0.6, 0.3, 3) - 0.5))) *
      Math.max(0, fbm2(seed + 5, along * 1.6, u * 2.5, 4) - 0.35) * 2.2;
    const ext = Math.min(1, (horizon - y) / (horizon * 0.4));
    const v = Math.max(0, band * (0.35 + 0.9 * cloud) - lane * band * 0.9) * ext * strength;
    const k = (j * lw + i) * 4;
    d[k] = 150 + 60 * cloud; d[k + 1] = 150 + 40 * cloud; d[k + 2] = 190; d[k + 3] = Math.min(255, v * 70);
  }
  o.putImageData(img, 0, 0);
  c.save(); c.imageSmoothingEnabled = true; c.imageSmoothingQuality = 'high';
  c.drawImage(off, 0, 0, W, horizon); c.restore();
  return dist;
}

// A ridgeline (array of y per x column). base: fraction of H; amp: fraction of H; rough: features per screen width.
export function ridgeLine(W, H, seed, { base, amp, rough = 3, sharp = 0.6, step = 2, taper = null }) {
  const ys = [];
  for (let x = 0; x <= W + step; x += step) {
    const u = x / W * rough, r = ridged1(seed, u + 3.1, 7), f = fbm1(seed + 7, u * 1.7, 6);
    const detail = fbm1(seed + 11, u * 14, 4) - 0.5;          // rocky, jagged small scale
    let v = sharp * r + (1 - sharp) * f + detail * 0.08;
    if (taper) v *= taper(x / W);
    ys.push(H * (base - amp * v));
  }
  return { ys, step };
}
export function fillRidge(c, W, H, { ys, step }, fill, bottom = H) {
  c.beginPath(); c.moveTo(0, bottom);
  ys.forEach((y, i) => c.lineTo(i * step, y));
  c.lineTo(W, bottom); c.closePath(); c.fillStyle = fill; c.fill();
}
// A ridge range with vertical gradient (lighter, hazier crest towards the distance) on c, its material on m.
export function range(c, m, W, H, seed, opts, colTop, colBot, albedo, bottom = H) {
  const r = ridgeLine(W, H, seed, opts), top = Math.min(...r.ys);
  const g = c.createLinearGradient(0, top, 0, bottom);
  g.addColorStop(0, rgb(...colTop)); g.addColorStop(1, rgb(...colBot));
  fillRidge(c, W, H, r, g, bottom); fillRidge(m, W, H, r, mat(albedo), bottom);
  return r;
}
// Snow on the highest parts of a ridge, wherever the crest rises above `line` (px): one polygon per snowy stretch,
// hugging the crest, deeper higher up, with a ragged noise-shaped lower edge. Shading follows the smoothed slope
// (faces turned left, towards the moon, are lighter) through a horizontal gradient, so it varies smoothly at any
// resolution, and the snow fades downwards. The material map marks snow as bright (lit strongly by bursts).
export function snow(c, m, { ys, step }, line, depth, seed) {
  const W = c.canvas.width, H = c.canvas.height;
  const lower = (x, y) => y + Math.max(0, Math.min(depth, (line - y) * 0.9) * (0.35 + 0.95 * fbm1(seed, x * 0.018, 5)));
  const smoothY = i => { let a = 0, n = 0; for (let k = -6; k <= 6; k++) { const v = ys[i + k]; if (v !== undefined) { a += v; n++; } } return a / n; };
  const draw = idx => {                                       // idx: crest column indices of one snowy stretch
    if (idx.length < 3) return;
    const x0 = idx[0] * step, x1 = idx[idx.length - 1] * step, top = Math.min(...idx.map(i => ys[i]));
    const bot = Math.max(...idx.map(i => lower(i * step, ys[i])));
    const path = k => {
      k.beginPath(); idx.forEach(i => k.lineTo(i * step, ys[i]));
      for (let r = idx.length - 1; r >= 0; r--) k.lineTo(idx[r] * step, lower(idx[r] * step, ys[idx[r]]));
      k.closePath();
    };
    const hg = c.createLinearGradient(x0, 0, x1 + 0.01, 0);
    for (let r = 0; r < idx.length; r += 3) {                 // slope -> brightness, smooth along x
      const i = idx[r], slope = (smoothY(i + 3) - smoothY(i - 3)) / (6 * step), b = Math.min(1, Math.max(0, 0.5 + slope * 1.6));
      hg.addColorStop((i * step - x0) / Math.max(1, x1 - x0), rgb(105 + 80 * b, 115 + 78 * b, 148 + 70 * b, 0.5 + 0.25 * b));
    }
    const off = document.createElement('canvas'); off.width = W; off.height = H;
    const o = off.getContext('2d');
    path(o); o.fillStyle = hg; o.fill();
    const vg = o.createLinearGradient(0, top, 0, bot + 1);
    vg.addColorStop(0, 'rgba(0,0,0,1)'); vg.addColorStop(1, 'rgba(0,0,0,0.12)');
    o.globalCompositeOperation = 'destination-in'; o.fillStyle = vg; o.fillRect(0, 0, W, H);
    c.drawImage(off, 0, 0);
    path(m); m.fillStyle = mat(0.85); m.fill();
  };
  let run = [];
  ys.forEach((y, i) => { if (y < line) run.push(i); else { draw(run); run = []; } });
  draw(run);
}

// Conifer silhouette (layered jagged tiers) or broadleaf (noisy blob) at base (x, y), height h.
export function conifer(c, x, y, h, rnd) {
  const w = h * (0.28 + rnd() * 0.12), tiers = 6 + Math.floor(rnd() * 4);
  c.beginPath(); c.moveTo(x, y - h);
  for (let i = 1; i <= tiers; i++) {
    const t = i / tiers, ty = y - h + h * 0.92 * t, tw = w * t * (0.75 + rnd() * 0.35);
    c.lineTo(x + tw, ty); c.lineTo(x + tw * 0.45, ty - h * 0.02);
  }
  c.lineTo(x + w * 0.08, y); c.lineTo(x - w * 0.08, y);
  for (let i = tiers; i >= 1; i--) {
    const t = i / tiers, ty = y - h + h * 0.92 * t, tw = w * t * (0.75 + rnd() * 0.35);
    c.lineTo(x - tw * 0.45, ty - h * 0.02); c.lineTo(x - tw, ty);
  }
  c.closePath(); c.fill();
}
export function broadleaf(c, x, y, h, rnd) {
  c.beginPath(); c.moveTo(x - h * 0.035, y); c.lineTo(x - h * 0.015, y - h * 0.5); c.lineTo(x + h * 0.015, y - h * 0.5);
  c.lineTo(x + h * 0.035, y); c.fill();
  const n = 40 + Math.floor(rnd() * 20), rx = h * (0.26 + rnd() * 0.1), ry = h * 0.24;
  for (let i = 0; i < n; i++) {                              // crown: many small clumps inside an irregular ellipse
    const a = rnd() * 6.2832, d = Math.sqrt(rnd());
    const cx = x + Math.cos(a) * rx * d, cy = y - h * 0.68 + Math.sin(a) * ry * d, rr = h * (0.03 + rnd() * 0.06);
    c.beginPath(); c.arc(cx, cy, rr, 0, 6.2832); c.fill();
  }
}
// Palm: curved, tapering trunk and arching fronds whose leaflets hang down towards the tip.
export function palm(c, x, y, h, lean, rnd) {
  const tx = x + lean * h * 0.35, ty = y - h, bx = x + lean * h * 0.05, by = y - h * 0.6;
  c.fillStyle = c.strokeStyle;
  c.beginPath();                                              // trunk as a tapered filled shape
  const w0 = h * 0.03, w1 = h * 0.016;
  c.moveTo(x - w0, y); c.quadraticCurveTo(bx - w1, by, tx - w1, ty); c.lineTo(tx + w1, ty);
  c.quadraticCurveTo(bx + w1, by, x + w0, y); c.closePath(); c.fill();
  c.lineCap = 'round';
  const fronds = 9 + Math.floor(rnd() * 4);
  for (let i = 0; i < fronds; i++) {
    const a = (i / fronds) * 6.2832 + rnd() * 0.4, dir = Math.cos(a), up = Math.sin(a) * 0.5 + 0.2;
    const len = h * (0.34 + rnd() * 0.16);
    const ex = tx + dir * len, ey = ty + len * (0.45 - up * 0.3) + len * 0.2 * (1 - Math.abs(dir));
    const mx = tx + dir * len * 0.55, my = ty - len * (0.18 + up * 0.25);
    c.lineWidth = h * 0.008; c.beginPath(); c.moveTo(tx, ty); c.quadraticCurveTo(mx, my, ex, ey); c.stroke();
    for (let k = 2; k < 22; k++) {                          // leaflets along the rib
      const t = k / 22, px = (1 - t) * (1 - t) * tx + 2 * (1 - t) * t * mx + t * t * ex;
      const py = (1 - t) * (1 - t) * ty + 2 * (1 - t) * t * my + t * t * ey;
      const l = len * (0.1 + 0.08 * rnd()) * Math.sin(Math.PI * Math.min(1, t * 1.15)), sx = dir * l * 0.55;
      c.lineWidth = h * (0.004 + rnd() * 0.003);
      c.beginPath(); c.moveTo(px, py); c.lineTo(px + sx + l * 0.25, py + l * 0.9);
      c.moveTo(px, py); c.lineTo(px + sx - l * 0.25, py + l * 0.85); c.stroke();
    }
  }
  for (let i = 0; i < 4; i++) { c.beginPath(); c.arc(tx + (rnd() - 0.5) * h * 0.04, ty + h * 0.02, h * 0.012, 0, 6.28); c.fill(); }
}

// Water below `wl` (px): base gradient, then a rippled, darkened mirror image of everything above it.
export function water(c, m, W, H, wl, seed, { tint = [8, 14, 28], reflect = 0.55 } = {}) {
  const src = document.createElement('canvas'); src.width = W; src.height = Math.ceil(wl);
  src.getContext('2d').drawImage(c.canvas, 0, 0);
  const g = c.createLinearGradient(0, wl, 0, H);
  g.addColorStop(0, rgb(...tint.map(v => v * 1.6))); g.addColorStop(1, rgb(...tint.map(v => v * 0.5)));
  c.fillStyle = g; c.fillRect(0, wl, W, H - wl);
  const strip = Math.max(1, Math.round(H / 400));
  for (let y = wl; y < H; y += strip) {
    const d = y - wl, sy = wl - d * 0.85 - 1;                  // mirrored row (slightly compressed)
    if (sy < 0) break;
    const off = (fbm2(seed, 0.3, d * 0.08, 3) - 0.5) * (1 + d * 0.03) + Math.sin(d * 0.9) * (0.3 + d * 0.006);
    const smear = Math.min(sy, 1 + d * 0.35);               // vertical smear grows with distance from the shore line
    c.globalAlpha = reflect * Math.max(0.25, 1 - d / (H - wl) * 0.6);
    c.drawImage(src, 0, sy - smear, W, strip + smear, off, y, W, strip);
  }
  c.globalAlpha = 1;
  m.fillStyle = mat(0.12, 1); m.fillRect(0, wl, W, H - wl);
}
