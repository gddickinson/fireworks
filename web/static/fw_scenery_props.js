// Natural props of the realistic scenery: tree lines and surf (moved unchanged from fw_scenery.js), snow-laden
// conifers, flat-topped mesas, wind-shaped dunes, a single smooth hill, rolling fields with hedgerows, and rippled
// reflections of single lights on water. Colour goes to `c`, material (albedo) to `m`.
// Porting note (QPainter/numpy): every shape here is a polyline filled with a linear gradient; dunes() shades by
// slope through a horizontal gradient with one stop per few columns (as snow() in fw_scenery_parts.js does).
import { fbm1, hash, prng } from './fw_noise.js';
import { conifer, fillRidge, mat, mixc, rgb } from './fw_scenery_parts.js';

export const sizeScale = S => Math.min(S.H / 800, S.W / 900);   // structure size: fits portrait phones too

export function treeLine(c, m, W, H, y, seed, h, col) {
  const rnd = prng(seed), n = Math.round(W / (h * 0.22));
  c.fillStyle = rgb(...col); m.fillStyle = mat(0.2);
  c.fillRect(0, y - h * 0.15, W, h * 0.2); m.fillRect(0, y - h * 0.15, W, h * 0.2);
  for (let i = 0; i < n; i++) {
    const x = (i + rnd()) * W / n, th = h * (0.5 + rnd() * 0.7) * (0.7 + 0.6 * fbm1(seed, x / W * 3, 3));
    const s = seed * 1000 + i;
    conifer(c, x, y + 1, th, prng(s)); conifer(m, x, y + 1, th, prng(s));
  }
}

export function surf(c, W, H, wl, seed) {                    // faint foam lines catching the sky light
  const sc = H / 800;
  for (let i = 0; i < 6; i++) {
    const y = wl + (H - wl) * (0.25 + i * 0.13), a = 0.05 + i * 0.015;
    c.strokeStyle = rgb(160, 175, 210, a); c.lineWidth = (1 + i * 0.5) * sc; c.beginPath();
    for (let x = 0; x <= W; x += 8) c.lineTo(x, y + Math.sin(x / (60 * sc) + i * 1.7) * 3 * sc + (hash(seed, x, i) - 0.5) * 2 * sc);
    c.stroke();
  }
}

// Conifer with snow lying on the upper side of each tier (pale strokes along the tier tops).
export function snowyConifer(c, m, x, y, h, seed, dark, snowCol) {
  c.fillStyle = rgb(...dark); conifer(c, x, y, h, prng(seed));
  m.fillStyle = mat(0.3); conifer(m, x, y, h, prng(seed));
  const rnd = prng(seed + 1), tiers = 6 + Math.floor(rnd() * 3), w = h * 0.32;
  c.fillStyle = rgb(...snowCol, 0.85);
  for (let i = 1; i <= tiers; i++) {
    const t = i / tiers, ty = y - h + h * 0.92 * t, tw = w * t * (0.7 + rnd() * 0.25), th = h * 0.035 * (0.6 + rnd() * 0.6);
    c.beginPath(); c.moveTo(x - tw * 0.85, ty - h * 0.01); c.quadraticCurveTo(x, ty - h * 0.11 * (1 - t * 0.5), x + tw * 0.75, ty - h * 0.02);
    c.quadraticCurveTo(x, ty - h * 0.11 * (1 - t * 0.5) + th, x - tw * 0.85, ty - h * 0.01); c.fill();
  }
}

// Flat-topped mesas and buttes: fbm pushed through a steep step, so tops are flat and the walls are cliffs.
export function mesaLine(W, H, seed, { base, amp, rough = 2.5, step = 2 }) {
  const ys = [];
  for (let x = 0; x <= W + step; x += step) {
    const u = x / W * rough, f = fbm1(seed, u, 5);
    const t = Math.min(1, Math.max(0, (f - 0.48) * 7)), mesa = t * t * (3 - 2 * t);
    const tier = Math.min(1, Math.max(0, (fbm1(seed + 3, u * 0.7, 3) - 0.5) * 6)) * 0.35;
    const detail = (fbm1(seed + 9, u * 25, 3) - 0.5) * 0.06;
    ys.push(H * (base - amp * (mesa * (0.65 + tier) + 0.05 * f + detail * (0.3 + mesa))));
  }
  return { ys, step };
}

// One layer of dunes: sharp crests, smooth windward slopes lit by the sky, and a shadowed slip face behind each
// crest whose lower edge curves down towards the viewer (so crest lines read as sinuous ridges, not columns).
export function dunes(c, m, W, H, seed, { base, amp, waves = 3, lit, shade, albedo = 0.45, bottom = H }) {
  const step = 3, ys = [], crest = [];
  let prev = 0;
  for (let x = 0; x <= W + step; x += step) {
    const u = x / W * waves + fbm1(seed, x / W * 2, 3) * 0.8, ph = u - Math.floor(u);
    const shape = ph < 0.68 ? 0.5 - 0.5 * Math.cos(Math.PI * ph / 0.68) : Math.pow((1 - ph) / 0.32, 1.3);   // slow rise, steep fall
    const height = 0.55 + 0.45 * fbm1(seed + 4, Math.floor(u) * 0.37 + 0.2, 2);
    ys.push(H * (base - amp * (shape * height * 0.85 + 0.15 * fbm1(seed + 7, x / W * 5, 3))));
    if (ph < prev - 0.5 || (x === 0 && ph > 0.68)) crest.push(ys.length - 1);   // phase wrapped: the trough
    prev = ph;
  }
  const r = { ys, step }, top = Math.min(...ys), depth = bottom - top;
  const g = c.createLinearGradient(0, top, 0, bottom);
  g.addColorStop(0, rgb(...lit)); g.addColorStop(1, rgb(...mixc(lit, shade, 0.7)));
  fillRidge(c, W, H, r, g, bottom); fillRidge(m, W, H, r, mat(albedo), bottom);
  c.fillStyle = rgb(...shade, 0.85);
  for (const t of crest) {                                    // slip face: from the crest (highest point before the trough)
    let k = t; while (k > 0 && ys[k - 1] < ys[k]) k--;
    if (t - k < 2) continue;
    const xc = k * step, xt = t * step, yc = ys[k], drop = Math.min(depth * 0.9, (ys[t] - yc) * 2.5 + depth * 0.25);
    c.beginPath(); c.moveTo(xc, yc);
    for (let i = k; i <= t; i++) c.lineTo(i * step, ys[i]);
    c.quadraticCurveTo(xt + (xt - xc) * 0.2, yc + drop, xc - (xt - xc) * 0.15, yc + drop * 1.1);
    c.quadraticCurveTo(xc - (xt - xc) * 0.05, yc + drop * 0.3, xc, yc); c.fill();
  }
  c.save(); c.beginPath(); c.moveTo(0, bottom); ys.forEach((y, i) => c.lineTo(i * step, y)); c.lineTo(W, bottom); c.clip();
  const vg = c.createLinearGradient(0, top, 0, bottom);       // the layer darkens downwards (less sky light reaches)
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.45)');
  c.fillStyle = vg; c.fillRect(0, top, W, depth); c.restore();
  c.strokeStyle = rgb(...lit.map(v => Math.min(255, v * 1.5)), 0.5); c.lineWidth = Math.max(1, H / 900);   // crest edge
  c.beginPath(); ys.forEach((y, i) => c.lineTo(i * step, y)); c.stroke();
  return r;
}

// Spreading broadleaf tree (oak): a trunk splitting into branches recursively, leaf clumps at the twig ends.
export function oak(c, x, y, h, rnd) {
  const branch = (x0, y0, a, len, w, d) => {
    const x1 = x0 + Math.cos(a) * len, y1 = y0 + Math.sin(a) * len;
    c.beginPath(); c.moveTo(x0 - w / 2, y0); c.lineTo(x1 - w * 0.3, y1); c.lineTo(x1 + w * 0.3, y1); c.lineTo(x0 + w / 2, y0); c.fill();
    if (d === 0) {
      for (let i = 0; i < 16; i++) { c.beginPath(); c.arc(x1 + (rnd() - 0.5) * h * 0.13, y1 + (rnd() - 0.65) * h * 0.09, h * (0.008 + rnd() * 0.014), 0, 6.2832); c.fill(); }
      return;
    }
    const n = d > 2 ? 3 : 2 + (rnd() < 0.5 ? 1 : 0);
    for (let i = 0; i < n; i++) branch(x1, y1, a + (i - (n - 1) / 2) * (0.42 + rnd() * 0.25) + (rnd() - 0.5) * 0.3, len * (0.66 + rnd() * 0.14), w * 0.6, d - 1);
  };
  branch(x, y, -Math.PI / 2 + (rnd() - 0.5) * 0.15, h * 0.33, h * 0.07, 4);
}

// A single rounded hill (castle mound): bump centred at cx (fraction of W), rocky detail on the flanks.
export function hillLine(W, H, seed, { base, amp, cx, width, step = 2 }) {
  const ys = [];
  for (let x = 0; x <= W + step; x += step) {
    const u = (x / W - cx) / width, bump = Math.exp(-u * u * 2.2) * (1 - 0.18 * Math.exp(-u * u * 30));
    const flat = Math.exp(-Math.pow(u * 2.2, 8));                   // a flattened summit to build on
    const v = Math.max(bump, flat * 0.93) + (fbm1(seed, x / W * 9, 5) - 0.5) * 0.08 * (1 - flat) + (fbm1(seed + 2, x / W * 2, 3) - 0.5) * 0.1;
    ys.push(H * (base - amp * v));
  }
  return { ys, step };
}
export const ridgeY = ({ ys, step }, x) => ys[Math.max(0, Math.min(ys.length - 1, Math.round(x / step)))];

// Rolling farmland on a ridge (from ridgeLine): fields in slightly different tones between contour hedgerows and
// cross hedges, with trees along the hedges. depth: how far down the fields reach (px). The ridge itself must
// already be painted (range()).
export function fields(c, m, W, H, r, seed, { depth, rows = 4, col, sc }) {
  const rnd = prng(seed), off = k => depth * Math.pow(k / rows, 1.4);
  for (let k = 0; k < rows; k++) {                          // field strips between contours, cut by cross hedges
    let x0 = 0;
    while (x0 < W) {
      const x1 = Math.min(W + 4, x0 + W * (0.06 + rnd() * 0.12) * (1 + k * 0.4));
      const tint = 0.75 + rnd() * 0.5;
      c.fillStyle = rgb(...col.map(v => v * tint)); c.beginPath();
      for (let x = x0; x <= x1; x += 4) c.lineTo(x, ridgeY(r, x) + off(k) + 2 * sc);
      for (let x = x1; x >= x0; x -= 4) c.lineTo(x, ridgeY(r, x) + off(k + 1));
      c.closePath(); c.fill();
      c.strokeStyle = rgb(...col.map(v => v * 0.45)); c.lineWidth = (0.8 + k * 0.5) * sc;   // cross hedge
      c.beginPath(); c.moveTo(x1, ridgeY(r, x1) + off(k)); c.lineTo(x1 + (rnd() - 0.5) * 20 * sc, ridgeY(r, x1) + off(k + 1)); c.stroke();
      x0 = x1;
    }
    c.strokeStyle = rgb(...col.map(v => v * 0.4)); c.lineWidth = (1 + k * 0.6) * sc;      // contour hedge
    c.beginPath(); for (let x = 0; x <= W; x += 4) c.lineTo(x, ridgeY(r, x) + off(k + 1)); c.stroke();
    c.fillStyle = rgb(...col.map(v => v * 0.35));               // trees along the hedge
    for (let x = rnd() * 40 * sc; x < W; x += (8 + rnd() * rnd() * 90) * sc * (1 + k * 0.5)) {
      const y = ridgeY(r, x) + off(k + 1), rr = (1.2 + rnd() * rnd() * 4) * sc * (1 + k * 0.45);
      c.beginPath(); c.arc(x, y - rr * 0.8, rr, 0, 6.2832); c.arc(x + rr * 0.7, y - rr * 0.5, rr * 0.8, 0, 6.2832); c.fill();
    }
  }
  m.fillStyle = mat(0.3); m.beginPath(); m.moveTo(0, H);
  for (let x = 0; x <= W; x += 4) m.lineTo(x, ridgeY(r, x)); m.lineTo(W, H); m.closePath(); m.fill();
}

// The rippled reflection of a point light at (x, y) on water starting at y0: a column of short horizontal dashes,
// wider and fainter with distance, jittered sideways (seeded).
export function lightReflection(c, x, y0, len, col, sc, seed, a = 0.5) {
  const rnd = prng(seed);
  for (let d = 1.5 * sc; d < len; d += (1.6 + rnd() * 1.6) * sc) {
    const t = d / len, w = (1.5 + 9 * t + rnd() * 4) * sc, al = a * (1 - t) * (0.4 + rnd() * 0.6);
    if (al < 0.02) continue;
    c.fillStyle = rgb(...col, al); c.fillRect(x - w / 2 + (rnd() - 0.5) * 3 * sc * (1 + 3 * t), y0 + d, w, (0.7 + rnd() * 0.8) * sc);
  }
}
