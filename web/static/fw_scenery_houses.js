// Small lit structures and objects of the realistic scenery: cottages (snowy roofs, chimneys, warm windows that
// light the snow below), a village church with a spire, waterfront town houses, a floodlit hilltop castle, boats with
// riding lights, a lit jetty, a glowing tent, wind-turbine towers and a crowd watching the show. Colour goes to `c`,
// material (albedo) to `m`; chimney / beacon / turbine positions (device px) go into S for fw_scene_fx.js.
import { prng } from './fw_noise.js';
import { mat, rgb } from './fw_scenery_parts.js';
import { glow } from './fw_scenery_city.js';
import { tone } from './fw_scenery_sky.js';

const WARM = [255, 190, 110];
const both = (c, m, col, alb, fn) => { c.fillStyle = col; m.fillStyle = mat(alb); fn(c); fn(m); };
const poly = (k, pts) => { k.beginPath(); pts.forEach(([x, y]) => k.lineTo(x, y)); k.closePath(); k.fill(); };

// A lit window with a soft halo; `spill` adds a pool of light on the ground (snow) below it.
export function litWindow(c, x, y, w, h, rnd, spill = 0, col = WARM) {
  const k = 0.75 + rnd() * 0.25;
  c.fillStyle = rgb(...col.map(v => v * k), 0.95); c.fillRect(x, y, w, h);
  c.fillStyle = rgb(40, 25, 15, 0.7); c.fillRect(x + w / 2 - w * 0.06, y, w * 0.12, h); c.fillRect(x, y + h / 2 - h * 0.05, w, h * 0.1);
  glow(c, x + w / 2, y + h / 2, Math.max(w, h) * 1.6, col, 0.22, 0.3);
  if (spill) {
    const g = c.createRadialGradient(x + w / 2, y + h + spill * 0.3, 0, x + w / 2, y + h + spill * 0.3, spill);
    g.addColorStop(0, rgb(...col, 0.22)); g.addColorStop(1, rgb(...col, 0));
    c.fillStyle = g; c.fillRect(x + w / 2 - spill, y + h, 2 * spill, spill * 1.3);
  }
}

// Cottage standing on `base`: walls, steep roof (snow-covered when opts.snow), a chimney, lit windows.
export function cottage(S, c, m, x, base, w, h, rnd, sc, { snow = false, spill = 0, haze = 0.3 } = {}) {
  const wall = tone(S, [16, 14, 16], haze), roofC = tone(S, snow ? [72, 80, 104] : [12, 12, 16], haze);
  const rh = h * (0.55 + rnd() * 0.3), eave = w * 0.08;
  both(c, m, rgb(...wall), 0.35, k => k.fillRect(x, base - h, w, h));
  const roof = [[x - eave, base - h], [x + w / 2, base - h - rh], [x + w + eave, base - h]];
  both(c, m, rgb(...roofC), snow ? 0.8 : 0.3, k => poly(k, roof));
  if (snow) {                                                 // snow edge overhanging the eaves, darker underside
    c.fillStyle = rgb(...roofC.map(v => v * 1.15)); c.fillRect(x - eave, base - h - 1.5 * sc, w + 2 * eave, 2.2 * sc);
    c.fillStyle = rgb(...roofC.map(v => v * 0.55)); c.beginPath(); c.moveTo(x + w / 2, base - h - rh);
    c.lineTo(x + w + eave, base - h); c.lineTo(x + w / 2 + w * 0.12, base - h); c.closePath(); c.fill();
  }
  const cx = x + w * (0.2 + rnd() * 0.55), cw = w * 0.11, ctop = base - h - rh * (0.55 + rnd() * 0.25) - 6 * sc;
  both(c, m, rgb(...wall), 0.35, k => k.fillRect(cx, ctop, cw, base - h - ctop - rh * 0.15));
  if (snow) { c.fillStyle = rgb(...roofC); c.fillRect(cx - 0.6 * sc, ctop - 1.4 * sc, cw + 1.2 * sc, 1.8 * sc); }
  S.chimneys.push([cx + cw / 2, ctop - 1.5 * sc, cw]);
  const n = w > 30 * sc ? 2 + Math.floor(rnd() * 2) : 1, ww = Math.min(w * 0.16, 6 * sc), wh = Math.min(h * 0.38, 7 * sc);
  for (let i = 0; i < n; i++) {
    if (rnd() < 0.2) continue;
    const wx = x + w * (i + 0.5) / n - ww / 2;
    litWindow(c, wx, base - h * 0.62, ww, wh, rnd, spill);
  }
  if (rnd() < 0.5) litWindow(c, x + w / 2 - ww * 0.35, base - h - rh * 0.55, ww * 0.7, wh * 0.7, rnd);   // attic light
}

// Village church: nave with tall lit windows, a square tower with a spire, a faintly lit clock face.
export function church(S, c, m, x, base, sc, rnd, { snow = false, haze = 0.3 } = {}) {
  const wall = tone(S, [18, 16, 18], haze), roofC = tone(S, snow ? [72, 80, 104] : [12, 12, 16], haze);
  const nw = 70 * sc, nh = 26 * sc, tw = 16 * sc, th = 58 * sc, sh = 52 * sc, tx = x - tw;
  both(c, m, rgb(...wall), 0.4, k => k.fillRect(x, base - nh, nw, nh));
  both(c, m, rgb(...roofC), snow ? 0.8 : 0.3, k => poly(k, [[x - 2 * sc, base - nh], [x + 6 * sc, base - nh - 18 * sc], [x + nw - 6 * sc, base - nh - 18 * sc], [x + nw + 2 * sc, base - nh]]));
  for (let i = 0; i < 4; i++) {                               // tall arched windows, warm
    const wx = x + 10 * sc + i * 15 * sc, wy = base - nh + 6 * sc;
    c.fillStyle = rgb(255, 180, 100, 0.85); c.beginPath(); c.moveTo(wx, wy + 14 * sc); c.lineTo(wx, wy + 2.5 * sc);
    c.arc(wx + 2.5 * sc, wy + 2.5 * sc, 2.5 * sc, Math.PI, 0); c.lineTo(wx + 5 * sc, wy + 14 * sc); c.closePath(); c.fill();
    glow(c, wx + 2.5 * sc, wy + 8 * sc, 12 * sc, [255, 170, 90], 0.15);
  }
  both(c, m, rgb(...wall), 0.4, k => k.fillRect(tx, base - th, tw, th));
  both(c, m, rgb(...roofC.map(v => v * 0.8)), 0.4, k => poly(k, [[tx - 1.5 * sc, base - th], [tx + tw / 2, base - th - sh], [tx + tw + 1.5 * sc, base - th]]));
  const fl = c.createLinearGradient(0, base - th - sh, 0, base);   // a floodlight from below on the tower
  fl.addColorStop(0, rgb(255, 210, 160, 0)); fl.addColorStop(1, rgb(255, 210, 160, 0.18));
  c.fillStyle = fl; c.fillRect(tx, base - th, tw, th);
  c.fillStyle = rgb(255, 230, 180, 0.5); c.beginPath(); c.arc(tx + tw / 2, base - th + 10 * sc, 3.5 * sc, 0, 6.2832); c.fill();
  c.fillStyle = rgb(255, 170, 90, 0.8); c.fillRect(tx + tw / 2 - 2 * sc, base - th + 20 * sc, 4 * sc, 8 * sc);
  c.strokeStyle = rgb(...wall); c.lineWidth = 1 * sc; c.beginPath();                // cross on the spire
  c.moveTo(tx + tw / 2, base - th - sh); c.lineTo(tx + tw / 2, base - th - sh - 7 * sc);
  c.moveTo(tx + tw / 2 - 2.5 * sc, base - th - sh - 5 * sc); c.lineTo(tx + tw / 2 + 2.5 * sc, base - th - sh - 5 * sc); c.stroke();
  return base - th - sh;
}

// Row of waterfront town houses (gabled, 2-4 floors, lit windows) from x0 to x1 standing on `base`.
export function townRow(S, c, m, x0, x1, base, sc, rnd, haze = 0.4) {
  for (let x = x0; x < x1;) {
    const w = (14 + rnd() * 16) * sc, floors = 2 + Math.floor(rnd() * 3), fh = 7.5 * sc, h = floors * fh + 3 * sc;
    const col = tone(S, [14 + rnd() * 8, 13 + rnd() * 6, 16 + rnd() * 6], haze), gable = rnd() < 0.6;
    both(c, m, rgb(...col), 0.35, k => { k.fillRect(x, base - h, w, h); if (gable) poly(k, [[x, base - h], [x + w / 2, base - h - w * 0.45], [x + w, base - h]]); else k.fillRect(x, base - h - 2 * sc, w, 2 * sc); });
    for (let f = 0; f < floors; f++) for (let i = 0; i < Math.max(1, Math.floor(w / (6 * sc))); i++) {
      if (rnd() > 0.38) continue;
      c.fillStyle = rgb(...(rnd() < 0.85 ? WARM : [200, 220, 255]), 0.6 + rnd() * 0.35);
      c.fillRect(x + 2 * sc + i * 6 * sc, base - h + 3 * sc + f * fh, 2.6 * sc, 3.6 * sc);
    }
    x += w + (rnd() < 0.15 ? 2 * sc : 0);
  }
}

// Floodlit castle centred at cx on `base` (px): curtain wall with crenellations, round towers with conical roofs,
// a tall keep, lit windows. Floodlights from below make the stone warm at the foot, fading upwards.
export function castle(S, c, m, cx, base, sc, rnd) {
  const stone = (y0, y1) => { const g = c.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, rgb(...tone(S, [62, 50, 44], 0.2))); g.addColorStop(1, rgb(170, 128, 80)); return g; };
  const roofC = rgb(...tone(S, [16, 16, 24], 0.2));
  const block = (x, y, w, h, crenel = true) => {
    both(c, m, stone(y, y + h), 0.6, k => k.fillRect(x, y, w, h));
    if (crenel) for (let i = 0; i < w / (4 * sc) - 1; i += 2) both(c, m, stone(y - 3 * sc, y + h), 0.6, k => k.fillRect(x + i * 4 * sc, y - 3 * sc, 4 * sc, 3 * sc));
  };
  const tower = (x, w, h, coneH) => {
    block(x, base - h, w, h, coneH === 0);
    if (coneH) {
      both(c, m, roofC, 0.25, k => poly(k, [[x - 2 * sc, base - h], [x + w / 2, base - h - coneH], [x + w + 2 * sc, base - h]]));
      c.strokeStyle = rgb(20, 20, 28); c.lineWidth = 0.8 * sc; c.beginPath(); c.moveTo(x + w / 2, base - h - coneH); c.lineTo(x + w / 2, base - h - coneH - 6 * sc); c.stroke();
    }
    for (let i = 0; i < 3; i++) if (rnd() < 0.55) litWindow(c, x + w / 2 - 1.4 * sc, base - h + (8 + i * 14) * sc, 2.8 * sc, 5 * sc, rnd);
  };
  const W = 230 * sc;
  block(cx - W / 2, base - 42 * sc, W, 42 * sc);                 // curtain wall
  for (let i = 0; i < 9; i++) c.fillStyle = rgb(30, 22, 18, 0.6), c.fillRect(cx - W / 2 + (12 + i * 25) * sc, base - 30 * sc, 2 * sc, 6 * sc);  // arrow slits
  tower(cx - W / 2 - 12 * sc, 24 * sc, 70 * sc, 34 * sc);
  tower(cx + W / 2 - 12 * sc, 24 * sc, 64 * sc, 30 * sc);
  tower(cx - 70 * sc, 20 * sc, 92 * sc, 30 * sc);
  block(cx - 30 * sc, base - 125 * sc, 56 * sc, 83 * sc);           // keep
  tower(cx + 18 * sc, 16 * sc, 150 * sc, 36 * sc);                // slender watch tower beside the keep
  tower(cx + 60 * sc, 22 * sc, 84 * sc, 0);
  for (let f = 0; f < 3; f++) for (let i = 0; i < 4; i++) if (rnd() < 0.5) litWindow(c, cx - 24 * sc + i * 13 * sc, base - 112 * sc + f * 22 * sc, 3.2 * sc, 6 * sc, rnd);
  c.fillStyle = rgb(70, 40, 25); c.beginPath(); c.arc(cx + 2 * sc, base - 12 * sc, 9 * sc, Math.PI, 0); c.fillRect(cx - 7 * sc, base - 12 * sc, 18 * sc, 12 * sc); c.fill();
  glow(c, cx + 2 * sc, base - 8 * sc, 22 * sc, [255, 170, 90], 0.25);
  glow(c, cx, base - 60 * sc, W * 0.9, [255, 170, 100], 0.07, 0.3);   // floodlight haze around the walls
}

// Boat (side view, facing right) on the waterline y: hull, cabin, mast (sailing) and riding lights. Also used by the
// bobbing-boat plug-in (fw_scene_fx.js) to pre-render its sprites. Returns the masthead light's offset [dx, dy].
export function boat(k, x, y, len, sc, rnd, { sail = true, colour = [12, 13, 18], lights = true } = {}) {
  const h = len * 0.16;
  k.fillStyle = rgb(...colour); k.beginPath();
  k.moveTo(x - len / 2, y - h); k.lineTo(x + len / 2 + len * 0.06, y - h * 1.15);
  k.quadraticCurveTo(x + len * 0.42, y + h * 0.2, x + len * 0.25, y + h * 0.25); k.lineTo(x - len * 0.42, y + h * 0.2);
  k.closePath(); k.fill();
  k.fillStyle = rgb(...colour.map(v => Math.min(255, v * 1.8 + 20))); k.fillRect(x - len / 2, y - h * 1.05, len * 1.04, h * 0.18);   // gunwale catching light
  k.fillStyle = rgb(...colour.map(v => v * 1.4)); k.fillRect(x - len * 0.2, y - h * 1.9, len * 0.32, h * 0.95);   // cabin
  let top = [0, -h * 1.9];
  if (sail) {
    const mh = len * (0.9 + rnd() * 0.4);
    k.fillStyle = rgb(...colour.map(v => v * 1.8)); k.fillRect(x - 0.5 * sc, y - h - mh, 1 * sc, mh);
    k.strokeStyle = rgb(...colour.map(v => v * 1.8)); k.lineWidth = 0.5 * sc; k.beginPath();
    k.moveTo(x, y - h - mh); k.lineTo(x + len * 0.5, y - h); k.moveTo(x, y - h - mh); k.lineTo(x - len * 0.48, y - h); k.stroke();
    top = [0, -h - mh];
  }
  if (lights) {
    k.fillStyle = rgb(255, 245, 220); k.beginPath(); k.arc(x + top[0], y + top[1], 1.1 * sc, 0, 6.2832); k.fill();
    glow(k, x + top[0], y + top[1], 6 * sc, [255, 240, 210], 0.35);
    k.fillStyle = rgb(255, 200, 130, 0.85); k.fillRect(x - len * 0.15, y - h * 1.6, len * 0.06, h * 0.4); k.fillRect(x, y - h * 1.6, len * 0.06, h * 0.4);
  }
  return top;
}

// Jetty on piles from x0 to x1 at deck height y (below the waterline), with lamp posts; lamp positions returned.
export function jetty(S, c, m, x0, x1, y, sc, rnd) {
  const col = rgb(...tone(S, [10, 10, 14], 0.3)), lamps = [];
  both(c, m, col, 0.3, k => { k.fillRect(x0, y - 3 * sc, x1 - x0, 4 * sc); for (let x = x0; x < x1; x += 9 * sc) k.fillRect(x, y, 1.6 * sc, 7 * sc); });
  c.fillStyle = rgb(90, 80, 70, 0.3); c.fillRect(x0, y - 3 * sc, x1 - x0, 0.8 * sc);      // lamp-lit plank edge
  for (let x = x0 + 12 * sc; x < x1; x += (34 + rnd() * 8) * sc) {
    both(c, m, col, 0.3, k => k.fillRect(x - 0.6 * sc, y - 22 * sc, 1.2 * sc, 19 * sc));
    c.fillStyle = rgb(255, 215, 150); c.beginPath(); c.arc(x, y - 23 * sc, 1.6 * sc, 0, 6.2832); c.fill();
    glow(c, x, y - 23 * sc, 14 * sc, [255, 180, 100], 0.45);
    glow(c, x, y - 2 * sc, 10 * sc, [255, 180, 100], 0.15);       // light pool on the planks
    lamps.push([x, y - 23 * sc]);
  }
  return lamps;
}

// Small tent glowing from a lantern inside, with a pool of light on the sand.
export function tent(c, m, x, base, sc) {
  const w = 26 * sc, h = 16 * sc;
  glow(c, x, base, 45 * sc, [255, 150, 70], 0.18, 0.2);
  const g = c.createLinearGradient(x, base - h, x, base);
  g.addColorStop(0, rgb(150, 80, 40)); g.addColorStop(1, rgb(240, 140, 60));
  c.fillStyle = g; poly(c, [[x - w / 2, base], [x, base - h], [x + w / 2, base]]);
  m.fillStyle = mat(0.5); poly(m, [[x - w / 2, base], [x, base - h], [x + w / 2, base]]);
  c.fillStyle = rgb(255, 210, 140); poly(c, [[x - 3 * sc, base], [x, base - h * 0.55], [x + 3 * sc, base]]);
  c.strokeStyle = rgb(30, 20, 18); c.lineWidth = 0.8 * sc; c.beginPath(); c.moveTo(x, base - h); c.lineTo(x, base - h - 4 * sc); c.stroke();
}

// Wind-turbine tower and nacelle (the blades are animated by fw_scene_fx.js); hub position pushed to S.turbines.
export function turbine(S, c, m, x, base, h, sc) {
  const col = rgb(...tone(S, [44, 48, 64], 0.8));
  both(c, m, col, 0.3, k => { poly(k, [[x - 1.6 * sc, base], [x - 0.7 * sc, base - h], [x + 0.7 * sc, base - h], [x + 1.6 * sc, base]]); k.fillRect(x - 1.5 * sc, base - h - 1.5 * sc, 5 * sc, 3 * sc); });
  S.turbines.push([x, base - h, h * 0.42]);
}

// A crowd watching the show along the bottom edge: heads and shoulders, a few raised phones with lit screens.
export function crowd(c, m, W, H, seed, sc, top) {
  const rnd = prng(seed);
  for (const [row, dark, sz] of [[0, [9, 9, 12], 0.85], [1, [4, 4, 6], 1.15]]) {
    const y0 = top + row * 16 * sc;
    for (let x = -10 * sc; x < W + 10 * sc; x += (12 + rnd() * 8) * sc * sz) {
      const s = sc * sz * (0.85 + rnd() * 0.3), hx = x + (rnd() - 0.5) * 4 * sc, hy = y0 + (rnd() - 0.5) * 6 * sc, arm = rnd() < 0.07;
      for (const k of [c, m]) {
        k.fillStyle = k === m ? mat(0.25) : rgb(...dark);
        k.beginPath(); k.ellipse(hx, hy, 4.2 * s, 5.2 * s, 0, 0, 6.2832); k.fill();
        k.beginPath(); k.moveTo(hx - 11 * s, H); k.lineTo(hx - 10 * s, hy + 9 * s); k.quadraticCurveTo(hx, hy + 4 * s, hx + 10 * s, hy + 9 * s); k.lineTo(hx + 11 * s, H); k.fill();
        if (arm) { k.fillRect(hx + 6 * s, hy - 12 * s, 2 * s, 18 * s); k.beginPath(); k.ellipse(hx + 7 * s, hy - 13 * s, 2.4 * s, 2.4 * s, 0, 0, 6.2832); k.fill(); }
      }
      if (row === 1 && rnd() < 0.08) {                        // phone held up, screen glowing
        const px = hx + (rnd() - 0.5) * 10 * s, py = hy - 16 * s;
        c.fillStyle = rgb(...dark); c.fillRect(px - 0.8 * s, py + 4 * s, 1.6 * s, 10 * s);
        c.fillStyle = rgb(190, 215, 255, 0.85); c.fillRect(px - 2.6 * s, py - 4 * s, 5.2 * s, 8 * s);
        glow(c, px, py, 14 * s, [170, 200, 255], 0.18);
      }
    }
  }
}
