// Python-`random`-shaped wrapper around the seeded mulberry32 generator of core.js (rng). The Python reference runs
// (web/reference.py, class PyRand) use the identical stream and the same four methods, so a seeded JS run consumes
// exactly the random numbers the Python models consumed.
import { rng } from './core.js';

export function pyRand(seed = randomSeed()) {
  const r = rng(seed);
  return {
    seed,
    random: r,
    uniform: (a, b) => a + (b - a) * r(),                     // CPython random.uniform
    randint: (a, b) => a + Math.floor(r() * (b - a + 1)),
    choice: seq => seq[Math.floor(r() * seq.length)],
  };
}

export const randomSeed = () => Math.floor(Math.random() * 4294967296);
