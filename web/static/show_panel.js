// Control panel of the display page: the browser version of gui/controls.py (ControlPanel). Choice lists, slider
// ranges, defaults and scales come from /api/defaults (ui_specs.py, shared with the desktop panel).
import { esc, list, slider } from './core.js';
import { hexToRgb, rgbToHex } from './fw_color.js';

const group = (host, title) => {
  const d = document.createElement('details');
  d.className = 'grp'; d.open = true;
  d.innerHTML = `<summary>${esc(title)}</summary><div class="body"></div>`;
  host.appendChild(d);
  return d.querySelector('.body');
};
const select = (id, label, options, value) => `<label for="${id}">${esc(label)}</label>
  <select id="${id}">${list(options, ([v, l]) => `<option value="${esc(v)}"${v === value ? ' selected' : ''}>${esc(l)}</option>`)}</select>`;
const check = (id, label, on) => `<label class="chk" for="${id}"><input type="checkbox" id="${id}"${on ? ' checked' : ''}> ${esc(label)}</label>`;

export function setSlider(input, v) {
  input.value = v;
  input.dispatchEvent(new Event('input'));
}

// Build into host. V: ShowView, D: /api/defaults, st: settings object (see show.js). Returns the inputs by key.
export function buildPanel(host, V, D, st, actions) {
  const S = V.show, spec = Object.fromEntries(D.sliders.map(s => [s.key, s])), el = {};
  const sl = (h, key, fn, fmt) => {
    const s = spec[key];
    el[key] = slider(h, { id: key, label: s.label, min: s.lo, max: s.hi, value: st[key] ?? s.default, fmt }, v => { st[key] = v; fn(v * s.scale); });
    return el[key];
  };

  // Particle Controls
  const pc = group(host, 'Particles');
  sl(pc, 'particle_count', v => { S.particle_count = v; });

  // Color Controls
  const cc = group(host, 'Colour');
  cc.innerHTML = `<label for="color">Firework colour <input type="color" id="color" value="${rgbToHex(st.color)}"></label>
    ${check('random_colors', 'Random colours', st.random_colors)}`;
  el.color = cc.querySelector('#color'); el.random_colors = cc.querySelector('#random_colors');
  el.color.oninput = () => { st.color = hexToRgb(el.color.value); S.firework_color = st.color; };
  el.random_colors.onchange = () => {
    st.random_colors = el.random_colors.checked; S.use_random_colors = st.random_colors; el.color.disabled = st.random_colors;
  };

  // Pattern Controls
  const pt = group(host, 'Pattern');
  const pats = [['None', 'None: plain burst (as in the desktop app)'], ...D.patterns.map(p => [p, p])];
  pt.innerHTML = `${select('pattern', 'Pattern', pats, st.pattern)}${check('random_patterns', 'Randomize patterns', st.random_patterns)}
    <div id="popts"></div><div id="pspec"></div>
    <p class="small mute" id="pnote"></p>`;
  el.pattern = pt.querySelector('#pattern'); el.random_patterns = pt.querySelector('#random_patterns');
  const popts = pt.querySelector('#popts'), pspec = pt.querySelector('#pspec'), pnote = pt.querySelector('#pnote');
  sl(popts, 'pattern_scale', v => S.set_pattern_scale(v), v => (v / 100).toFixed(1));
  sl(popts, 'pattern_rotation', v => S.set_pattern_rotation(v * Math.PI / 180), v => v + '°');
  const star = document.createElement('div'), spiral = document.createElement('div'), text = document.createElement('div');
  pspec.append(star, spiral, text);
  sl(star, 'star_points', v => S.set_pattern_option('star_points', v));
  sl(spiral, 'spiral_arms', v => S.set_pattern_option('spiral_arms', v));
  text.innerHTML = `<label for="ptext">Text</label><input id="ptext" placeholder="Enter text..." value="${esc(st.text)}">`;
  el.text = text.querySelector('input');
  el.text.oninput = () => { st.text = el.text.value; S.set_pattern_option('text', st.text); };
  const showSpec = name => {
    star.hidden = name !== 'Star'; spiral.hidden = name !== 'Spiral'; text.hidden = name !== 'Text';
    popts.classList.toggle('dim', st.random_patterns);
    pnote.textContent = name === 'Text' ? 'Only the letter A has a shape in patterns.py; other letters burst normally.'
      : name === 'Random' ? 'One random shape (circle, heart, star, spiral or double ring) for every rocket until changed.' : '';
  };
  el.pattern.onchange = () => { st.pattern = el.pattern.value; S.set_pattern(st.pattern); showSpec(st.pattern); };
  el.random_patterns.onchange = () => {
    st.random_patterns = el.random_patterns.checked;
    if (st.random_patterns && st.pattern !== 'Random') { el.pattern.value = 'Random'; el.pattern.onchange(); }
    S.set_random_patterns(st.random_patterns); showSpec(st.pattern);
  };

  // Physics Controls
  const ph = group(host, 'Physics');
  sl(ph, 'gravity', v => { S.gravity = v; }, v => (v / 100).toFixed(2));
  sl(ph, 'launch_speed', v => { S.launchSpeed = v; }, v => (v / 10).toFixed(1));
  ph.insertAdjacentHTML('beforeend', '<p class="small mute">Apply to new rockets.</p>');

  // Background Controls
  const bg = group(host, 'Scene');
  bg.innerHTML = `${select('background', 'Background', [['None', 'None'], ...D.backgrounds.map(b => [b, b])], st.background)}
    ${select('weather', 'Weather effect', D.weather.map(w => [w, w]), st.weather)}`;
  el.background = bg.querySelector('#background'); el.weather = bg.querySelector('#weather');
  el.background.onchange = () => { st.background = el.background.value; V.setBackground(st.background); };
  el.weather.onchange = () => { st.weather = el.weather.value; V.setWeather(st.weather); };

  // Launch Controls
  const lc = group(host, 'Launch');
  lc.innerHTML = `${check('auto_launch', 'Auto launch', st.auto_launch)}
    <div class="btns"><button id="launch">Launch firework</button><button class="alt" id="pause">Pause</button>
    <button class="alt" id="png">Save PNG</button></div>
    <div class="btns"><button class="alt" id="save">Save settings</button><button class="alt" id="reset">Reset</button>
    <button class="alt" id="full">Fullscreen</button></div><p class="small mute" id="saved" aria-live="polite"></p>`;
  el.auto_launch = lc.querySelector('#auto_launch');
  el.auto_launch.onchange = () => { st.auto_launch = el.auto_launch.checked; S.autoLaunch = st.auto_launch; };
  for (const id of ['launch', 'pause', 'png', 'save', 'reset', 'full']) lc.querySelector('#' + id).onclick = actions[id];
  el.pauseBtn = lc.querySelector('#pause'); el.savedNote = lc.querySelector('#saved');

  // Apply the starting settings to the show.
  S.particle_count = st.particle_count; S.firework_color = st.color; S.use_random_colors = st.random_colors;
  el.color.disabled = st.random_colors;
  S.pattern_scale = st.pattern_scale * spec.pattern_scale.scale; S.pattern_rotation = st.pattern_rotation * Math.PI / 180;
  S.pattern_options = { star_points: st.star_points, spiral_arms: st.spiral_arms, text: st.text };
  S.set_pattern(st.pattern); if (st.random_patterns) S.set_random_patterns(true); showSpec(st.pattern);
  S.gravity = st.gravity * spec.gravity.scale; S.launchSpeed = st.launch_speed * spec.launch_speed.scale;
  S.autoLaunch = st.auto_launch;
  V.setBackground(st.background); V.setWeather(st.weather);
  return el;
}
