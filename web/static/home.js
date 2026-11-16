// Home page: hero with a live display, counts from the Python package, entry cards and scene shortcuts.
import { route, api, app, list, esc, onLeave } from './core.js';
import { RealView, reducedMotion } from './real_view.js';

const DOORS = [
  ['#/show', 'The display', 'A realistic show: 3-D shells with air drag, twelve shell types from peonies to willows and crossettes, lit smoke, reflections, optional sound and a choreographed finale, over five scenes with four weather effects. Click the sky to launch.', 'a'],
  ['#/messages', 'Messages in the sky', 'Write a greeting in fireworks (any language, several messages in a row), then share it as a link, a GIF or a video.', 'b'],
  ['#/patterns', 'Explosion patterns', 'The shapes defined in models/patterns.py (circle, heart, star, spiral, double ring, random, text), computed by Python and JavaScript side by side.', 'b'],
  ['#/verify', 'Python vs JavaScript', 'Seeded runs of the Python models (realistic and classic fireworks, weather, scenes, colours) replayed by the browser, with the differences measured.', 'c'],
  ['#/about', 'About', 'What the simulation does step by step, what differs from the desktop app, and how to run both apps.', 'a'],
];

route('home', async () => {
  const [info, D] = await Promise.all([api('/info'), api('/defaults')]);
  app().innerHTML = `
  <section class="hero home-hero">
    <div>
      <p class="kicker">Rockets · Particles · Patterns</p>
      <h1 class="glow">Fireworks Simulator</h1>
      <p class="lead">${esc(info.summary)} In your browser: shells climb against gravity and air drag, burst at
      the top of their flight into burning stars that change colour as they cool, trail sparks, crackle and droop,
      lighting the smoke, the sky and the scene below: a harbour city, mountains over a lake, a beach, a forest or
      open country, in rain, snow, fog or lightning.</p>
      <a class="btn" href="#/show">Open the display</a><a class="btn alt" href="#/about">How it works</a>
    </div>
    <div class="hero-sky"><canvas id="mini"></canvas></div>
  </section>
  <div class="tiles">
    <div class="tile"><b>${info.shell_types}</b><span>shell types</span></div>
    <div class="tile"><b>${info.patterns}</b><span>pattern choices</span></div>
    <div class="tile"><b>${info.backgrounds}</b><span>background scenes</span></div>
    <div class="tile"><b>${info.weather}</b><span>weather effects</span></div>
    <div class="tile"><b>${info.sliders}</b><span>control sliders</span></div>
  </div>
  <div class="grid wide">${list(DOORS, ([href, t, d, c]) => `<a class="card door ${c}" href="${href}"><b>${t}</b><span>${d}</span></a>`)}</div>
  <h2>Pick a scene</h2>
  <div class="chips">${list(D.backgrounds, b => `<a class="chip" href="#/show?background=${encodeURIComponent(b)}&random=1">${esc(b)}</a>`)}
    ${list(D.weather.filter(w => w !== 'None'), w => `<a class="chip" href="#/show?weather=${encodeURIComponent(w)}&random=1">${esc(w)}</a>`)}</div>`;
  const V = new RealView(document.getElementById('mini'), { seed: 2024, background: 'Beach',
    label: 'Live fireworks display over a beach at night (click to launch)' });
  V.show.use_random_colors = true;
  V.director.rate = 1.6;
  for (let i = 0; i < 4; i++) V.launch(-0.7 + i * 0.45);
  for (let i = 0; i < 330; i++) V.step();                    // start mid-show
  V.draw();
  if (!reducedMotion()) V.start();
  onLeave(() => { V.stop?.(); V.ro.disconnect(); });
});
