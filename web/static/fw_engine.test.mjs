// node fw_engine.test.mjs: the JS port of the firework models and patterns against numbers from the Python code
// (tests/fixtures/fw_reference.json, written by scripts/make_js_fixtures.py from web/reference.py).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { rng } from './core.js';
import { CONFIG, Firework, Show } from './fw_engine.js';
import { pyRand } from './fw_rand.js';
import { CirclePattern, TextPattern } from './fw_patterns.js';
import { maxDiff, patternPoints, runShow } from './fw_reference.js';

const F = JSON.parse(readFileSync(new URL('../../tests/fixtures/fw_reference.json', import.meta.url)));
let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('ok  ', name); };

ok('mulberry32 stream equals reference.PyRand', () => {
  const r = rng(1);
  F.mulberry32_seed1.forEach(v => assert.equal(r(), v));
});
ok('CONFIG equals config.FireworkConfig', () => assert.deepEqual({ ...CONFIG }, F.config));

ok(`${F.patterns.length} pattern point sets match models/patterns.py`, () => {
  for (const ref of F.patterns) {
    const js = patternPoints(ref);
    if (ref.name === 'Random') assert.equal(js.selected, ref.selected, `Random seed ${ref.seed}`);
    assert.equal(js.points.length, ref.points.length, ref.name);
    const d = maxDiff(ref.points, js.points);
    assert.ok(d < 1e-12, `${ref.name} ${JSON.stringify(ref.kwargs || ref.seed)}: ${d}`);
  }
});

for (const ref of F.shows) {
  const c = ref.case;
  ok(`show "${c.name}": ${c.steps} frames (seed ${c.seed}, ${c.particles} particles) track Python`, () => {
    const js = runShow(c);
    assert.equal(js.snapshots.length, ref.snapshots.length);
    js.snapshots.forEach((s, k) => assert.equal(s.fireworks.length, ref.snapshots[k].fireworks.length, `step ${s.step}`));
    const d = maxDiff(ref.snapshots, js.snapshots);
    const fw = ref.snapshots.at(-1).fireworks.length;
    console.log(`      ${fw} fireworks at the end; max relative |JS - Python| ${d.toExponential(2)}`);
    assert.ok(d < 1e-9, `diverged: ${d}`);
  });
}

ok('rocket rises, explodes at the apex into particle_count particles, all expire after 100 frames', () => {
  const fw = new Firework(100, 600, [1, 2, 3], 30, pyRand(4));
  let frames = 0;
  while (!fw.exploded) { fw.update(); frames++; }
  assert.equal(fw.particles.length, 30);
  assert.ok(fw.velocity_y >= 0 && fw.y < 600 && frames > 70 && frames < 130, `${frames} frames`);
  for (let i = 0; i < 99; i++) assert.ok(fw.update());
  assert.equal(fw.update(), false);
});

ok('web additions: pattern bursts, gravity, launch speed, auto launch off', () => {
  const fw = new Firework(400, 600, [1, 1, 1], 50, pyRand(1), { pattern: new CirclePattern(1.0, 0, 36) });
  fw.y = 300; fw.explode();
  assert.equal(fw.particles.length, 36);
  fw.particles.forEach(p => assert.ok(Math.abs(Math.hypot(p.velocity_x, p.velocity_y) - CONFIG.PARTICLE_SPEED_MAX) < 1e-12));
  const t = new Firework(0, 600, [1, 1, 1], 20, pyRand(1), { pattern: new TextPattern('xyz') });
  t.explode(); assert.equal(t.particles.length, 20);            // no letter shape -> plain burst
  const a = new Firework(0, 600, [1, 1, 1], 5, pyRand(2)), b = new Firework(0, 600, [1, 1, 1], 5, pyRand(2), { launchSpeed: 20 });
  assert.ok(Math.abs(b.velocity_y - 2 * a.velocity_y) < 1e-12);
  const g = new Firework(0, 600, [1, 1, 1], 5, pyRand(2), { gravity: 0 });
  for (let i = 0; i < 50; i++) g.update();
  assert.equal(g.exploded, false);
  const s = new Show(800, 600, { rand: pyRand(3) }); s.autoLaunch = false;
  for (let i = 0; i < 200; i++) s.update();
  assert.equal(s.fireworks.length, 0);
});

console.log(`fw_engine: ${n} tests passed`);
