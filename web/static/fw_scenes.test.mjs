// node fw_scenes.test.mjs: the JS weather, background scenes and random colours against effects/weather.py,
// effects/backgrounds.py, effects/mountains.py and utils/color.py (the "qt" part of tests/fixtures/fw_reference.json).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { hsvToRgb } from './fw_color.js';
import { backgroundScenes, maxDiff, randomColors, weatherRuns } from './fw_reference.js';

const F = JSON.parse(readFileSync(new URL('../../tests/fixtures/fw_reference.json', import.meta.url)));
let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('ok  ', name); };
assert.ok(F.qt, 'fixture has no Qt part: regenerate it with PyQt6 installed (scripts/make_js_fixtures.py)');

const W = weatherRuns();
for (const name of ['Rain', 'Snow', 'Fog']) {
  ok(`${name}: ${F.qt.weather[name].steps} updates match`, () => {
    assert.equal(W[name].particles.length, F.qt.weather[name].particles.length);
    const d = maxDiff(F.qt.weather[name], W[name]);
    assert.ok(d < 1e-9, `${name}: ${d}`);
  });
}
ok(`Lightning: ${F.qt.weather.Lightning.strikes.length} strikes in 600 frames, bolts and branches match`, () => {
  assert.equal(W.Lightning.strikes.length, F.qt.weather.Lightning.strikes.length);
  const d = maxDiff(F.qt.weather.Lightning, W.Lightning);
  assert.ok(d < 1e-9, `lightning: ${d}`);
});

const B = backgroundScenes();
for (const name of Object.keys(F.qt.backgrounds)) {
  ok(`background "${name}": generated scene matches`, () => {
    const d = maxDiff(F.qt.backgrounds[name], B[name]);
    assert.ok(d < 1e-12, `${name}: ${d}`);
  });
}

ok('random colours equal ColorUtils.random_color', () => assert.deepEqual(randomColors(), F.qt.colors));
ok('hsvToRgb corners', () => {
  assert.deepEqual(hsvToRgb(0, 1, 1), [1, 0, 0]);
  assert.deepEqual(hsvToRgb(0.5, 0, 0.3), [0.3, 0.3, 0.3]);
  assert.deepEqual(hsvToRgb(1 / 3, 1, 1).map(Math.round), [0, 1, 0]);
});

console.log(`fw_scenes: ${n} tests passed`);
