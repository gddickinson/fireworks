// Verify page: seeded runs of the real Python models (web/reference.py) replayed by the JavaScript port in this
// browser, with the largest relative difference. The node tests in the repo assert the same comparisons.
import { route, api, app, esc, list } from './core.js';
import { backgroundScenes, maxDiff, randomColors, runShow, weatherRuns } from './fw_reference.js';
import { rgbCss } from './fw_color.js';

const verdict = (d, tol = 1e-9) => `<b class="${d < tol ? 'ok' : 'err'}">${d === 0 ? '0 (identical)' : d.toExponential(2)}</b>`;
const row = (what, detail, d) => `<tr><th>${what}</th><td>${detail}</td><td>${verdict(d)}</td></tr>`;

route('verify', async () => {
  const [cases, D] = await Promise.all([api('/reference'), api('/defaults')]);
  app().innerHTML = `
  <h1 class="glow">Python vs JavaScript</h1>
  <p class="lead">The web display runs a JavaScript port of the desktop app's models. To check it, the Python code is
  run with a seeded random stream (mulberry32, a copy of the browser's generator stands in for Python's
  <code>random</code> module) and the browser replays the same runs here. Differences are relative, per number.</p>
  <section class="panel"><h2>Firework shows</h2>
  <p class="small mute">The <code>FireworksCanvas.update_animation</code> loop with the real <code>Firework</code> and
  <code>Particle</code> classes: spawn chance ${Math.round(D.firework.SPAWN_RATE * 100)}% per frame, rockets at random x, burst at the apex. Snapshots compare
  every firework's position and velocity and the sums of its particles' positions and velocities.</p>
  <div class="scroll"><table><thead><tr><th>Run</th><th>Setup</th><th>max |JS − Python|</th></tr></thead><tbody id="shows"></tbody></table></div></section>
  <section class="panel"><h2>Weather, scenes and colours</h2>
  <p class="small mute">These Python modules import PyQt6, so their reference numbers were computed once by
  <code>scripts/make_js_fixtures.py</code> and are served from the committed fixture.</p>
  <div class="scroll"><table><thead><tr><th>Part</th><th>Compared</th><th>max |JS − Python|</th></tr></thead><tbody id="scenes"></tbody></table></div>
  <h3>Random colours (ColorUtils.random_color, seed 9): Python, then JavaScript</h3><div id="cols"></div></section>`;
  const shows = document.getElementById('shows');
  for (const c of cases) {
    const ref = await api('/reference/' + c.name), t0 = performance.now();
    const js = runShow(ref.case), ms = performance.now() - t0;
    const k = ref.case, last = ref.snapshots.at(-1).fireworks;
    const parts = last.reduce((n, f) => n + f.n, 0);
    shows.insertAdjacentHTML('beforeend', row(`"${esc(k.name)}"`, `seed ${k.seed} · ${k.width}×${k.height} · ${k.particles}
      particles per rocket${k.pattern ? ` · ${k.pattern} pattern` : ''}${k.random_each ? ' · random pattern per rocket' : ''}${k.gravity !== undefined ? ` · gravity ${k.gravity}, launch speed ${k.launch_speed}` : ""} · ${k.steps} frames, ${ref.snapshots.length} snapshots · ${last.length} fireworks and ${parts}
      particles at the end · JS ${ms.toFixed(0)} ms`, maxDiff(ref.snapshots, js.snapshots)));
  }
  let q;
  try { q = await api('/reference/scenes'); } catch (e) {
    document.getElementById('scenes').innerHTML = `<tr><td colspan="3" class="err">${esc(e.message)}</td></tr>`; return;
  }
  const W = weatherRuns(), B = backgroundScenes(), C = randomColors();
  const rows = [];
  for (const n of ['Rain', 'Snow', 'Fog']) {
    const r = q.weather[n];
    rows.push(row(n, `${r.steps} updates · ${r.particles.length || r.layers.length} ${r.particles.length ? 'particles' : 'fog layers'}`, maxDiff(r, W[n])));
  }
  const L = q.weather.Lightning;
  rows.push(row('Lightning', `600 frames · ${L.strikes.length} strikes, their bolt segments and branches`, maxDiff(L, W.Lightning)));
  for (const n of Object.keys(q.backgrounds)) {
    const b = q.backgrounds[n];
    rows.push(row(n, Object.entries(b).map(([k, v]) => `${v.length} ${k.replace('_', ' ')}`).join(' · '), maxDiff(b, B[n])));
  }
  rows.push(row('Colours', `${C.length} random colours (HSV → RGB)`, maxDiff(q.colors, C)));
  document.getElementById('scenes').innerHTML = rows.join('');
  const sw = cs => `<div>${list(cs, c => `<span class="swatch" style="background:${rgbCss(c)}" title="${c.join(', ')}"></span>`)}</div>`;
  document.getElementById('cols').innerHTML = sw(q.colors) + sw(C);
});
