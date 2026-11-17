// Land scenes of the realistic scenery (registered in fw_scenery.js): desert dunes under a clear Milky Way, a snowy
// village, a floodlit castle on a hill, and countryside with fields, a church spire and wind turbines. Shells launch
// from behind the village / hill / far ridge (the front layer hides the launch points).
// Painter signature: (S, c, f, m, seed) with c/f/m the back/front/material contexts (see fw_scenery.js).
import { fbm1, prng } from './fw_noise.js';
import { broadleaf, conifer, fillRidge, mat, range, rgb } from './fw_scenery_parts.js';
import { darkSky, starry, tone } from './fw_scenery_sky.js';
import { glow } from './fw_scenery_city.js';
import { dunes, fields, hillLine, mesaLine, oak, ridgeY, sizeScale, snowyConifer, treeLine } from './fw_scenery_props.js';
import { castle, church, cottage, tent, turbine } from './fw_scenery_houses.js';

// Small houses with lit windows scattered over a band (y0..y1 px) – distant village / town lights.
function lights(S, c, x0, x1, y0, y1, n, sc, seed, ground = null) {
  const rnd = prng(seed);
  for (let i = 0; i < n; i++) {
    const x = x0 + rnd() * (x1 - x0), y = ground ? Math.max(ground(x) + 3 * sc, y0 + rnd() * (y1 - y0)) : y0 + rnd() * (y1 - y0);
    c.fillStyle = rgb(...tone(S, [14, 14, 20], 0.5)); c.fillRect(x - 3 * sc, y - 4 * sc, 7 * sc, 4 * sc);
    if (rnd() < 0.7) { c.fillStyle = rgb(255, 185 + rnd() * 30, 110, 0.6 + rnd() * 0.35); c.fillRect(x, y - 2.8 * sc, 1.5 * sc, 1.8 * sc); }
    if (rnd() < 0.08) glow(c, x, y - 2 * sc, 7 * sc, [255, 170, 90], 0.5);
  }
}

export const LAND_SCENES = {
  Desert(S, c, f, m, seed) {                                  // dunes and mesas under a clear, dark sky
    const { W, H } = S, hz = S.horizon * H, sc = sizeScale(S);
    darkSky(S, c, hz, [40, 36, 52], { low: [16, 18, 34], glowH: 0.14, sunX: 0.75 });
    starry(S, c, seed, hz, { n: 1.5, milky: 1.6, angle: -1.15, cx: 0.48 });
    const mesa = mesaLine(W, H, seed + 1, { base: S.horizon + 0.004, amp: 0.13, rough: 2.2 });
    const g = c.createLinearGradient(0, H * (S.horizon - 0.13), 0, hz);
    g.addColorStop(0, rgb(...tone(S, [44, 38, 50], 0.9))); g.addColorStop(1, rgb(...tone(S, [20, 18, 28], 0.9)));
    fillRidge(c, W, H, mesa, g); fillRidge(m, W, H, mesa, mat(0.3));
    dunes(c, m, W, H, seed + 2, { base: S.horizon + 0.03, amp: 0.05, waves: 4.5, lit: tone(S, [40, 34, 38], 0.7), shade: tone(S, [16, 15, 22], 0.7) });
    const mid = dunes(f, m, W, H, seed + 4, { base: S.horizon + 0.1, amp: 0.1, waves: 2.5, lit: tone(S, [50, 40, 40], 0.4), shade: tone(S, [12, 11, 15], 0.4), albedo: 0.55 });
    let tx = W * (0.3 + prng(seed + 3)() * 0.4), ty = ridgeY(mid, tx);
    for (let x = tx - 60 * sc; x < tx + 60 * sc; x += 3) if (ridgeY(mid, x) > ty) { ty = ridgeY(mid, x); tx = x; }   // in a hollow
    tent(f, m, tx, ty + 3 * sc, sc * 1.5);
    const near = dunes(f, m, W, H, seed + 5, { base: 1.02, amp: 0.13, waves: 1.6, lit: tone(S, [42, 34, 34], 0.2), shade: tone(S, [8, 7, 10], 0.2), albedo: 0.6 });
    const rnd = prng(seed + 6);                               // shrubs and a few rocks on the near dune
    for (let i = 0; i < 9; i++) {
      const x = rnd() * W, y = ridgeY(near, x) + (4 + rnd() * 30) * sc;
      f.fillStyle = rgb(6, 6, 8); m.fillStyle = mat(0.3);
      if (rnd() < 0.6) for (const k of [f, m]) for (let j = 0; j < 9; j++) {
        const a = -Math.PI * (0.15 + 0.7 * j / 8), l = (6 + rnd() * 9) * sc;
        k.beginPath(); k.moveTo(x, y); k.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); k.lineWidth = 1.2 * sc; k.strokeStyle = k.fillStyle; k.stroke();
      }
      else for (const k of [f, m]) { k.beginPath(); k.ellipse(x, y, (6 + rnd() * 8) * sc, (3 + rnd() * 4) * sc, 0, Math.PI, 0); k.fill(); }
    }
  },

  'Snowy Village'(S, c, f, m, seed) {                          // cottages in snow, a church, smoking chimneys
    const { W, H } = S, hz = S.horizon * H, sc = sizeScale(S), snowC = tone(S, [92, 100, 128], 0.3);
    darkSky(S, c, hz, [60, 62, 84], { low: [22, 28, 50], glowH: 0.22 });
    starry(S, c, seed, hz, { n: 0.9, milky: 0.9, angle: -0.6, cx: 0.7 });
    range(c, m, W, H, seed + 1, { base: S.horizon - 0.03, amp: 0.16, rough: 2.6, sharp: 0.55 }, tone(S, [74, 82, 110], 0.9), tone(S, [36, 42, 64], 0.9), 0.75, hz);
    treeLine(c, m, W, H, hz - H * 0.01, seed + 2, H * 0.035, tone(S, [16, 20, 30], 0.8));
    const ground = { base: S.horizon + 0.005, amp: 0.025, rough: 1.5, sharp: 0.1 };
    range(c, m, W, H, seed + 3, ground, tone(S, [64, 70, 96], 0.6), tone(S, [40, 46, 68], 0.6), 0.8);
    const rnd = prng(seed + 4);
    const slope = { base: 0.9, amp: 0.07, rough: 1.2, sharp: 0.1 };   // village slope in front (hides the launch line)
    const back = range(f, m, W, H, seed + 5, { ...slope, base: S.horizon + 0.06, amp: 0.04 }, tone(S, [62, 68, 94], 0.4), tone(S, [44, 50, 72], 0.4), 0.8);
    const cx = W * (0.45 + rnd() * 0.15);
    for (let x = rnd() * 30 * sc; x < W; x += (46 + rnd() * 40) * sc) {   // back row of cottages along the slope
      if (Math.abs(x - cx) < 80 * sc) continue;
      const w = (26 + rnd() * 14) * sc;
      cottage(S, f, m, x, ridgeY(back, x + w / 2) + 3 * sc, w, (12 + rnd() * 5) * sc, rnd, sc, { snow: true, spill: 10 * sc, haze: 0.4 });
    }
    church(S, f, m, cx, ridgeY(back, cx) + 4 * sc, sc * 1.1, rnd, { snow: true, haze: 0.4 });
    const front = range(f, m, W, H, seed + 6, slope, tone(S, [70, 76, 102], 0.2), tone(S, [30, 34, 52], 0.2), 0.85);
    for (let i = 0; i < 4; i++) {                             // front row: bigger cottages
      const x = W * (0.06 + i * 0.25 + rnd() * 0.08), w = (48 + rnd() * 20) * sc;
      cottage(S, f, m, x, ridgeY(front, x + w / 2) + 4 * sc, w, (22 + rnd() * 8) * sc, rnd, sc, { snow: true, spill: 22 * sc, haze: 0.1 });
    }
    for (let i = 0; i < 8; i++) {                             // snow-laden conifers at the sides
      const x = (i % 2 ? rnd() * 0.12 : 0.88 + rnd() * 0.12) * W, h = H * (0.16 + rnd() * 0.16);
      snowyConifer(f, m, x, H * 1.01, h, seed + 70 + i, tone(S, [6, 8, 12], 0.1), snowC);
    }
    for (let i = 0; i < 6; i++) {                             // lamp posts along the lane
      const x = W * (0.1 + i * 0.16 + rnd() * 0.04), y = ridgeY(front, x) + 26 * sc;
      f.fillStyle = rgb(8, 8, 12); f.fillRect(x - 0.8 * sc, y - 26 * sc, 1.6 * sc, 26 * sc);
      glow(f, x, y - 27 * sc, 20 * sc, [255, 190, 120], 0.5, 0.1); glow(f, x, y, 26 * sc, [255, 190, 120], 0.12, 0.3);
    }
  },

  Castle(S, c, f, m, seed) {                                  // a floodlit castle on a hill above a small town
    const { W, H } = S, hz = S.horizon * H, sc = sizeScale(S), rnd = prng(seed + 5);
    darkSky(S, c, hz, [64, 52, 64], { low: [20, 22, 40], glowH: 0.26, sunX: 0.85 });
    starry(S, c, seed, hz, { n: 0.9, milky: 0.9, angle: -0.35, cx: 0.78 });
    range(c, m, W, H, seed + 1, { base: S.horizon + 0.004, amp: 0.1, rough: 2.2, sharp: 0.5 }, tone(S, [28, 32, 48], 0.9), tone(S, [16, 18, 28], 0.9), 0.25);
    range(c, m, W, H, seed + 2, { base: S.horizon + 0.03, amp: 0.05, rough: 3.5, sharp: 0.4 }, tone(S, [14, 16, 24], 0.8), tone(S, [8, 9, 14], 0.8), 0.3);
    const cxf = 0.36 + rnd() * 0.12, peak = Math.min(0.3, 0.2 + 0.06 * W / H);
    const hill = hillLine(W, H, seed + 3, { base: 1.0, amp: 1.0 - (S.horizon - peak), cx: cxf, width: 0.42 });
    const hg = f.createLinearGradient(0, H * (S.horizon - peak), 0, H);
    hg.addColorStop(0, rgb(...tone(S, [30, 26, 26], 0.3))); hg.addColorStop(0.35, rgb(...tone(S, [14, 14, 18], 0.3))); hg.addColorStop(1, rgb(5, 5, 7));
    fillRidge(f, W, H, hill, hg); fillRidge(m, W, H, hill, mat(0.3));
    const cx = W * cxf, base = ridgeY(hill, cx) + 6 * sc;
    f.save(); f.beginPath(); f.moveTo(0, H); hill.ys.forEach((y, i) => f.lineTo(i * hill.step, y)); f.lineTo(W, H); f.clip();
    glow(f, cx, base, 160 * sc, [255, 160, 90], 0.22, 0.2);   // floodlight spill on the summit
    const rk = prng(seed + 8);                                // rocky outcrops catching the light
    for (let i = 0; i < 60; i++) {
      const x = cx + (rk() - 0.5) * W * 0.5, y = ridgeY(hill, x) + rk() * (H - ridgeY(hill, x)) * 0.6, w = (6 + rk() * 18) * sc;
      f.fillStyle = rgb(...tone(S, [34, 30, 30], 0.3), 0.25 + rk() * 0.25); f.beginPath(); f.moveTo(x, y); f.lineTo(x + w, y + w * 0.25); f.lineTo(x + w * 0.3, y + w * 0.4); f.fill();
    }
    f.restore();
    for (let i = 0; i < 40; i++) {                            // trees on the flanks
      const x = cx + (rnd() < 0.5 ? -1 : 1) * (0.08 + rnd() * 0.4) * W, y = ridgeY(hill, x) + (4 + rnd() * 60) * sc, h = (16 + rnd() * 22) * sc;
      const tree = rnd() < 0.6 ? broadleaf : conifer;
      f.fillStyle = rgb(...tone(S, [6, 6, 8], 0.2)); m.fillStyle = mat(0.25);
      tree(f, x, y, h, prng(seed + 100 + i)); tree(m, x, y, h, prng(seed + 100 + i));
    }
    castle(S, f, m, cx, base, sc * 1.05, rnd);
    const town = x => ridgeY(hill, x);                        // town lights at the foot of the hill
    lights(S, f, 0, W, H * 0.9, H * 1.0, Math.round(W / (9 * sc)), sc, seed + 7, town);
    for (let t = 0; t < 1; t += 0.06) {                       // lamps on the road winding up to the gate
      const x = cx + Math.sin(t * 7) * 60 * sc * (1 - t) + 30 * sc * (1 - t), y = H * 0.98 - t * (H * 0.98 - base - 4 * sc);
      if (y < ridgeY(hill, x)) continue;
      glow(f, x, y, 6 * sc, [255, 180, 100], 0.7, 0.15);
    }
  },

  Countryside(S, c, f, m, seed) {                             // farmland, a church spire, wind turbines on the ridge
    const { W, H } = S, hz = S.horizon * H, sc = sizeScale(S), rnd = prng(seed + 9);
    darkSky(S, c, hz, [50, 52, 72], { low: [18, 22, 40], glowH: 0.22, sunX: 0.3 });
    starry(S, c, seed, hz, { n: 1.1, milky: 1.1, angle: -0.75, cx: 0.32 });
    const far = range(c, m, W, H, seed + 1, { base: S.horizon - 0.02, amp: 0.07, rough: 1.6, sharp: 0.2 }, tone(S, [28, 32, 46], 0.9), tone(S, [18, 21, 32], 0.9), 0.25, hz + H * 0.02);
    for (let i = 0, x = W * (0.05 + rnd() * 0.1); x < W; i++, x += W * (0.09 + rnd() * 0.08)) {
      turbine(S, c, m, x, ridgeY(far, x) + 2 * sc, (52 + rnd() * 18) * sc, sc);
    }
    lights(S, c, 0, W, hz - H * 0.005, hz + H * 0.01, Math.round(W / (40 * sc)), sc * 0.7, seed + 2);
    const mid = range(c, m, W, H, seed + 3, { base: S.horizon + 0.02, amp: 0.05, rough: 1.4, sharp: 0.15 }, tone(S, [20, 24, 30], 0.6), tone(S, [12, 15, 18], 0.6), 0.3);
    fields(c, m, W, H, mid, seed + 4, { depth: H * 0.09, rows: 3, col: tone(S, [26, 30, 34], 0.6), sc });
    const cxp = W * (0.45 + rnd() * 0.15), farm = W * (0.15 + rnd() * 0.12);
    church(S, c, m, cxp, ridgeY(mid, cxp + 35 * sc) + 10 * sc, sc * 0.7, rnd, { haze: 0.6 });
    for (let i = 0; i < 3; i++) {
      const x = farm + i * 32 * sc;
      cottage(S, c, m, x, ridgeY(mid, x + 12 * sc) + 14 * sc, (22 + rnd() * 10) * sc, (10 + rnd() * 4) * sc, rnd, sc * 0.8, { haze: 0.6 });
    }
    S.chimneys.length = 0;
    const near = range(f, m, W, H, seed + 5, { base: 0.98, amp: 0.1, rough: 1.1, sharp: 0.1 }, tone(S, [14, 16, 18], 0.2), tone(S, [5, 6, 7], 0.2), 0.35);
    for (let x = rnd() * 20 * sc; x < W; x += 34 * sc) {        // fence posts and wire along the near meadow
      const y = ridgeY(near, x) + 26 * sc;
      for (const k of [f, m]) { k.fillStyle = k === m ? mat(0.3) : rgb(5, 5, 7); k.fillRect(x - 1.6 * sc, y - 24 * sc, 3.2 * sc, 24 * sc); }
    }
    f.strokeStyle = rgb(30, 32, 40, 0.6); f.lineWidth = 0.6 * sc;
    for (const d of [17, 8]) { f.beginPath(); for (let x = 0; x <= W; x += 6) f.lineTo(x, ridgeY(near, x) + 26 * sc - d * sc + fbm1(seed, x * 0.02, 2) * 2 * sc); f.stroke(); }
    const ox = W * 0.94;                                      // a big oak at the side
    f.fillStyle = rgb(4, 5, 6); m.fillStyle = mat(0.2);
    oak(f, ox, H * 1.02, H * 0.5, prng(seed + 11)); oak(m, ox, H * 1.02, H * 0.5, prng(seed + 11));
  },
};
