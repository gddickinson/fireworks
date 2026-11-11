// About page: what the simulator does (from the README and the code), what the web version adds, how to run both.
import { route, api, app, esc } from './core.js';

route('about', async () => {
  const [info, D] = await Promise.all([api('/info'), api('/defaults')]);
  const F = D.firework, sl = Object.fromEntries(D.sliders.map(s => [s.key, s]));
  app().innerHTML = `
  <h1 class="glow">About</h1>
  <p class="lead">${esc(info.summary)} Version ${esc(info.version)}. A desktop app (Python, PyQt6) and this web version,
  which runs a JavaScript port of the same models in the browser.</p>

  <h2>The simulation</h2>
  <p>Every frame (${F.FRAME_RATE} per second; the desktop timer ticks every ${Math.floor(1000 / F.FRAME_RATE)} ms):</p>
  <ul>
    <li><b>Launch</b>: with probability ${F.SPAWN_RATE} a rocket starts at a random x along the bottom edge with an
      upward speed between ${F.LAUNCH_SPEED_MIN} and ${F.LAUNCH_SPEED_MAX} pixels per frame.</li>
    <li><b>Climb</b>: gravity (${F.GRAVITY} px/frame²) slows it; when its vertical velocity reaches zero, at the top of
      its flight, it bursts.</li>
    <li><b>Burst</b>: ${F.MIN_PARTICLES} to ${F.MAX_PARTICLES} particles (default ${F.DEFAULT_PARTICLES}) fly out at random
      angles with speeds between ${F.PARTICLE_SPEED_MIN} and ${F.PARTICLE_SPEED_MAX} px/frame, fall under the same gravity,
      and fade out over 100 frames.</li>
    <li><b>Colour</b>: one colour per rocket, red by default, or a random bright colour (HSV saturation ≥ 0.7, value ≥ 0.8).</li>
    <li><b>Scenes</b>: ${esc(D.backgrounds.join(', '))}, generated at random for the window size (stars,
      lit windows, mountain ranges with snow caps, animated waves and palm trees, three layers of trees with fireflies).</li>
    <li><b>Weather</b>: rain falling at 45°, swaying snow, drifting layers of fog, and lightning with branching bolts and a
      sky flash every 50 to 200 frames.</li>
  </ul>

  <h2>What the web version adds</h2>
  <p>The JavaScript port matches the Python models number for number (see <a href="#/verify">Python vs JS</a>),
  including gravity (${sl.gravity.lo * sl.gravity.scale} to ${sl.gravity.hi * sl.gravity.scale}) and launch speed
  (${sl.launch_speed.lo * sl.launch_speed.scale} to ${sl.launch_speed.hi * sl.launch_speed.scale}; 10 keeps the
  ${F.LAUNCH_SPEED_MIN} to ${F.LAUNCH_SPEED_MAX} range, other values scale it). Additions of the web version:</p>
  <ul>
    <li><b>Explosion patterns</b>: the desktop app builds the chosen pattern but its <code>Firework.explode()</code> does
      not use it yet. Here each pattern point becomes a particle (see <a href="#/patterns">Patterns</a>). "None" gives
      the desktop's plain random bursts.</li>
    <li><b>Click to launch</b> at the clicked spot, keyboard shortcuts, pause and PNG export.</li>
    <li>The desktop app has no sound (<code>effects/sound.py</code> exists but is not used and its sound files are not in
      the repository), so neither has the web version.</li>
  </ul>

  <h2>Run the desktop app</h2>
  <pre>pip install -r requirements.txt     # PyQt6, numpy
python main.py</pre>
  <p class="small mute">Double-click a tab to detach the display or the controls. Ctrl+S save settings, Ctrl+R reset,
  Ctrl+T toggle controls, F11 fullscreen, Ctrl+Q quit.</p>

  <h2>Run the web app</h2>
  <pre>pip install -r requirements-web.txt
python run_web.py                   # http://127.0.0.1:8125</pre>
  <p>The local server serves this front end and a small JSON API read from the desktop app's modules: the physics
  constants and control specs (<code>/api/defaults</code>, from <code>config.py</code> and <code>ui_specs.py</code>),
  the pattern shapes (<code>/api/patterns</code>) and seeded reference runs of the Python models
  (<code>/api/reference</code>). The GitHub Pages site is the same front end with those answers exported to JSON by
  <code>scripts/build_static.py</code>, so it works without a server. In the web display: L launch, Space pause,
  T toggle controls, F fullscreen, R reset, S save settings (kept in this browser).</p>

  <h2>Credits</h2>
  <p>By George Dickinson, MIT licence. Web version built with AI assistance from <a href="https://claude.com/" rel="noopener">Claude
  (Anthropic)</a>. Source: <a href="https://github.com/gddickinson/fireworks">github.com/gddickinson/fireworks</a>.</p>`;
});
