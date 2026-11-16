// About page: what the simulator does (from the README and the code), what the web version adds, how to run both.
import { route, api, app, esc } from './core.js';

route('about', async () => {
  const [info, D] = await Promise.all([api('/info'), api('/defaults')]);
  const F = D.firework, sl = Object.fromEntries(D.sliders.map(s => [s.key, s]));
  app().innerHTML = `
  <h1 class="glow">About</h1>
  <p class="lead">${esc(info.summary)} Version ${esc(info.version)}. A desktop app (Python, PyQt6) and this web version,
  which runs JavaScript copies of the same Python models in the browser.</p>

  <h2>The realistic display (default)</h2>
  <p>Python <code>models/pyro.py</code>, <code>shell_types.py</code> and <code>director.py</code>, copied to JavaScript
  and checked against seeded Python runs (<a href="#/verify">Python vs JS</a>):</p>
  <ul>
    <li><b>Physics in metres and seconds</b>: shells are fired from 300 to 600 m away with the speed that reaches the
      chosen height against gravity (9.81 m/s²) and quadratic air drag; they burst at the top. Every star then feels
      drag a = −k|v − wind|(v − wind): it leaves at 30 to 70 m/s, slows within a second or two towards its terminal
      speed √(g/k) and droops. A pinhole camera projects the 3-D positions, so distant shells look smaller and dimmer.</li>
    <li><b>${info.shell_types} shell types</b>: peony, chrysanthemum (spark tails), willow, kamuro (glittering gold crown),
      palm (comets), crossette (stars that split in four), ring (tilted in 3-D), horsetail, crackle (delayed pops),
      strobe, multi-break (sub-shells), plus salutes in the finale; stars may change colour mid-flight or carry a
      pistil of a second colour. Colours are those of real emitters (strontium red, barium green, copper blue,
      sodium yellow, charcoal gold, titanium silver); each star flashes white-hot at ignition and cools to an orange ember.</li>
    <li><b>Finale</b>: a 40-second programme (pairs, a fan of palms, crossettes and rings, a willow curtain, strobes,
      a crescendo and a salute barrage). <b>Messages</b>: stars burst, glide into the dots of a text drawn with a real
      font, hold, sparkle and fall.</li>
    <li><b>Rendering</b> (browser only, not part of the Python check): WebGL2 with HDR additive stars, short exposure
      trails, a three-level bloom, smoke puffs lit by the bursts, burst light on the scenery and the sky, rippled
      reflections on water, tone mapping, vignette and grain; a 2D-canvas fallback without WebGL. Scenes are painted
      once per size from seeded noise: night skies with airglow and light pollution, star fields with a range of
      magnitudes and the Milky Way, fractal ridgelines fading into haze, a harbour skyline with lit windows. The drawing
      resolution and particle budget drop automatically if frames take too long.</li>
    <li><b>Sound</b> (off until you switch it on): synthesised launch thumps, booms and crackles, each delayed by the
      distance over the speed of sound.</li>
    <li><b>Export</b>: PNG/WebP stills, animated GIF (an encoder in this site, run in a Web Worker) and video (MP4 or
      WebM, whatever the browser records), all made in the browser from a fixed-time-step replay.</li>
  </ul>

  <h2>The classic display (the desktop app's model)</h2>
  <p>Every frame (${F.FRAME_RATE} per second; the desktop timer ticks every ${Math.floor(1000 / F.FRAME_RATE)} ms):</p>
  <ul>
    <li><b>Launch</b>: with probability ${F.SPAWN_RATE} a rocket starts at a random x along the bottom edge with an
      upward speed between ${F.LAUNCH_SPEED_MIN} and ${F.LAUNCH_SPEED_MAX} pixels per frame.</li>
    <li><b>Climb</b>: gravity (${F.GRAVITY} px/frame²) slows it; when its vertical velocity reaches zero, at the top of
      its flight, it bursts.</li>
    <li><b>Pattern</b>: with an explosion pattern (see <a href="#/patterns">Patterns</a>) each pattern point becomes one
      particle flying outwards, so the burst grows into the shape.</li>
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
  <p>The classic JavaScript port matches the Python models number for number (see <a href="#/verify">Python vs JS</a>),
  including gravity (${sl.gravity.lo * sl.gravity.scale} to ${sl.gravity.hi * sl.gravity.scale}) and launch speed
  (${sl.launch_speed.lo * sl.launch_speed.scale} to ${sl.launch_speed.hi * sl.launch_speed.scale}; 10 keeps the
  ${F.LAUNCH_SPEED_MIN} to ${F.LAUNCH_SPEED_MAX} range, other values scale it). Additions of the web version:</p>
  <ul>
    <li><b>"None" pattern</b>: plain random bursts with the chosen particle count (the desktop list starts at Random).</li>
    <li><b>Click to launch</b> at the clicked spot, keyboard shortcuts, pause and PNG export.</li>
    <li>The realistic display, messages, sound and exports described above.</li>
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
  T toggle controls, F fullscreen, R reset, S save settings (kept in this browser), G finale.</p>

  <h2>Credits</h2>
  <p>By George Dickinson, MIT licence. Web version built with AI assistance from <a href="https://claude.com/" rel="noopener">Claude
  (Anthropic)</a>. Source: <a href="https://github.com/gddickinson/fireworks">github.com/gddickinson/fireworks</a>.</p>`;
});
