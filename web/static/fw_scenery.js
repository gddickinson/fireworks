// Realistic scenery for the realistic renderer: one function per background, painted once per size into offscreen
// canvases (seeded, so the same scene every time):
//   back  - opaque: sky, stars, Milky Way, distant terrain/skyline, water with reflections (behind the fireworks)
//   front - transparent: foreground silhouettes in front of the fireworks
//   mat   - material map (fw_scenery_parts.js): red albedo, green water, blue open sky
// plus `horizon` (fraction of the height where shells are launched, the sim's horizon) and `water` (px, or null).
import { prng, fbm1, hash } from './fw_noise.js';
import { broadleaf, conifer, mat, milkyWay, palm, range, rgb, sky, snow, stars, water } from './fw_scenery_parts.js';

const canvas = (W, H) => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };

export const SCENERY_HORIZON = { None: 0.92, 'Night Sky': 0.86, Cityscape: 0.7, Mountains: 0.76, Beach: 0.66, Forest: 0.82 };

export function buildScenery(name, W, H, seed = 7) {
  W = Math.max(2, Math.round(W)); H = Math.max(2, Math.round(H));
  const back = canvas(W, H), front = canvas(W, H), mt = canvas(W, H);
  const c = back.getContext('2d'), f = front.getContext('2d'), m = mt.getContext('2d');
  m.fillStyle = mat(0, 0, 1); m.fillRect(0, 0, W, H);
  const hz = SCENERY_HORIZON[name] ?? SCENERY_HORIZON.None;
  const S = { W, H, back, front, mat: mt, horizon: hz, water: null, fireflies: [], name };
  (PAINTERS[name] || PAINTERS.None)(S, c, f, m, seed);
  return S;
}

function darkSky(c, W, H, horizon, glow, opts = {}) {
  sky(c, W, H, { top: [1, 2, 8], mid: [4, 8, 22], low: opts.low || [12, 20, 40], glow, glowH: opts.glowH || 0.3, horizon });
}

function starry(S, c, seed, horizon, { n = 1.0, milky = 1, angle = -0.55, cx = 0.62 } = {}) {
  const { W, H } = S, rnd = prng(seed);
  const dist = milky > 0 ? milkyWay(c, W, H, seed, { horizon, angle, cx, strength: milky }) : null;
  stars(c, W, H, rnd, { n: Math.round(W * H / 260 * n), horizon, milky: dist });
}

const PAINTERS = {
  None(S, c, f, m, seed) {
    const { W, H } = S, hz = S.horizon * H;
    darkSky(c, W, H, H, [30, 34, 60], { glowH: 0.2 });
    starry(S, c, seed, H, { milky: 0.8 });
    m.fillStyle = mat(0.15); m.fillRect(0, hz, W, H - hz);
  },

  'Night Sky'(S, c, f, m, seed) {                              // open country: distant hills, a meadow, a few trees
    const { W, H } = S, hz = S.horizon * H;
    darkSky(c, W, H, hz, [46, 52, 70], { glowH: 0.22 });
    starry(S, c, seed, hz, { milky: 1.1 });
    range(c, m, W, H, seed + 1, { base: S.horizon + 0.005, amp: 0.05, rough: 2.5, sharp: 0.3 }, [26, 32, 46], [14, 18, 28], 0.25);
    range(c, m, W, H, seed + 2, { base: S.horizon + 0.03, amp: 0.035, rough: 4, sharp: 0.2 }, [12, 16, 22], [6, 8, 12], 0.3);
    const meadow = { base: 0.95, amp: 0.06, rough: 1.4, sharp: 0.1 };
    range(f, m, W, H, seed + 3, meadow, [7, 9, 10], [3, 4, 5], 0.35);
    const rnd = prng(seed + 4);
    f.fillStyle = rgb(4, 5, 6); m.fillStyle = mat(0.2);
    for (let i = 0; i < 5; i++) {
      const x = rnd() * W, y = H * (0.93 - 0.05 * fbm1(seed + 3, x / W * 1.4, 5)) + 6, h = H * (0.08 + rnd() * 0.08);
      const r2 = prng(seed + 40 + i);
      (rnd() < 0.5 ? conifer : broadleaf)(f, x, y, h, r2);
      (rnd() < 0.5 ? conifer : broadleaf)(m, x, y, h, prng(seed + 40 + i));
    }
  },

  Cityscape(S, c, f, m, seed) {                                // a harbour: skyline on the far bank, river in front
    const { W, H } = S, wl = S.horizon * H;
    darkSky(c, W, H, wl, [120, 70, 40], { low: [30, 26, 36], glowH: 0.38 });
    starry(S, c, seed, wl, { n: 0.25, milky: 0 });
    skyline(c, m, W, H, wl, seed + 1, { far: true });
    skyline(c, m, W, H, wl, seed + 2, { far: false });
    streetLights(c, W, H, wl, seed + 3);
    water(c, m, W, H, wl, seed + 4, { tint: [10, 12, 22], reflect: 0.7 });
    S.water = wl;
    f.fillStyle = rgb(3, 3, 5); f.fillRect(0, H * 0.965, W, H);   // quay edge
    m.fillStyle = mat(0.3); m.fillRect(0, H * 0.965, W, H);
  },

  Mountains(S, c, f, m, seed) {                                // alpine lake under ranges fading into haze
    const { W, H } = S, wl = S.horizon * H;
    darkSky(c, W, H, wl, [40, 50, 80], { glowH: 0.25 });
    starry(S, c, seed, wl, { milky: 1.2, angle: -0.9, cx: 0.4 });
    const haze = [[38, 44, 66], [28, 33, 52], [18, 22, 36], [10, 12, 20]];
    const specs = [{ base: 0.72, amp: 0.4, rough: 3.2, sharp: 0.85 }, { base: 0.74, amp: 0.28, rough: 4.5, sharp: 0.8 },
      { base: 0.76, amp: 0.15, rough: 6, sharp: 0.6 }];
    specs.forEach((sp, i) => {
      const top = haze[i], bot = haze[i].map(v => v * 0.55);
      const r = range(c, m, W, H, seed + 10 + i, sp, top, bot, 0.5 - i * 0.1, wl);
      if (i < 2) snow(c, m, r, H * (sp.base - sp.amp * 0.5), H * 0.06, seed + 20 + i);
    });
    treeLine(c, m, W, H, wl, seed + 30, H * 0.025, [8, 10, 14]);
    water(c, m, W, H, wl, seed + 5, { tint: [8, 12, 22], reflect: 0.6 });
    S.water = wl;
    range(f, m, W, H, seed + 6, { base: 1.0, amp: 0.06, rough: 1.5, sharp: 0.2 }, [5, 6, 8], [2, 2, 3], 0.25);
    const rnd = prng(seed + 7);
    f.fillStyle = rgb(3, 4, 5); m.fillStyle = mat(0.15);
    for (let i = 0; i < 9; i++) {
      const x = (i < 5 ? rnd() * 0.18 : 0.82 + rnd() * 0.18) * W, h = H * (0.18 + rnd() * 0.16);
      conifer(f, x, H * 1.01, h, prng(seed + 70 + i)); conifer(m, x, H * 1.01, h, prng(seed + 70 + i));
    }
  },

  Beach(S, c, f, m, seed) {                                    // the sea to the horizon, a headland, palms on the sand
    const { W, H } = S, wl = S.horizon * H;
    darkSky(c, W, H, wl, [50, 46, 70], { low: [18, 22, 44], glowH: 0.2 });
    starry(S, c, seed, wl, { milky: 1.0, angle: -0.35, cx: 0.3 });
    for (const k of [c, m]) { k.save(); k.beginPath(); k.rect(0, 0, W * 0.4, H); k.clip(); }   // headland on the left
    const head = { base: S.horizon + 0.004, amp: 0.1, rough: 1.6, sharp: 0.5, taper: u => Math.max(0, 1 - Math.pow(u / 0.4, 2)) };
    range(c, m, W, H, seed + 1, head, [18, 22, 34], [10, 12, 20], 0.25, wl + 1);
    c.restore(); m.restore();
    water(c, m, W, H, wl, seed + 2, { tint: [8, 14, 30], reflect: 0.65 });
    S.water = wl;
    surf(c, W, H, wl, seed + 3);
    const sand = { base: 1.0, amp: 0.12, rough: 0.7, sharp: 0.0 };
    range(f, m, W, H, seed + 4, sand, [26, 22, 22], [10, 9, 10], 0.55);
    const rnd = prng(seed + 5);
    f.strokeStyle = rgb(4, 4, 6); m.strokeStyle = mat(0.15);
    for (let i = 0; i < 3; i++) {
      const x = (i === 0 ? 0.05 + rnd() * 0.12 : i === 1 ? 0.8 + rnd() * 0.15 : 0.18 + rnd() * 0.1) * W;
      const h = H * (0.38 + rnd() * 0.2), lean = (x < W / 2 ? 1 : -1) * (0.3 + rnd() * 0.4);
      palm(f, x, H * 1.02, h, lean, prng(seed + 50 + i)); palm(m, x, H * 1.02, h, lean, prng(seed + 50 + i));
    }
  },

  Forest(S, c, f, m, seed) {                                   // a clearing in a conifer forest, fireflies
    const { W, H } = S, hz = S.horizon * H;
    darkSky(c, W, H, hz, [36, 44, 60], { glowH: 0.2 });
    starry(S, c, seed, hz, { milky: 1.2, angle: -0.7, cx: 0.55 });
    treeLine(c, m, W, H, hz - H * 0.02, seed + 1, H * 0.06, [26, 32, 44]);
    treeLine(c, m, W, H, hz, seed + 2, H * 0.08, [14, 18, 24]);
    treeLine(c, m, W, H, hz + H * 0.03, seed + 3, H * 0.1, [6, 8, 10]);
    c.fillStyle = rgb(4, 6, 6); c.fillRect(0, hz + H * 0.03, W, H); m.fillStyle = mat(0.25); m.fillRect(0, hz + H * 0.03, W, H);
    const rnd = prng(seed + 4);
    f.fillStyle = rgb(2, 3, 3); m.fillStyle = mat(0.12);
    for (let i = 0; i < 10; i++) {
      const side = i % 2 ? rnd() * 0.12 : 0.88 + rnd() * 0.12, x = side * W, h = H * (0.3 + rnd() * 0.35);
      conifer(f, x, H * 1.02, h, prng(seed + 60 + i)); conifer(m, x, H * 1.02, h, prng(seed + 60 + i));
    }
    for (let i = 0; i < Math.round(W / 60); i++) {
      S.fireflies.push([rnd(), S.horizon + 0.04 + rnd() * 0.12, rnd() * 6.28, 0.5 + rnd()]);  // fractions of W, H
    }
  },
};

function treeLine(c, m, W, H, y, seed, h, col) {
  const rnd = prng(seed), n = Math.round(W / (h * 0.22));
  c.fillStyle = rgb(...col); m.fillStyle = mat(0.2);
  c.fillRect(0, y - h * 0.15, W, h * 0.2); m.fillRect(0, y - h * 0.15, W, h * 0.2);
  for (let i = 0; i < n; i++) {
    const x = (i + rnd()) * W / n, th = h * (0.5 + rnd() * 0.7) * (0.7 + 0.6 * fbm1(seed, x / W * 3, 3));
    const s = seed * 1000 + i;
    conifer(c, x, y + 1, th, prng(s)); conifer(m, x, y + 1, th, prng(s));
  }
}

// City skyline standing on the far bank at wl. Far: lower, hazier, tiny windows. Near: towers with roof details.
function skyline(c, m, W, H, wl, seed, { far }) {
  const rnd = prng(seed), sc = H / 800;
  const centre = 0.3 + rnd() * 0.4;
  let x = -rnd() * 30 * sc;
  while (x < W) {
    const w = (far ? 14 + rnd() * 30 : 22 + rnd() * 48) * sc;
    const d = (x / W - centre) / 0.28, cluster = Math.exp(-d * d);
    let h = (far ? 30 + rnd() * 50 + 90 * cluster * rnd() : 24 + rnd() * 50 + 170 * cluster * Math.pow(rnd(), 0.7)) * sc;
    if (!far && rnd() < 0.12) h *= 0.35;
    building(c, m, x, wl, w, h, rnd, far, sc);
    x += w + (rnd() < 0.2 ? rnd() * 8 * sc : 0);
  }
}

function building(c, m, x, base, w, h, rnd, far, sc) {
  const top = base - h, col = far ? [24, 24, 36] : [9, 10, 16];
  const g = c.createLinearGradient(0, top, 0, base);
  g.addColorStop(0, rgb(...col.map(v => v * 1.25))); g.addColorStop(1, rgb(...col));
  c.fillStyle = g; c.fillRect(x, top, w, h);
  m.fillStyle = mat(far ? 0.25 : 0.35); m.fillRect(x, top, w, h);
  let roof = top;
  const r = rnd();                                            // roof details
  c.fillStyle = rgb(...col);
  if (!far && r < 0.3 && h > 120 * sc) {                      // setbacks
    const w2 = w * 0.7, h2 = h * 0.12; c.fillRect(x + (w - w2) / 2, top - h2, w2, h2);
    const w3 = w * 0.4, h3 = h * 0.08; c.fillRect(x + (w - w3) / 2, top - h2 - h3, w3, h3);
    m.fillRect(x + (w - w2) / 2, top - h2, w2, h2); roof = top - h2 - h3;
  } else if (!far && r < 0.45 && h > 150 * sc) {               // spire
    c.beginPath(); c.moveTo(x + w * 0.3, top); c.lineTo(x + w / 2, top - h * 0.22); c.lineTo(x + w * 0.7, top); c.fill();
    roof = top - h * 0.22;
  } else if (r < 0.65) {                                      // plant room / water tank
    c.fillRect(x + w * (0.1 + rnd() * 0.4), top - 6 * sc, w * 0.3, 6 * sc);
  }
  if (!far && (r > 0.85 || h > 220 * sc)) {                  // antenna with a red aviation light
    c.fillStyle = rgb(20, 20, 26); c.fillRect(x + w / 2 - sc * 0.6, roof - 26 * sc, 1.2 * sc, 26 * sc);
    c.fillStyle = rgb(255, 40, 30, 0.9); c.beginPath(); c.arc(x + w / 2, roof - 26 * sc, 1.6 * sc, 0, 6.28); c.fill();
    const gl = c.createRadialGradient(x + w / 2, roof - 26 * sc, 0, x + w / 2, roof - 26 * sc, 9 * sc);
    gl.addColorStop(0, rgb(255, 40, 30, 0.35)); gl.addColorStop(1, rgb(255, 40, 30, 0));
    c.fillStyle = gl; c.fillRect(x + w / 2 - 9 * sc, roof - 35 * sc, 18 * sc, 18 * sc);
  }
  const cw = (far ? 2.2 : 3.2) * sc, chh = (far ? 3.2 : 4.4) * sc, lit = 0.06 + rnd() * (far ? 0.2 : 0.32);
  const warm = rnd() < 0.7, floorLit = rnd() < 0.3;
  for (let fy = top + chh; fy < base - chh * 1.5; fy += chh * 1.6) {
    const wholeFloor = floorLit && rnd() < 0.15;
    for (let fx = x + cw * 0.7; fx < x + w - cw * 1.2; fx += cw * 1.7) {
      if (!(wholeFloor || rnd() < lit)) continue;
      const t = warm ? (rnd() < 0.85 ? [255, 196, 120] : [190, 215, 255]) : (rnd() < 0.7 ? [200, 225, 255] : [255, 210, 150]);
      c.fillStyle = rgb(...t, (far ? 0.35 : 0.55) + rnd() * 0.4);
      c.fillRect(fx, fy, cw, chh * 0.75);
    }
  }
}

function streetLights(c, W, H, wl, seed) {
  const rnd = prng(seed), sc = H / 800;
  for (let x = rnd() * 20 * sc; x < W; x += (14 + rnd() * 18) * sc) {
    const y = wl - (2 + rnd() * 3) * sc, r = (6 + rnd() * 6) * sc, col = rnd() < 0.75 ? [255, 170, 80] : [220, 235, 255];
    const g = c.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgb(...col, 0.9)); g.addColorStop(0.15, rgb(...col, 0.35)); g.addColorStop(1, rgb(...col, 0));
    c.fillStyle = g; c.fillRect(x - r, y - r, 2 * r, 2 * r);
  }
}

function surf(c, W, H, wl, seed) {                           // faint foam lines catching the sky light
  const sc = H / 800;
  for (let i = 0; i < 6; i++) {
    const y = wl + (H - wl) * (0.25 + i * 0.13), a = 0.05 + i * 0.015;
    c.strokeStyle = rgb(160, 175, 210, a); c.lineWidth = (1 + i * 0.5) * sc; c.beginPath();
    for (let x = 0; x <= W; x += 8) c.lineTo(x, y + Math.sin(x / (60 * sc) + i * 1.7) * 3 * sc + (hash(seed, x, i) - 0.5) * 2 * sc);
    c.stroke();
  }
}
