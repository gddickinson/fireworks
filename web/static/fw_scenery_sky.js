// Skies of the realistic scenery (fw_scenery.js and the scene modules), aware of the time of day (S.time):
//   night (default) - near-black zenith, airglow, light pollution `glow` over the horizon, stars and Milky Way
//   dusk            - the blue hour: deep blue zenith, paler blue lower down, a warm afterglow band over the horizon
//                     (strongest on the sunset side), the light-pollution glow on top, only the brightest stars,
//                     no Milky Way; terrain colours lifted a little by the sky light (tone()).
// Night output is exactly what the original painters drew (the desktop port, effects/scenery.py, matches it).
import { prng } from './fw_noise.js';
import { milkyWay, rgb, sky, stars } from './fw_scenery_parts.js';

export const isDusk = S => S.time === 'dusk';

// Sky gradient from the top of the frame to `horizon` (px), glow: light-pollution colour or null.
export function darkSky(S, c, horizon, glow, opts = {}) {
  const { W, H } = S;
  if (!isDusk(S)) {
    sky(c, W, H, { top: [1, 2, 8], mid: [4, 8, 22], low: opts.low || [12, 20, 40], glow, glowH: opts.glowH || 0.3, horizon });
    return;
  }
  const g = c.createLinearGradient(0, 0, 0, horizon);      // blue hour
  g.addColorStop(0, rgb(6, 13, 40)); g.addColorStop(0.45, rgb(16, 32, 78)); g.addColorStop(0.8, rgb(44, 62, 118));
  g.addColorStop(1, rgb(92, 96, 140));
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  const sx = W * (opts.sunX ?? 0.22);                         // afterglow: warm, wide, low, centred on the sunset side
  const band = H * 0.2;
  for (const [col, a, h, wr] of [[[255, 150, 90], 0.55, band, 1.1], [[250, 120, 80], 0.5, band * 0.45, 0.6]]) {
    const vg = c.createLinearGradient(0, horizon - h, 0, horizon);
    vg.addColorStop(0, rgb(...col, 0)); vg.addColorStop(0.65, rgb(...col, a * 0.45)); vg.addColorStop(1, rgb(...col, a));
    const off = document.createElement('canvas'); off.width = W; off.height = Math.max(1, Math.ceil(h));
    const o = off.getContext('2d');
    o.translate(0, -(horizon - h)); o.fillStyle = vg; o.fillRect(0, horizon - h, W, h);
    const hg = o.createLinearGradient(0, 0, W, 0);           // fades away from the sunset side
    for (let i = 0; i <= 8; i++) { const x = i / 8, d = (x * W - sx) / (W * wr); hg.addColorStop(x, rgb(0, 0, 0, Math.max(0.25, Math.exp(-d * d)))); }
    o.globalCompositeOperation = 'destination-in'; o.fillStyle = hg; o.fillRect(0, horizon - h, W, h);
    c.drawImage(off, 0, horizon - h);
  }
  if (glow) {                                                 // town light still adds its own colour near the horizon
    const gg = c.createLinearGradient(0, horizon - H * 0.12, 0, horizon);
    gg.addColorStop(0, rgb(...glow, 0)); gg.addColorStop(1, rgb(...glow, 0.25));
    c.fillStyle = gg; c.fillRect(0, horizon - H * 0.12, W, H * 0.12);
  }
}

export function starry(S, c, seed, horizon, { n = 1.0, milky = 1, angle = -0.55, cx = 0.62 } = {}) {
  const { W, H } = S, rnd = prng(seed);
  if (isDusk(S)) {                                            // a few of the brightest stars and planets only
    stars(c, W, H, rnd, { n: Math.round(W * H / 260 * n * 0.1), horizon: horizon * 0.75, dim: 0.75 });
    return;
  }
  const dist = milky > 0 ? milkyWay(c, W, H, seed, { horizon, angle, cx, strength: milky }) : null;
  stars(c, W, H, rnd, { n: Math.round(W * H / 260 * n), horizon, milky: dist });
}

// Terrain/building colour at the time of day: at dusk the sky light lifts and blues the shadows (aerial perspective).
// `haze` 0 (foreground) .. 1 (far away).
export function tone(S, col, haze = 0.5) {
  if (!isDusk(S)) return col;
  const k = 1.35 + haze * 0.9, add = [6, 10, 26].map(v => v * (0.4 + haze));
  return col.map((v, i) => Math.min(255, v * k + add[i]));
}
