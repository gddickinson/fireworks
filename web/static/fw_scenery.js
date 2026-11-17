// Realistic scenery for the realistic renderer: one function per background, painted once per size into offscreen
// canvases (seeded, so the same scene every time):
//   back  - opaque: sky, stars, Milky Way, distant terrain/skyline, water with reflections (behind the fireworks)
//   front - transparent: foreground silhouettes in front of the fireworks
//   mat   - material map (fw_scenery_parts.js): red albedo, green water, blue open sky
// plus `horizon` (fraction of the height where shells are launched, the sim's horizon) and `water` (px, or null).
import { prng, fbm1 } from './fw_noise.js';
import { broadleaf, conifer, mat, palm, range, rgb, snow, water } from './fw_scenery_parts.js';
import { darkSky, starry } from './fw_scenery_sky.js';
import { skyline, streetLights } from './fw_scenery_city.js';
import { surf, treeLine } from './fw_scenery_props.js';
import { WATER_SCENES } from './fw_scenery_more.js';
import { LAND_SCENES } from './fw_scenery_land.js';

const canvas = (W, H) => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };

// Launch horizon (fraction of the height) per scene: shells rise from the waterline or from behind the skyline.
export const SCENERY_HORIZON = { None: 0.92, 'Night Sky': 0.86, Cityscape: 0.7, Mountains: 0.76, Beach: 0.66, Forest: 0.82,
  Harbour: 0.72, 'River Bridge': 0.74, Waterfront: 0.7, Desert: 0.8, 'Snowy Village': 0.76, Castle: 0.8, Countryside: 0.8 };

// opts.time: "night" (default) | "dusk" (blue hour). Returns S: { W, H, back, front, mat, horizon, water (px or null),
// fireflies (fractions), chimneys / beacons / boats / turbines / lighthouse (device px, for the scene plug-ins in
// fw_scene_fx.js), bridge (deck height in m, River Bridge: the engine's waterfall finale), name, time }.
export function buildScenery(name, W, H, seed = 7, opts = {}) {
  W = Math.max(2, Math.round(W)); H = Math.max(2, Math.round(H));
  const back = canvas(W, H), front = canvas(W, H), mt = canvas(W, H);
  const c = back.getContext('2d'), f = front.getContext('2d'), m = mt.getContext('2d');
  m.fillStyle = mat(0, 0, 1); m.fillRect(0, 0, W, H);
  const hz = SCENERY_HORIZON[name] ?? SCENERY_HORIZON.None;
  const S = { W, H, back, front, mat: mt, horizon: hz, water: null, fireflies: [], chimneys: [], beacons: [], boats: [], turbines: [], name,
    time: opts.time === 'dusk' ? 'dusk' : 'night' };
  (PAINTERS[name] || PAINTERS.None)(S, c, f, m, seed);
  return S;
}

export const PAINTERS = {                                     // scene name -> painter (S, c, f, m, seed)
  None(S, c, f, m, seed) {
    const { W, H } = S, hz = S.horizon * H;
    darkSky(S, c, H, [30, 34, 60], { glowH: 0.2 });
    starry(S, c, seed, H, { milky: 0.8 });
    m.fillStyle = mat(0.15); m.fillRect(0, hz, W, H - hz);
  },

  'Night Sky'(S, c, f, m, seed) {                              // open country: distant hills, a meadow, a few trees
    const { W, H } = S, hz = S.horizon * H;
    darkSky(S, c, hz, [46, 52, 70], { glowH: 0.22 });
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
    darkSky(S, c, wl, [120, 70, 40], { low: [30, 26, 36], glowH: 0.38 });
    starry(S, c, seed, wl, { n: 0.25, milky: 0 });
    skyline(c, m, W, H, wl, seed + 1, { far: true, S });
    skyline(c, m, W, H, wl, seed + 2, { far: false, S });
    streetLights(c, W, H, wl, seed + 3);
    water(c, m, W, H, wl, seed + 4, { tint: [10, 12, 22], reflect: 0.7 });
    S.water = wl;
    f.fillStyle = rgb(3, 3, 5); f.fillRect(0, H * 0.965, W, H);   // quay edge
    m.fillStyle = mat(0.3); m.fillRect(0, H * 0.965, W, H);
  },

  Mountains(S, c, f, m, seed) {                                // alpine lake under ranges fading into haze
    const { W, H } = S, wl = S.horizon * H;
    darkSky(S, c, wl, [40, 50, 80], { glowH: 0.25 });
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
    darkSky(S, c, wl, [50, 46, 70], { low: [18, 22, 44], glowH: 0.2 });
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
    darkSky(S, c, hz, [36, 44, 60], { glowH: 0.2 });
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
  ...WATER_SCENES,
  ...LAND_SCENES,
};
