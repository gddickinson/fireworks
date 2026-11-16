// node fw_pyro.test.mjs: the JavaScript copy of the realistic engine (fw_pyro.js, fw_shells.js, fw_director.js)
// against seeded runs of models/pyro.py, shell_types.py and director.py (tests/fixtures/fw_reference.json "pyro").
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { maxDiff } from './fw_reference.js';
import { runPyro } from './fw_reference_pyro.js';
import { Sim, sphereDirs } from './fw_pyro.js';
import { Director, finaleCues } from './fw_director.js';
import { starRGB } from './fw_palette.js';
import { pyRand } from './fw_rand.js';

const F = JSON.parse(readFileSync(new URL('../../tests/fixtures/fw_reference.json', import.meta.url)));
let n = 0;
const test = (name, fn) => { fn(); n++; console.log('ok', name); };

for (const ref of F.pyro) {
  test(`pyro run "${ref.case.name}" matches Python`, () => {
    const js = runPyro(ref.case);
    const d = maxDiff(ref.snapshots, js.snapshots);
    assert.ok(d < 1e-9, `${ref.case.name}: max relative difference ${d}`);
    const last = ref.snapshots.at(-1);
    assert.ok(last.events.burst > 0, 'something burst');
  });
}

test('sphere directions are unit vectors spread over both hemispheres', () => {
  const ds = sphereDirs(100, 0.3);
  for (const [x, y, z] of ds) assert.ok(Math.abs(Math.hypot(x, y, z) - 1) < 1e-12);
  assert.equal(ds.filter(d => d[1] > 0).length, 50);
});

test('a shell bursts near the height asked for (drag-corrected launch speed)', () => {
  const sim = new Sim(pyRand(3)), d = new Director(sim.rand);
  sim.wind = 0;
  const s = sim.launch(d.recipe('peony'), 0, 500, 0.6);
  const want = 0.6 * sim.y_top(500);
  for (let i = 0; i < 1000 && sim.stars.includes(s); i++) sim.step();
  assert.ok(Math.abs(s.y - want) < 0.03 * want, `burst at ${s.y} m, wanted ${want}`);
});

test('stars slow under drag towards terminal velocity sqrt(g/k)', () => {
  const sim = new Sim(pyRand(4)), d = new Director(sim.rand);
  sim.wind = 0;
  sim.launch(d.recipe('peony'), 0, 500, 0.6);
  for (let i = 0; i < 2000 && !sim.stars.some(s => s.kind === 'star'); i++) sim.step();
  for (let i = 0; i < 90; i++) sim.step();                    // 1.5 s after the burst
  const v = Math.max(...sim.stars.filter(s => s.kind === 'star').map(s => Math.hypot(s.vx, s.vy, s.vz)));
  assert.ok(v < 25, `fastest star ${v} m/s (burst at ~55 m/s, terminal ~17 m/s)`);
});

test('the finale programme is sorted and ends with salutes', () => {
  const cues = finaleCues(pyRand(5));
  for (let i = 1; i < cues.length; i++) assert.ok(cues[i][0] >= cues[i - 1][0]);
  assert.ok(cues.some(c => c[1] === 'salute') && cues.length > 60);
  for (const t of ['peony', 'palm', 'crossette', 'ring', 'willow', 'kamuro', 'strobe']) assert.ok(cues.some(c => c[1] === t), t);
});

test('star colour: white-hot at ignition, its colour while burning, dark at the end', () => {
  const s = { kind: 'star', age: 0, life: 2, color: [255, 38, 28], color2: null, change: 1, bright: 1, strobe: 0, glitter: false, phase: 0 };
  const o = [0, 0, 0, 0];
  starRGB(s, o); assert.ok(o[1] > 200 && o[3] > 1.5);
  s.age = 0.8; starRGB(s, o); assert.ok(o[1] < 60 && o[0] > 250);
  s.age = 2; starRGB(s, o); assert.ok(o[3] < 1e-9);
});

console.log(`${n} tests passed`);
