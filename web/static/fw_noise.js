// Seeded value noise for the scenery (ridgelines, clouds of the Milky Way, foliage edges). Deterministic: the same
// seed always paints the same scene. hash() is an integer hash; noise1/noise2 interpolate it smoothly; fbm sums
// octaves; ridged() gives sharp mountain crests.
export function hash(seed, x, y = 0) {
  let h = (seed ^ Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263)) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
const fade = t => t * t * (3 - 2 * t);

export function noise1(seed, x) {
  const i = Math.floor(x), f = x - i;
  return hash(seed, i) + (hash(seed, i + 1) - hash(seed, i)) * fade(f);
}

export function noise2(seed, x, y) {
  const i = Math.floor(x), j = Math.floor(y), fx = fade(x - i), fy = fade(y - j);
  const a = hash(seed, i, j), b = hash(seed, i + 1, j), c = hash(seed, i, j + 1), d = hash(seed, i + 1, j + 1);
  return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
}

export function fbm1(seed, x, oct = 5, gain = 0.5) {
  let s = 0, a = 1, f = 1, n = 0;
  for (let o = 0; o < oct; o++) { s += a * noise1(seed + o * 101, x * f); n += a; a *= gain; f *= 2.03; }
  return s / n;
}

export function fbm2(seed, x, y, oct = 5, gain = 0.5) {
  let s = 0, a = 1, f = 1, n = 0;
  for (let o = 0; o < oct; o++) { s += a * noise2(seed + o * 131, x * f, y * f); n += a; a *= gain; f *= 2.01; }
  return s / n;
}

// Ridged multifractal (1-D): sharp peaks like eroded mountain crests, 0..1.
export function ridged1(seed, x, oct = 6) {
  let s = 0, a = 0.5, f = 1, w = 1, n = 0;
  for (let o = 0; o < oct; o++) {
    let v = 1 - Math.abs(noise1(seed + o * 71, x * f) * 2 - 1);
    v *= v * w; w = Math.min(1, v * 2);
    s += v * a; n += a; a *= 0.5; f *= 2.1;
  }
  return s / n;
}

// Seeded uniform generator (mulberry32) for placing things.
export function prng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
