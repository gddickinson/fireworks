// node fw_scenery.test.mjs: the realistic scene list, every painter (night and dusk) on a recording mock canvas
// (deterministic, finite geometry), and the sky-effect / scene plug-ins' update() (deterministic for a seed, bounded,
// no canvas needed). No DOM: document.createElement('canvas') returns a mock whose 2D context records every call.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

let log = [];
const num = v => { if (typeof v === 'number' && !Number.isFinite(v)) throw new Error('non-finite canvas argument'); return v; };
const ctx2d = cv => {
  const gradient = () => ({ addColorStop: (o, c) => { num(o); log.push('s', o, c); } });
  const img = (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(Math.max(1, w * h * 4)) });
  return new Proxy({ canvas: cv }, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === 'createLinearGradient' || k === 'createRadialGradient') return (...a) => { a.forEach(num); log.push(k, ...a); return gradient(); };
      if (k === 'getImageData' || k === 'createImageData') return (x, y, w, h) => img(w ?? x, h ?? y);
      return (...a) => { for (const v of a) if (typeof v === 'number') { num(v); log.push(Math.round(v * 100)); } log.push(k); };
    },
    set(t, k, v) { t[k] = v; log.push(k, typeof v === 'number' ? Math.round(num(v) * 1000) : String(v)); return true; },
  });
};
globalThis.document = { createElement: () => { const cv = { width: 300, height: 150 }; const c = ctx2d(cv); cv.getContext = () => c; return cv; } };

const { SCENERY_HORIZON, PAINTERS, buildScenery } = await import('./fw_scenery.js');
const { SKY_FX, SCENE_FX } = await import('./fw_fx.js');
await import('./fw_fx_all.js');
const { moonDisc } = await import('./fw_sky_fx.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('ok  ', name); };
const NEW = ['Harbour', 'River Bridge', 'Waterfront', 'Desert', 'Snowy Village', 'Castle', 'Countryside'];

ok('every SCENERY_HORIZON key has a painter and a horizon in (0.5, 0.95)', () => {
  for (const [k, h] of Object.entries(SCENERY_HORIZON)) {
    assert.equal(typeof PAINTERS[k], 'function', k);
    assert.ok(h > 0.5 && h < 0.95, `${k}: ${h}`);
  }
  for (const k of Object.keys(PAINTERS)) assert.ok(k in SCENERY_HORIZON, `painter without horizon: ${k}`);
  for (const k of NEW) assert.ok(k in SCENERY_HORIZON, k);
});

const build = (name, time, seed = 7, W = 320, H = 180) => { log = []; const S = buildScenery(name, W, H, seed, { time }); return { S, log }; };
const digest = a => { let h = 0; for (const v of a) { const s = String(v); for (let i = 0; i < s.length; i++) h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0; } return h; };

for (const name of Object.keys(SCENERY_HORIZON)) {
  ok(`${name}: paints night and dusk with finite geometry, deterministically`, () => {
    for (const time of ['night', 'dusk']) {
      const a = build(name, time), b = build(name, time);
      assert.equal(digest(a.log), digest(b.log), `${name} ${time} not deterministic`);
      assert.equal(a.S.time, time); assert.equal(a.S.horizon, SCENERY_HORIZON[name]);
      if (a.S.water !== null) assert.ok(a.S.water > 0 && a.S.water < a.S.H);
      for (const k of ['chimneys', 'beacons', 'boats', 'turbines']) for (const p of a.S[k]) p.slice(0, 3).forEach(v => assert.ok(Number.isFinite(v), `${name}.${k}`));
    }
    assert.notEqual(digest(build(name, 'night').log), digest(build(name, 'dusk').log), 'dusk paints the same as night');
    assert.notEqual(digest(build(name, 'night', 7).log), digest(build(name, 'night', 8).log), 'seed has no effect');
  });
}

ok('scene data for the plug-ins: chimneys in the village, boats + lighthouse in the harbour, beacons, turbines, bridge', () => {
  assert.ok(build('Snowy Village').S.chimneys.length >= 6);
  const h = build('Harbour').S; assert.ok(h.boats.length >= 2 && h.lighthouse);
  assert.ok(build('River Bridge').S.beacons.length >= 2 && build('Waterfront').S.beacons.length >= 3);
  assert.ok(build('Countryside').S.turbines.length >= 3);
  const br = build('River Bridge').S.bridge; assert.ok(br > 2 && br < 40, `bridge ${br} m`);
});

// ---- plug-ins: update() deterministic and bounded (no canvas used by update)
const env = (S, seed, extra = {}) => ({ sim: null, cam: null, cssW: 640, cssH: 360, k: 640 / S.W, lights: [], time: 0, wind: 1.5,
  scenery: S, seed, reduced: false, quality: 1, ...extra });
const run = (make, S, seed, steps = 900, extra = {}) => {
  const e = env(S, seed, extra), p = make(e), states = [];
  for (let i = 0; i < steps; i++) {
    e.time = i / 60; e.wind = 1.5 + Math.sin(i / 50) * 2;
    p.update?.(1 / 60, e);
    if (i % 150 === 149) states.push(JSON.stringify(p.state()));
  }
  return { p, states, e };
};
const finite = (v, path = '') => {
  if (typeof v === 'number') assert.ok(Number.isFinite(v), `non-finite at ${path}`);
  else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) finite(x, path + '.' + k);
};
const plugins = [...Object.entries(SKY_FX).map(([k, f]) => [`sky ${k}`, f.make, 'Harbour']),
  ...Object.entries(SCENE_FX).map(([k, make]) => [`scene ${k}`, make, k])];

for (const key of ['moon', 'aurora', 'meteors', 'lanterns']) ok(`sky effect "${key}" is registered with a label`, () => assert.ok(SKY_FX[key]?.label));
for (const k of ['Harbour', 'Snowy Village', 'River Bridge', 'Waterfront', 'Countryside']) ok(`scene objects for ${k}`, () => assert.ok(SCENE_FX[k]));

for (const [label, make, scene] of plugins) {
  ok(`${label}: update() deterministic for a seed, different for another, finite`, () => {
    const S = build(scene, 'night', 7, 640, 360).S;
    const a = run(make, S, 11), b = run(make, S, 11), c = run(make, S, 12);
    assert.deepEqual(a.states, b.states);
    a.states.forEach(s => finite(JSON.parse(s)));
    if (label.startsWith('sky')) assert.notDeepEqual(a.states, c.states, 'seed ignored');
    run(make, S, 11, 300, { reduced: true });
  });
}

ok('meteors: rare (about one per 7 s), at most 6 alive, inside the sky; rarer with reduced motion', () => {
  const S = build('Desert', 'night', 7, 640, 360).S, e = env(S, 3), p = SKY_FX.meteors.make(e);
  let seen = 0, last = -1;
  for (let i = 0; i < 60 * 120; i++) {
    p.update(1 / 60, e); const st = p.state();
    assert.ok(st.list.length <= 6);
    for (const m of st.list) { assert.ok(m.x >= 0 && m.x <= 640 && m.y >= 0 && m.y <= 360 * 0.8); if (m.age < 1 / 60 + 1e-9 && st.t !== last) seen++; }
    last = st.t;
  }
  assert.ok(seen >= 6 && seen <= 40, `meteors in 2 min: ${seen}`);
  const r = SKY_FX.meteors.make({ ...e, reduced: true }); let rs = 0;
  for (let i = 0; i < 60 * 120; i++) { const before = r.state().next; r.update(1 / 60, e); if (r.state().next !== before) rs++; }
  assert.ok(rs < seen, `reduced ${rs} vs ${seen}`);
});

ok('lanterns: stay near the screen and rise; drift follows the wind', () => {
  const S = build('Harbour', 'night', 7, 640, 360).S;
  for (const wind of [-4, 4]) {
    const e = env(S, 5, { wind }), p = SKY_FX.lanterns.make(e), x0 = p.state().list.map(L => L.x);
    for (let i = 0; i < 60 * 3; i++) p.update(1 / 60, e);
    const st = p.state().list, dx = st.reduce((a, L, i) => a + L.x - x0[i], 0) / st.length;
    assert.ok(Math.sign(dx) === Math.sign(wind), `drift ${dx} for wind ${wind}`);
    for (let i = 0; i < 60 * 60; i++) p.update(1 / 60, e);
    for (const L of p.state().list) assert.ok(L.x > -61 && L.x < 701 && L.y > -21 && L.y < 360);
  }
});

ok('chimney smoke: bounded puff count, puffs rise and drift downwind', () => {
  const S = build('Snowy Village', 'night', 7, 640, 360).S, e = env(S, 5, { wind: 3 }), p = SCENE_FX['Snowy Village'](e);
  for (let i = 0; i < 60 * 30; i++) p.update(1 / 60, e);
  const st = p.state(), k = 640 / S.W;
  assert.ok(st.n > 0 && st.n <= S.chimneys.length * Math.ceil(6 / 0.32 + 1), `${st.n} puffs`);
  const top = Math.min(...S.chimneys.map(c => c[1] * k));
  assert.ok(st.list.some(([, y]) => y < top - 10), 'smoke rises');
  const meanX = st.list.reduce((a, [x]) => a + x, 0) / st.n, chX = S.chimneys.reduce((a, c) => a + c[0] * k, 0) / S.chimneys.length;
  assert.ok(meanX > chX, 'drifts with the wind');
});

ok('aurora: columns finite, brightness in [0, 1.5], calmer (slower) with reduced motion', () => {
  const S = build('Harbour', 'night', 7, 640, 360).S, e = env(S, 9), p = SKY_FX.aurora.make(e);
  for (const C of p.curtains) for (let u = 0; u <= 1; u += 0.01) {
    const c = p.column(C, u); finite(c); assert.ok(c.b >= 0 && c.b <= 1.5 && c.y > 0 && c.y < 1.2);
  }
  const r = SKY_FX.aurora.make({ ...e, reduced: true });
  p.update(1, e); r.update(1, { ...e, reduced: true });
  assert.ok(r.state().t < p.state().t);
});

ok('moon: phase is a crescent or gibbous, disc shading depends on the phase', () => {
  const lit = ph => { const { px } = moonDisc(12, 3, ph, 1, 0); let s = 0; for (let i = 0; i < px.length; i += 4) s += px[i] * px[i + 3] / 255; return s; };
  assert.ok(lit(0.75) > lit(2.35) * 1.5);
  const st = SKY_FX.moon.make(env(build('Harbour').S, 4)).state();
  assert.ok(st.phase > 0.5 && st.phase < 2.6 && st.fx > 0.1 && st.fx < 0.9);
});

ok('no Math.random in the scenery and effect modules', () => {
  for (const f of ['fw_scenery.js', 'fw_scenery_parts.js', 'fw_scenery_sky.js', 'fw_scenery_city.js', 'fw_scenery_props.js',
    'fw_scenery_houses.js', 'fw_scenery_more.js', 'fw_scenery_land.js', 'fw_sky_fx.js', 'fw_sky_aurora.js', 'fw_scene_fx.js', 'fw_fx_masks.js']) {
    const src = readFileSync(new URL(f, import.meta.url), 'utf8');
    assert.ok(!/Math\.random\s*\(/.test(src), f);
    assert.ok(src.split('\n').length < 500, `${f} has 500+ lines`);
  }
});

console.log(`fw_scenery: ${n} tests passed`);
