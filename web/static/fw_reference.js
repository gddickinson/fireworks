// Replays the Python reference runs (web/reference.py) in the JavaScript port and measures the differences.
// Used by the Verify page and the node tests.
import { Show } from './fw_engine.js';
import { pyRand } from './fw_rand.js';
import { PATTERN_CLASSES, RandomPattern } from './fw_patterns.js';
import { makeWeather } from './fw_weather.js';
import { BACKGROUNDS } from './fw_backgrounds.js';
import { randomColor } from './fw_color.js';

const sum = xs => xs.reduce((a, b) => a + b, 0);

function snap(fws) {
  return fws.map(fw => {
    const ps = fw.particles;
    return { x: fw.x, y: fw.y, vy: fw.velocity_y, exploded: fw.exploded, n: ps.length,
      sx: sum(ps.map(p => p.x)), sy: sum(ps.map(p => p.y)), svx: sum(ps.map(p => p.velocity_x)),
      svy: sum(ps.map(p => p.velocity_y)), life: ps.length ? ps[0].current_life : null };
  });
}

// The loop of web/reference.py run_show (= FireworksCanvas.update_animation, fixed red, no pattern).
export function runShow(c) {
  const show = new Show(c.width, c.height, { rand: pyRand(c.seed) });
  show.particle_count = c.particles;
  const snapshots = [];
  for (let step = 0; step <= c.steps; step++) {
    if (step % c.snap_every === 0) snapshots.push({ step, fireworks: snap(show.fireworks) });
    show.update();
  }
  return { snapshots };
}

// Max relative difference between two nested structures of numbers (structure must match, else Infinity).
export function maxDiff(a, b) {
  if (Array.isArray(a) || (a && typeof a === 'object')) {
    if (!b || typeof b !== 'object' || Object.keys(a).length !== Object.keys(b).length) return Infinity;
    let m = 0;
    for (const k of Object.keys(a)) m = Math.max(m, maxDiff(a[k], b[k]));
    return m;
  }
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) / Math.max(1, Math.abs(a));
  return a === b ? 0 : Infinity;
}

export function patternPoints(ref) {
  if (ref.name === 'Random') {
    const rp = new RandomPattern(pyRand(ref.seed));
    return { selected: rp.patterns.indexOf(rp.selected_pattern), points: rp.get_points(400, 300) };
  }
  return { points: PATTERN_CLASSES[ref.name](ref.kwargs).get_points(400, 300) };
}

const bolt = b => ({ segments: b.segments.map(([s, e]) => [...s, ...e]), lifetime: b.lifetime, branches: b.branches.map(bolt) });

// web/reference.py weather_runs / background_scenes / random_colors (seeds 3, 5, 9; 800 x 600).
export function weatherRuns(seed = 3, w = 800, h = 600) {
  const R = pyRand(seed), out = {};
  for (const [name, steps] of [['Rain', 40], ['Snow', 40], ['Fog', 60]]) {
    const eff = makeWeather(name, w, h, R);
    for (let i = 0; i < steps; i++) eff.update();
    out[name] = { steps, particles: eff.particles.map(p => [p.x, p.y, p.speed]),
      layers: (eff.fog_layers || []).map(L => [L.x, L.y, L.width, L.height, L.velocity, L.opacity, L.control_points]) };
  }
  const eff = makeWeather('Lightning', w, h, R), strikes = [];
  for (let step = 0; step < 600; step++) {
    eff.update();
    for (const b of eff.active_bolts) if (b.current_life === b.lifetime) strikes.push({ step, bolt: bolt(b) });
  }
  out.Lightning = { steps: 600, strikes, next_strike: eff.next_strike, flash: eff.flash_intensity };
  return out;
}

export function backgroundScenes(seed = 5, w = 800, h = 600) {
  const R = pyRand(seed), mk = n => new BACKGROUNDS[n](w, h, R);
  const ns = mk('Night Sky'), cs = mk('Cityscape'), mo = mk('Mountains'), be = mk('Beach'), fo = mk('Forest');
  return {
    'Night Sky': { stars: ns.stars }, Cityscape: { buildings: cs.buildings, windows: cs.windows },
    Mountains: { mountains: mo.mountains, stars: mo.stars },
    Beach: { stars: be.stars, waves: be.waves, palm_trees: be.palm_trees },
    Forest: { stars: fo.stars, trees: fo.trees, fireflies: fo.fireflies },
  };
}

export function randomColors(seed = 9, n = 24) {
  const R = pyRand(seed);
  return Array.from({ length: n }, () => randomColor(R));
}
