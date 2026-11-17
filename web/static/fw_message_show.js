// Copy of models/message_show.py: the opening show, the messages and the optional finale of a message show (see the
// Python docstring for the timeline). Same random order as the Python (checked by fw_pyro.test.mjs).
import { finaleCues } from './fw_director.js';

export const OPENERS = { off: null, short: [3, 2, 1], medium: [4, 4, 3], long: [5, 7, 8] };
export const OPENER_LABELS = { off: 'Off', short: 'Short (~8 s)', medium: 'Medium (~15 s)', long: 'Long (~25 s)' };
const SHORT_TYPES = ['peony', 'chrysanthemum', 'ring', 'crackle'];
const SINGLE_TYPES = ['peony', 'chrysanthemum', 'ring', 'willow', 'palm'];
const PAIR_TYPES = ['chrysanthemum', 'crossette', 'ring', 'kamuro', 'peony', 'horsetail'];
const VOLLEY_TYPES = ['peony', 'chrysanthemum', 'crackle', 'multibreak', 'strobe', 'ring', 'willow'];
const GENTLE_OUT = ['strobe', 'crackle', 'multibreak'];
export const DARK_BEAT = 1.5;
const SAFE_TAIL = 3.5;

function pick(R, types, gentle) {
  if (gentle) types = types.filter(t => !GENTLE_OUT.includes(t));
  return types[Math.trunc(R.random() * types.length)];
}

export function openerCues(R, level, gentle = false) {
  const spec = OPENERS[level];
  if (!spec) return [[], 0];
  const [ns, np, nv] = gentle ? [3, 2, 0] : spec, slots = [];
  let t = 0.3;
  for (let i = 0; i < ns; i++) { slots.push([t, 'single', i]); t += 1.3; }
  for (let i = 0; i < np; i++) { slots.push([t, 'pair', i]); t += 1.1; }
  for (let i = 0; i < nv; i++) { slots.push([t, 'volley', i]); t += Math.max(0.9, 1.4 - 0.1 * i); }
  const end = slots.at(-1)[0], cues = [];
  for (const [when, kind, i] of slots) {
    const tail = when > end - SAFE_TAIL;
    if (kind === 'single') {
      const typ = pick(R, tail ? SHORT_TYPES : SINGLE_TYPES, gentle);
      const x = (i % 2 === 0 ? -1 : 1) * R.uniform(0.15, 0.55);
      cues.push([when, typ, x, R.uniform(0.5, 0.72), 0]);
    } else if (kind === 'pair') {
      const typ = pick(R, tail ? SHORT_TYPES : PAIR_TYPES, gentle), x = R.uniform(0.35, 0.8), h = R.uniform(0.45, 0.7);
      cues.push([when, typ, -x, h, 0], [when, typ, x, h, 0]);
    } else {
      const k = 3 + Math.min(2, i);
      for (let j = 0; j < k; j++) {
        const typ = pick(R, tail ? SHORT_TYPES : VOLLEY_TYPES, gentle);
        const x = -0.8 + 1.6 * j / (k - 1) + R.uniform(-0.08, 0.08);
        cues.push([when + 0.05 * j, typ, x, R.uniform(0.45, 0.75), 0]);
      }
    }
  }
  return [cues, end + (nv ? 0.05 * (2 + Math.min(2, nv - 1)) : 0)];
}

// [cues sorted by time, duration in s]
export function showCues(R, messages, opener = 'short', finale = false, gentle = false, lift = 3) {
  const [cues, last] = openerCues(R, opener, gentle);
  let t = cues.length ? last + DARK_BEAT : 0.3, end = t;
  messages.forEach((m, i) => {
    cues.push([t, 'message', m]);
    const release = t + lift + 0.45 + 1.1 + (m.hold ?? 2.5);
    if (i < messages.length - 1) {
      cues.push([release, pick(R, SHORT_TYPES, gentle), -0.85, 0.4, 0]);
      cues.push([release + 0.8, pick(R, SHORT_TYPES, gentle), 0.85, 0.4, 0]);
      t = release + 2.5;
    }
    end = release + 2;
  });
  if (finale && messages.length) {
    const fc = finaleCues(R);
    for (const c of fc) cues.push([end + c[0], ...c.slice(1)]);
    end += fc.at(-1)[0] + lift + 4;
  } else if (!messages.length) end = t;
  return [cues.map((c, i) => [c, i]).sort((a, b) => a[0][0] - b[0][0] || a[1] - b[1]).map(a => a[0]), end];
}
