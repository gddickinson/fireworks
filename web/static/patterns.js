// Patterns page: every explosion shape from models/patterns.py. The points come from the Python code (/api/patterns,
// centred at 400, 300) and are recomputed here by fw_patterns.js; both are drawn, with the largest difference.
import { route, api, app, esc } from './core.js';
import { maxDiff, patternPoints } from './fw_reference.js';

const NAMES = ['Circle', 'Heart', 'Star', 'Spiral', 'Double Ring'];

function draw(canvas, py, js) {
  const W = 220, H = 160, dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = W * dpr; canvas.height = H * dpr;
  const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
  ctx.fillStyle = '#000014'; ctx.fillRect(0, 0, W, H);
  const all = py.length ? py : [[400, 300]];
  const r = Math.max(10, ...all.map(([x, y]) => Math.max(Math.abs(x - 400), Math.abs(y - 300))));
  const k = 62 / r, tx = x => W / 2 + (x - 400) * k, ty = y => H / 2 + (y - 300) * k;
  ctx.strokeStyle = '#ffc83d'; ctx.lineWidth = 1.2;
  for (const [x, y] of py) { ctx.beginPath(); ctx.arc(tx(x), ty(y), 3.2, 0, 2 * Math.PI); ctx.stroke(); }
  ctx.fillStyle = '#ff4fa3'; for (const [x, y] of js) ctx.fillRect(tx(x) - 1, ty(y) - 1, 2, 2);
}

const label = r => r.name === 'Random' ? `Random (seed ${r.seed}): ${NAMES[r.selected]}`
  : `${r.name}${Object.keys(r.kwargs).length ? ' · ' + Object.entries(r.kwargs).map(([k, v]) => `${k}=${typeof v === 'number' ? +v.toFixed(2) : JSON.stringify(v)}`).join(', ') : ' · defaults'}`;

route('patterns', async () => {
  const refs = await api('/patterns');
  app().innerHTML = `
  <h1 class="glow">Explosion patterns</h1>
  <p class="lead">The shapes defined in <code>models/patterns.py</code>. Gold rings: the points computed by the Python
  code; pink dots inside them: the same points from the JavaScript port. In the display each point becomes one
  particle flying outwards, so the burst grows into the shape.</p>
  <p class="callout small">The desktop app defines these patterns and lets you choose them, but its
  <code>Firework.explode()</code> does not use them yet (every burst is a uniform random spray). The web display adds
  that last step: one particle per pattern point, the outermost moving at the maximum particle speed times the
  pattern scale. <code>TextPattern</code> only has a shape for the letter A.</p>
  <div class="grid pats" id="pats"></div>`;
  const host = document.getElementById('pats');
  for (const r of refs) {
    const js = patternPoints(r), d = maxDiff(r.points, js.points);
    const same = d < 1e-9 && (r.name !== 'Random' || js.selected === r.selected);
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<b>${esc(r.name)}</b><small>${esc(label(r))}</small>
      <canvas role="img" aria-label="${esc(r.name)} pattern, ${r.points.length} points"></canvas>
      <span class="small">${r.points.length} points · max |JS − Python| <b class="${same ? 'ok' : 'err'}">${d === 0 ? '0 (identical)' : d.toExponential(1)}</b>
      ${r.points.length ? '' : ' (no letter shape)'} · <a href="#/show?pattern=${encodeURIComponent(r.name)}&random=1">launch</a></span>`;
    host.appendChild(card);
    draw(card.querySelector('canvas'), r.points, js.points);
  }
});
