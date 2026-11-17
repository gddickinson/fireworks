// node fw_wx.test.mjs: the realistic weather plug-ins (fw_wx_*.js) without a DOM: only update() runs (drawing needs
// canvases). Each registered weather is deterministic for a seed, keeps its particle counts bounded and scaled by
// env.quality and the canvas area, drifts with the wind's sign, and has no lightning flashes under reduced motion.
import assert from 'node:assert/strict';
import { WEATHER } from './fw_fx.js';
import './fw_fx_all.js';

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('ok  ', name); };
const NAMES = ['Rain', 'Snow', 'Fog', 'Mist', 'Clouds', 'Storm', 'Lightning'];
const fakeEnv = (o = {}) => ({ sim: null, cam: null, cssW: 1280, cssH: 800, k: 0.5, time: 0, wind: 1.5, scenery: null,
  seed: 1234, reduced: false, quality: 1,
  lights: [{ x: 1200, y: 500, r: 600, I: 1.5, col: [255, 120, 60] }], ...o });

// Run a weather for `frames` 60 Hz steps; returns the plug-in. `env` may change per frame through `each`.
function run(name, env, frames = 600, each = null) {
  const P = WEATHER[name].make(env);
  P.resize?.(env);
  for (let i = 0; i < frames; i++) { env.time = i / 60; each?.(i, env); P.update(1 / 60, env); }
  return P;
}
const parts = P => P.parts || [P];
const stats = P => parts(P).map(p => p.stats?.() ?? {});
// Everything numeric in the state that matters (positions, counts, flash), as one JSON string.
const snapshot = P => JSON.stringify(parts(P).map(p => ({ s: p.stats?.(),
  drops: p.layers?.map(L => L.drops?.map(d => [d.x, d.y]) ?? L.off), flakes: p.flakes?.map(f => [f.x, f.y]),
  strikes: p.strikes?.map(s => [s.t0, s.x, s.bolt?.length]) })));
const count = P => stats(P).reduce((a, s) => a + (s.count || 0), 0);

ok('all seven weathers are registered', () => assert.deepEqual(NAMES.filter(k => !WEATHER[k]), []));

for (const name of NAMES) {
  ok(`${name}: deterministic for a seed, different for another seed`, () => {
    const a = snapshot(run(name, fakeEnv())), b = snapshot(run(name, fakeEnv()));
    assert.equal(a, b);
    assert.notEqual(a, snapshot(run(name, fakeEnv({ seed: 99 }))));
  });
  ok(`${name}: particle counts bounded, scaled by quality and area`, () => {
    const full = count(run(name, fakeEnv(), 120)), low = count(run(name, fakeEnv({ quality: 0.4 }), 120));
    const phone = count(run(name, fakeEnv({ cssW: 390, cssH: 844 }), 120));
    const huge = count(run(name, fakeEnv({ cssW: 7680, cssH: 4320 }), 30));
    assert.ok(full > 0 && full < 6000, `${full}`);
    assert.ok(huge <= Math.max(full * 2.01, 3), `huge ${huge} vs ${full}`);   // capped on big screens
    if (full > 20) { assert.ok(low < full * 0.6, `quality: ${low} vs ${full}`); assert.ok(phone < full * 0.6, `phone: ${phone} vs ${full}`); }
    // the quality dropping mid-run (adaptive renderer) shrinks the live particle lists
    const P = run(name, fakeEnv(), 200, (i, env) => { env.quality = i < 100 ? 1 : 0.35; });
    if (full > 20) assert.ok(count(P) < full * 0.6);
  });
  ok(`${name}: the wind's sign sets the drift`, () => {
    const drift = w => stats(run(name, fakeEnv({ wind: w }), 120)).map(s => s.vx).filter(v => v !== undefined);
    const east = drift(3), west = drift(-3);
    assert.ok(east.length > 0);
    east.forEach((v, i) => { assert.ok(v > 0, `${name} east ${v}`); assert.ok(west[i] < 0, `${name} west ${west[i]}`); });
  });
}

ok('Storm and Lightning strike within 40 s and flash; never under reduced motion', () => {
  for (const name of ['Storm', 'Lightning']) {
    let maxFlash = 0, bolts = 0;
    const P = WEATHER[name].make(fakeEnv()), env = fakeEnv();
    for (let i = 0; i < 2400; i++) {
      P.update(1 / 60, env);
      const L = P.parts.find(p => p.strikes);
      maxFlash = Math.max(maxFlash, L.shared.flash); bolts += L.stats().bolts;
    }
    assert.ok(maxFlash > 0.5 && bolts > 0, `${name}: flash ${maxFlash}, bolt frames ${bolts}`);
    const R = WEATHER[name].make(fakeEnv({ reduced: true })), renv = fakeEnv({ reduced: true });
    for (let i = 0; i < 2400; i++) {
      R.update(1 / 60, renv);
      const L = R.parts.find(p => p.strikes);
      assert.equal(L.shared.flash, 0); assert.equal(L.strikes.length, 0);
    }
  }
});

ok('Snow accumulates slowly and monotonically', () => {
  const P = WEATHER.Snow.make(fakeEnv()), env = fakeEnv();
  let last = 0;
  for (let i = 0; i < 3600; i++) { P.update(1 / 60, env); assert.ok(P.acc >= last); last = P.acc; }
  assert.ok(last > 0.9 && last < 3.5, `${last}`);
});

ok('Rain: splashes on water when the scene has water, on the ground otherwise; bounded', () => {
  const water = run('Rain', fakeEnv({ scenery: { name: 'Cityscape', water: 1100, horizon: 0.7 } }), 300).splashes;
  const ground = run('Rain', fakeEnv({ scenery: { name: 'Forest', water: null, horizon: 0.82 } }), 300).splashes;
  assert.ok(water.length > 5 && water.every(s => s.ring && s.y >= 550), `${water.length}`);
  assert.ok(ground.length > 2 && ground.every(s => !s.ring && s.y >= 720), `${ground.length}`);
  assert.ok(water.length <= 400 && ground.length <= 400);
});

console.log(`${n} weather tests passed`);
