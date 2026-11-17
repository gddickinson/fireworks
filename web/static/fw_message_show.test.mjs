// node fw_message_show.test.mjs: the message-show timeline (fw_message_show.js, played by fw_director.js):
// ordering, nothing bursting over the letters while they hold, seed determinism, and the share link's show options.
import assert from 'node:assert/strict';
import { Sim } from './fw_pyro.js';
import { Director } from './fw_director.js';
import { showCues, openerCues, OPENERS } from './fw_message_show.js';
import { messagePoints } from './fw_reference_pyro.js';
import { pyRand } from './fw_rand.js';
import { decodeQuery, encodeQuery } from './msg_link.js';

let n = 0;
const test = (name, fn) => { fn(); n++; console.log('ok', name); };
const msgs = texts => texts.map(t => ({ points: messagePoints(t), hold: 3 }));

test('openers last about 8, 15 and 25 s and end with a dark beat before the message', () => {
  const want = { short: 8, medium: 15, long: 25 };
  for (const lvl of Object.keys(OPENERS)) {
    const [cues] = showCues(pyRand(1), msgs(['HI']), lvl);
    const m = cues.find(c => c[1] === 'message'), before = cues.filter(c => c[0] < m[0]);
    if (lvl === 'off') { assert.equal(before.length, 0); continue; }
    assert.ok(Math.abs(m[0] - want[lvl]) < 1.5, `${lvl}: message at ${m[0]}`);
    assert.ok(m[0] - Math.max(...before.map(c => c[0])) >= 1.4, 'dark beat');
    for (let i = 1; i < cues.length; i++) assert.ok(cues[i][0] >= cues[i - 1][0], 'sorted');
    const tail = before.filter(c => c[0] > m[0] - 1.5 - 3.5);  // last shells: short-lived types only
    assert.ok(tail.every(c => ['peony', 'chrysanthemum', 'ring', 'crackle'].includes(c[1])), lvl);
  }
  const [gentle] = openerCues(pyRand(2), 'long', true);
  assert.ok(gentle.length <= 7 && gentle.every(c => !['strobe', 'crackle', 'multibreak'].includes(c[1])));
});

test('messages play in order with light shells between them; the finale comes after the last', () => {
  const [cues, dur] = showCues(pyRand(3), msgs(['ONE', 'TWO', 'SIX']), 'short', true);
  const ms = cues.filter(c => c[1] === 'message');
  assert.deepEqual(ms.map(c => c[2].points.length), msgs(['ONE', 'TWO', 'SIX']).map(m => m.points.length));
  for (let i = 1; i < ms.length; i++) {
    const between = cues.filter(c => c[0] > ms[i - 1][0] && c[0] < ms[i][0]);
    assert.equal(between.length, 2);
    assert.ok(between.every(c => Math.abs(c[2]) > 0.8 && c[3] <= 0.4), 'low, at the sides');
  }
  assert.ok(cues.some(c => c[1] === 'salute' && c[0] > ms.at(-1)[0]) && dur > ms.at(-1)[0] + 40);
});

function play(seed, opener, texts, lift = 3) {
  const R = pyRand(seed), sim = new Sim(R), d = new Director(R);
  sim.lift_time = lift;
  const dur = d.queueMessages(sim, msgs(texts), opener, false);
  const bursts = [], holds = [];
  for (let f = 0; f < (dur + 3) * 60; f++) {
    d.step(sim); sim.step();
    const held = sim.stars.filter(s => s.target && s.age >= s.glide + 1.1 && s.age < s.hold);
    if (held.length) {
      const xs = held.map(s => s.target[0]), ys = held.map(s => s.target[1]);
      holds.push({ f, box: [Math.min(...xs) - 40, Math.max(...xs) + 40, Math.min(...ys) - 40, Math.max(...ys) + 40] });
    }
    for (const e of sim.events) if (e[0] === 'burst') bursts.push({ f, x: e[1], y: e[2], z: e[3], held: held.length > 0 });
  }
  return { bursts, holds, dur, mode: d.mode };
}

test('no shell bursts near the text while its letters hold (incl. real-time lift)', () => {
  for (const [opener, lift] of [['short', 3], ['medium', 3], ['long', 2], ['short', null]]) {
    const r = play(5, opener, ['HAPPY', 'NEW YEAR'], lift);
    assert.ok(r.holds.length > 200, 'letters held');
    const hf = new Set(r.holds.map(h => h.f));
    const during = r.bursts.filter(b => hf.has(b.f));
    for (const b of during) {
      const box = r.holds.find(h => h.f === b.f).box;
      const sx = b.x * 450 / b.z, sy = b.y * 450 / b.z;     // project to the message's depth
      assert.ok(!(sx > box[0] && sx < box[1] && sy > box[2] && sy < box[3]), `${opener}: burst over the text at frame ${b.f}`);
    }
    assert.equal(during.length, 0, `${opener}/${lift}: nothing bursts at all while letters hold`);
    assert.ok(r.bursts.length > 2 && r.mode === 'auto');
  }
});

test('the same seed gives the same show', () => {
  const a = play(9, 'medium', ['HI']), b = play(9, 'medium', ['HI']), c = play(10, 'medium', ['HI']);
  assert.deepEqual(a.bursts, b.bursts);
  assert.notDeepEqual(a.bursts, c.bursts);
});

test('share link carries the opener and finale options, validated', () => {
  const o = decodeQuery({ m: 'Hi', o: 'long', fin: '1' });
  assert.equal(o.opener, 'long'); assert.equal(o.finale, true);
  assert.deepEqual(decodeQuery(Object.fromEntries(new URLSearchParams(encodeQuery(o).split('?')[1]))), o);
  const bad = decodeQuery({ m: 'Hi', o: '<script>', fin: 'yes please' });
  assert.equal(bad.opener, 'short'); assert.equal(bad.finale, false);
  assert.equal(decodeQuery({ m: 'Hi' }).opener, 'short');
});

console.log(`${n} tests passed`);
