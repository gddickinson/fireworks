// Home page: hero with a live display, counts from the Python package, entry cards and scene shortcuts.
import { route, api, app, list, esc, onLeave } from './core.js';
import { ShowView } from './show_view.js';

const DOORS = [
  ['#/show', 'The display', 'The full simulator: particle count, colours, explosion patterns, gravity and launch speed, five scenes and four weather effects. Click the sky to launch.', 'a'],
  ['#/patterns', 'Explosion patterns', 'The shapes defined in models/patterns.py (circle, heart, star, spiral, double ring, random, text), computed by Python and JavaScript side by side.', 'b'],
  ['#/verify', 'Python vs JavaScript', 'Seeded runs of the Python models (fireworks, weather, scenes, colours) replayed by the browser port, with the differences measured.', 'c'],
  ['#/about', 'About', 'What the simulation does step by step, what differs from the desktop app, and how to run both apps.', 'a'],
];

route('home', async () => {
  const [info, D] = await Promise.all([api('/info'), api('/defaults')]);
  app().innerHTML = `
  <section class="hero home-hero">
    <div>
      <p class="kicker">Rockets · Particles · Patterns</p>
      <h1 class="glow">Fireworks Simulator</h1>
      <p class="lead">${esc(info.summary)} This is the same display running in your browser: rockets climb against
      gravity, burst at the top of their flight into fading particles, over a night sky, city, mountains, beach or
      forest, in rain, snow, fog or lightning.</p>
      <a class="btn" href="#/show">Open the display</a><a class="btn alt" href="#/about">How it works</a>
    </div>
    <div class="hero-sky"><canvas id="mini"></canvas></div>
  </section>
  <div class="tiles">
    <div class="tile"><b>${info.patterns}</b><span>pattern choices</span></div>
    <div class="tile"><b>${info.backgrounds}</b><span>background scenes</span></div>
    <div class="tile"><b>${info.weather}</b><span>weather effects</span></div>
    <div class="tile"><b>${info.sliders}</b><span>control sliders</span></div>
    <div class="tile"><b>${info.max_particles}</b><span>max particles per rocket</span></div>
  </div>
  <div class="grid wide">${list(DOORS, ([href, t, d, c]) => `<a class="card door ${c}" href="${href}"><b>${t}</b><span>${d}</span></a>`)}</div>
  <h2>Pick a scene</h2>
  <div class="chips">${list(D.backgrounds, b => `<a class="chip" href="#/show?background=${encodeURIComponent(b)}&random=1">${esc(b)}</a>`)}
    ${list(D.weather.filter(w => w !== 'None'), w => `<a class="chip" href="#/show?weather=${encodeURIComponent(w)}&random=1">${esc(w)}</a>`)}</div>`;
  const V = new ShowView(document.getElementById('mini'), { seed: 2024, background: 'Night Sky',
    label: 'Live fireworks display over a night sky (click to launch)' });
  Object.assign(V.show, { use_random_colors: true, particle_count: 80 });
  V.show.set_pattern('Random'); V.show.set_random_patterns(true);
  for (let i = 0; i < 90; i++) V.step();                     // start mid-show
  V.draw();
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) V.start();
  onLeave(() => { V.stop?.(); V.ro.disconnect(); });
});
