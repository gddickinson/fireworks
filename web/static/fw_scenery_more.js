// Waterside scenes of the realistic scenery (registered in fw_scenery.js): a fishing harbour, a cable-stayed bridge
// over a city river, and a big-city waterfront on New Year's Eve. Shells launch from barges on the waterline.
// Painter signature: (S, c, f, m, seed) with c/f/m the back/front/material contexts (see fw_scenery.js).
import { prng } from './fw_noise.js';
import { mat, range, rgb, water } from './fw_scenery_parts.js';
import { darkSky, starry, tone } from './fw_scenery_sky.js';
import { cableBridge, crownTower, ferrisWheel, glow, skyline, streetLights } from './fw_scenery_city.js';
import { lightReflection, ridgeY, sizeScale } from './fw_scenery_props.js';
import { boat, crowd, jetty, townRow } from './fw_scenery_houses.js';

// Hillside town: little houses with a lit window or two, denser towards the shore, and a winding lit road.
function hillTown(S, c, m, r, x0, x1, wl, sc, seed) {
  const rnd = prng(seed);
  for (let i = 0; i < (x1 - x0) / (3.2 * sc); i++) {
    const x = x0 + rnd() * (x1 - x0), top = ridgeY(r, x) + 8 * sc;
    if (top > wl - 10 * sc) continue;
    const y = wl - Math.pow(rnd(), 1.8) * (wl - top), w = (5 + rnd() * 7) * sc, h = (4 + rnd() * 4) * sc;
    c.fillStyle = rgb(...tone(S, [20, 20, 28], 0.6)); c.fillRect(x, y - h, w, h);
    c.beginPath(); c.moveTo(x - sc, y - h); c.lineTo(x + w / 2, y - h - w * 0.35); c.lineTo(x + w + sc, y - h); c.fill();
    if (rnd() < 0.55) { c.fillStyle = rgb(255, 190, 110, 0.55 + rnd() * 0.4); c.fillRect(x + w * 0.3, y - h * 0.6, 1.6 * sc, 2 * sc); }
  }
  let px = x0 + (x1 - x0) * 0.2;                              // road lamps zig-zagging up the hill
  for (let t = 0; t < 1; t += 0.035) {
    const x = px + Math.sin(t * 9 + seed) * (x1 - x0) * 0.12, y = wl - t * (wl - ridgeY(r, x) - 14 * sc);
    if (y < ridgeY(r, x) + 6 * sc) break;
    glow(c, x, y, 5 * sc, [255, 175, 90], 0.7, 0.15);
    px += (x1 - x0) * 0.004;
  }
}

export const WATER_SCENES = {
  Harbour(S, c, f, m, seed) {                                 // a fishing harbour: hillside town, boats, a lit jetty
    const { W, H } = S, wl = S.horizon * H, sc = sizeScale(S), rnd = prng(seed + 9);
    darkSky(S, c, wl, [90, 70, 64], { low: [22, 24, 40], glowH: 0.26, sunX: 0.8 });
    starry(S, c, seed, wl, { n: 0.7, milky: 0.55, angle: -0.4, cx: 0.7 });
    const hill = { base: S.horizon, amp: 0.3, rough: 1.4, sharp: 0.3, taper: u => u < 0.62 ? 1 : Math.max(0.08, 1 - (u - 0.62) / 0.25) };
    range(c, m, W, H, seed + 1, { ...hill, base: S.horizon - 0.04, amp: 0.2, rough: 2.2 }, tone(S, [30, 34, 52], 0.9), tone(S, [18, 20, 32], 0.9), 0.2, wl);
    const r = range(c, m, W, H, seed + 2, hill, tone(S, [18, 21, 32], 0.7), tone(S, [10, 11, 18], 0.7), 0.25, wl);
    hillTown(S, c, m, r, 0, W * 0.72, wl - 14 * sc, sc, seed + 3);
    townRow(S, c, m, -5 * sc, W * 0.62, wl, sc, rnd);
    streetLights(c, W * 0.62, H, wl - 1 * sc, seed + 4, sc);
    const lx = W * 0.9, ly = wl - 6 * sc;                    // headland with a lighthouse on the right
    c.fillStyle = rgb(...tone(S, [12, 13, 20], 0.6));
    c.beginPath(); c.moveTo(W * 0.8, wl); c.quadraticCurveTo(W * 0.86, ly - 4 * sc, lx, ly); c.lineTo(W + 2, ly + 2 * sc); c.lineTo(W + 2, wl); c.fill();
    m.fillStyle = mat(0.25); m.fillRect(W * 0.8, ly - 4 * sc, W * 0.2, wl - ly + 4 * sc);
    c.fillStyle = rgb(...tone(S, [70, 70, 80], 0.5)); c.beginPath();
    c.moveTo(lx - 5 * sc, ly); c.lineTo(lx - 3 * sc, ly - 44 * sc); c.lineTo(lx + 3 * sc, ly - 44 * sc); c.lineTo(lx + 5 * sc, ly); c.fill();
    c.fillStyle = rgb(160, 30, 30, 0.8); c.fillRect(lx - 4.2 * sc, ly - 30 * sc, 8.4 * sc, 5 * sc);
    c.fillStyle = rgb(255, 245, 210); c.fillRect(lx - 3 * sc, ly - 50 * sc, 6 * sc, 6 * sc);
    c.fillStyle = rgb(30, 30, 36); c.beginPath(); c.moveTo(lx - 4 * sc, ly - 50 * sc); c.lineTo(lx, ly - 55 * sc); c.lineTo(lx + 4 * sc, ly - 50 * sc); c.fill();
    glow(c, lx, ly - 47 * sc, 30 * sc, [255, 240, 200], 0.4, 0.1);
    S.lighthouse = [lx, ly - 47 * sc];
    water(c, m, W, H, wl, seed + 5, { tint: [8, 12, 24], reflect: 0.68 });
    S.water = wl;
    const jy = wl + (H - wl) * 0.42, lamps = jetty(S, c, m, -2, W * 0.4, jy, sc * 1.5, rnd);
    for (const [i, [x]] of lamps.entries()) lightReflection(c, x, jy + 5 * sc, (H - jy) * 0.7, [255, 180, 100], sc, seed + 60 + i, 0.55);
    for (let i = 0; i < 7; i++) {                             // moored boats off the town quay
      const x = W * (0.06 + i * 0.085 + rnd() * 0.03), y = wl + (H - wl) * (0.1 + rnd() * 0.12), len = (34 + rnd() * 26) * sc;
      const top = boat(c, x, y, len, sc, rnd, { sail: rnd() < 0.6, colour: tone(S, rnd() < 0.6 ? [44, 46, 56] : [16, 18, 26], 0.4) });
      lightReflection(c, x, y + 2 * sc, (H - y) * 0.45, [255, 240, 210], sc, seed + 80 + i, 0.4);
      m.fillStyle = mat(0.3); m.fillRect(x - len / 2, y + top[1], len, -top[1]);
    }
    for (let i = 0; i < 3; i++) S.boats.push([W * (0.5 + i * 0.16 + rnd() * 0.05), wl + (H - wl) * (0.3 + i * 0.16 + rnd() * 0.05), (60 + i * 22) * sc, seed + 90 + i]);
    const qy = H * 0.94;                                     // the quay in front: stone edge, bollards
    for (const k of [f, m]) {
      k.fillStyle = k === m ? mat(0.3) : rgb(...tone(S, [8, 8, 11], 0.1)); k.fillRect(0, qy, W, H - qy);
      for (let x = W * 0.07; x < W; x += W * 0.21) { k.fillRect(x - 5 * sc, qy - 12 * sc, 10 * sc, 12 * sc); k.beginPath(); k.ellipse(x, qy - 12 * sc, 7 * sc, 3 * sc, 0, 0, 6.2832); k.fill(); }
    }
    f.fillStyle = rgb(80, 80, 96, 0.4); f.fillRect(0, qy, W, 1.5 * sc);     // sky light on the quay edge
    f.fillStyle = rgb(30, 30, 38, 0.5);                       // joints between the coping stones
    for (let x = 0; x < W; x += 26 * sc) f.fillRect(x, qy, 1 * sc, H - qy);
  },

  'River Bridge'(S, c, f, m, seed) {                          // a cable-stayed bridge over a city river
    const { W, H } = S, wl = S.horizon * H, sc = sizeScale(S);
    darkSky(S, c, wl, [110, 78, 66], { low: [26, 26, 42], glowH: 0.34, sunX: 0.15 });
    starry(S, c, seed, wl, { n: 0.35, milky: 0 });
    skyline(c, m, W, H, wl, seed + 1, { far: true, S, sc });
    skyline(c, m, W, H, wl, seed + 2, { far: false, S, sc, tall: 0.45 });
    streetLights(c, W, H, wl, seed + 3, sc);
    const spec = { deck: wl - 0.07 * H, topY: wl - Math.min(0.42 * H, 0.42 * W), pylons: [0.27, 0.75], sc, seed: seed + 4, wl };
    cableBridge(S, c, m, spec);
    S.bridge = (wl - spec.deck) / H * 150 / 1.5;               // deck height (m) at ~150 m for the engine's waterfall finale
    water(c, m, W, H, wl, seed + 5, { tint: [10, 12, 24], reflect: 0.72 });
    S.water = wl;
    const beacons = S.beacons.length;
    cableBridge(S, f, m, spec);                               // again in front: shells rise behind the bridge
    S.beacons.length = beacons;
    for (const [i, p] of spec.pylons.entries()) lightReflection(c, p * W, wl + 2 * sc, (H - wl) * 0.55, [200, 220, 255], sc, seed + 40 + i, 0.3);
    const ey = H * 0.94;                                      // embankment balustrade in front
    for (const k of [f, m]) {
      k.fillStyle = k === m ? mat(0.3) : rgb(...tone(S, [7, 7, 10], 0.1));
      k.fillRect(0, ey, W, H - ey); k.fillRect(0, ey - 22 * sc, W, 4 * sc);
      for (let x = 0; x < W; x += 9 * sc) { k.beginPath(); k.ellipse(x, ey - 9 * sc, 2.4 * sc, 9 * sc, 0, 0, 6.2832); k.fill(); }
    }
    for (const x of [W * 0.12, W * 0.88]) {                  // two old lamp posts on the embankment
      for (const k of [f, m]) { k.fillStyle = k === m ? mat(0.3) : rgb(8, 8, 11); k.fillRect(x - 2 * sc, ey - 110 * sc, 4 * sc, 110 * sc); k.fillRect(x - 7 * sc, ey - 104 * sc, 14 * sc, 3 * sc); }
      f.fillStyle = rgb(255, 214, 160); f.beginPath(); f.ellipse(x, ey - 116 * sc, 5 * sc, 7 * sc, 0, 0, 6.2832); f.fill();
      glow(f, x, ey - 116 * sc, 40 * sc, [255, 190, 120], 0.35, 0.12);
    }
  },

  Waterfront(S, c, f, m, seed) {                              // big-city waterfront, New Year's Eve crowd in front
    const { W, H } = S, wl = S.horizon * H, sc = sizeScale(S), rnd = prng(seed + 7);
    darkSky(S, c, wl, [150, 96, 66], { low: [40, 30, 46], glowH: 0.48, sunX: 0.85 });
    starry(S, c, seed, wl, { n: 0.15, milky: 0 });
    skyline(c, m, W, H, wl, seed + 1, { far: true, S, sc: sc * 1.2 });
    const crowns = [[255, 232, 200], [236, 240, 255], [255, 222, 178], [245, 238, 228], null, null];   // soft whites, some unlit
    const n = Math.max(3, Math.round(W / (190 * sc)));
    for (let i = 0; i < n; i++) {                             // the tall towers with floodlit crowns
      const x = W * (i + 0.2 + rnd() * 0.6) / n, h = Math.min(Math.min(H, W * 1.1) * (0.26 + rnd() * 0.2), wl - H * 0.12), w = (34 + rnd() * 24) * sc;
      crownTower(S, c, m, x - w / 2, wl, w, h, rnd, sc, crowns[Math.floor(rnd() * crowns.length)]);
    }
    skyline(c, m, W, H, wl, seed + 2, { far: false, S, sc, tall: 1.3 });
    const fx = W * (0.78 + rnd() * 0.1), fr = Math.min(0.13 * H, 0.16 * W);
    ferrisWheel(c, m, fx, wl - fr * 1.12, fr, sc, rnd);
    streetLights(c, W, H, wl, seed + 3, sc);
    water(c, m, W, H, wl, seed + 4, { tint: [12, 12, 26], reflect: 0.78 });
    S.water = wl;
    for (const [i, [x, y]] of S.beacons.entries()) lightReflection(c, x, wl + (wl - y) * 0.8, H * 0.06, [255, 60, 40], sc, seed + i, 0.25);
    const top = H * 0.9;
    crowd(f, m, W, H, seed + 5, sc * 1.7, top);
    const g = f.createLinearGradient(0, top - 10 * sc, 0, H);  // the crowd's heads catch the city glow
    g.addColorStop(0, rgb(120, 80, 60, 0.12)); g.addColorStop(1, rgb(0, 0, 0, 0));
    f.globalCompositeOperation = 'source-atop'; f.fillStyle = g; f.fillRect(0, top - 20 * sc, W, H); f.globalCompositeOperation = 'source-over';
  },
};
