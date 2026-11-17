// Display page (#/show?pattern=Heart&background=Beach&weather=Snow&random=1&renderer=classic&finale=1): the firework
// display with the desktop app's controls. Default renderer: the realistic one (real_view.js); "Classic" is the
// verified port of the desktop app (show_view.js). Settings can be saved in this browser.
import { route, app, api, onLeave, $ } from './core.js';
import { ShowView } from './show_view.js';
import { RealView, reducedMotion } from './real_view.js';
import { buildPanel } from './show_panel.js';
import { buildShowGroup } from './show_real_panel.js';
import { buildExportPanel } from './export_panel.js';
import { FireworkAudio } from './fw_audio.js';
import { DEFAULT_COLOR } from './fw_engine.js';

const KEY = 'fireworks.settings';
const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; } };
const store = v => { try { localStorage.setItem(KEY, JSON.stringify(v)); return true; } catch { return false; } };
export const audio = new FireworkAudio();

export function defaultSettings(D) {
  const s = Object.fromEntries(D.sliders.map(x => [x.key, x.default]));
  return { ...s, color: [...(D.firework_rgb || DEFAULT_COLOR)], random_colors: true, pattern: 'None', random_patterns: false,
    text: '', background: 'Cityscape', weather: 'None', auto_launch: true, renderer: 'realistic', shell_type: 'mixed', sound: false, lift_time: 3, time_of_day: 'night', sky_fx: [] };
}

route('show', async (args, query) => {
  const D = await api('/defaults');
  const st = { ...defaultSettings(D), ...(load() || {}) };
  st.sound = false;                                           // never start noisy; needs a click anyway
  if (query.pattern) st.pattern = query.pattern;
  if (query.background) st.background = query.background;
  if (query.weather) st.weather = query.weather;
  if (query.random) st.random_colors = true;
  if (['realistic', 'realistic2d', 'classic'].includes(query.renderer)) st.renderer = query.renderer;
  app().innerHTML = `
    <div class="show-page">
      <div class="show-col">
        <div class="show-stage" id="stage"></div>
        <p class="small mute center" id="stats" aria-live="off">&nbsp;</p>
        <p class="small mute center">Click the sky to launch there · L launch · G finale · Space pause · T toggle controls · F fullscreen · R reset · S save settings</p>
      </div>
      <aside class="panel show-panel" id="panel" aria-label="Display controls">
        <h1 class="glow h-small">Firework display</h1>
        <div id="ctl"></div>
        <details class="grp" id="xgrp"><summary>Export &amp; share</summary><div class="body" id="xp"></div></details>
      </aside>
    </div>`;
  let el = null, V = null, stop = () => {};
  const stats = s => {
    if (s.R) { const t = s.stats(); $('#stats').textContent = `${t.stars} stars and sparks · ${t.renderer}${t.scale < 1 ? ` · resolution ${Math.round(t.scale * 100)}%` : ''}${t.quality < 1 ? ` · particles ${Math.round(t.quality * 100)}%` : ''}`; }
    else $('#stats').textContent = `${s.fireworks.length} fireworks · ${s.particleCount()} particles in the air`;
  };
  const makeView = () => {
    stop(); V?.ro?.disconnect();
    $('#stage').innerHTML = '<canvas id="sky"></canvas>';
    const opts = { label: 'Animated fireworks display (click to launch)', background: st.background, weather: st.weather };
    if (st.renderer === 'classic') V = new ShowView($('#sky'), { ...opts, onFrame: s => { if (s.frame % 15 === 0) stats(s); } });
    else {
      V = new RealView($('#sky'), { ...opts, renderer: st.renderer === 'realistic2d' ? '2d' : 'auto', onFrame: v => { if (v.sim.frame % 20 === 0) stats(v); } });
      V.on(ev => audio.onEvents(ev));
    }
    $('#ctl').innerHTML = '';
    buildShowGroup($('#ctl'), V, st, actions);
    el = buildPanel($('#ctl'), V, D, st, actions);
    if (V.R) cameraGroup($('#ctl'), V, st, el);
    $('#xgrp').hidden = st.renderer === 'classic';
    if (V.R) buildExportPanel($('#xp'), { getView: () => V, audio: () => (st.sound ? audio.stream() : null),
      prepare: { label: 'Record the finale (skips the first shells\' climb)', run: () => { V.finale(); for (let i = 0; i < 300; i++) V.step(); } } });
    if (query.finale && V.finale) V.finale();
    if (reducedMotion()) {                                    // a still frame; Play starts it
      if (V.R) for (let i = 0; i < 600; i++) V.step();
      V.paused = true; el.pauseBtn.textContent = 'Play'; V.draw();
    }
    stop = V.start().stop;
    onLeave(leave);                                           // V.start() registered only its own stop
  };
  const actions = {
    launch: () => (V.launch ? V.launch() : V.show.add_firework()),
    pause: () => { V.paused = !V.paused; if (!V.paused) V.longExposure = false; el.pauseBtn.textContent = V.paused ? 'Resume' : 'Pause'; },
    png: () => { const a = document.createElement('a'); a.href = V.toPNG(); a.download = 'fireworks.png'; a.click(); },
    save: () => { el.savedNote.textContent = store(st) ? 'Settings saved in this browser.' : 'Could not save (storage blocked).'; },
    reset: () => {
      if (!confirm('Reset all settings to defaults?')) return;
      try { localStorage.removeItem(KEY); } catch { /* storage blocked */ }
      Object.assign(st, defaultSettings(D)); makeView();
    },
    full: () => { const s = $('#stage'); if (document.fullscreenElement) document.exitFullscreen(); else s.requestFullscreen?.(); },
    toggle: () => { $('#panel').hidden = !$('#panel').hidden; $('.show-page').classList.toggle('solo', $('#panel').hidden); },
    renderer: () => makeView(),
    finale: () => V.finale?.(),
    sound: on => { if (on) audio.enable(); else audio.disable(); },
  };
  const keys = e => {
    if (e.target.closest('input, select, textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
    const map = { l: 'launch', ' ': 'pause', t: 'toggle', f: 'full', r: 'reset', s: 'save', g: 'finale' };
    const k = e.key.toLowerCase();
    if (map[k] && !(k === ' ' && e.target.closest('button, summary, a'))) { e.preventDefault(); actions[map[k]](); }
  };
  const leave = () => { stop(); V?.ro?.disconnect(); audio.disable(); document.removeEventListener('keydown', keys); };
  document.addEventListener('keydown', keys);
  makeView();
});

// Camera options of the realistic display: handheld sway and a long-exposure photo (trails build into one still).
function cameraGroup(host, V, st, el) {
  const d = document.createElement('details');
  d.className = 'grp';
  d.innerHTML = `<summary>Camera</summary><div class="body">
    <label class="chk"><input type="checkbox" id="sway"${st.sway ? ' checked' : ''}> Handheld (slight sway)</label>
    <div class="btns"><button class="alt" id="photo">Long-exposure photo (6 s)</button></div>
    <p class="small mute" id="photonote">Like a camera on a tripod with the shutter open: trails build up into one picture, then it pauses (Save PNG keeps it, Resume goes on).</p></div>`;
  host.appendChild(d);
  const sway = d.querySelector('#sway');
  V.sway = !!st.sway;
  sway.onchange = () => { st.sway = sway.checked; V.sway = st.sway; };
  d.querySelector('#photo').onclick = async () => {
    const b = d.querySelector('#photo'); b.disabled = true; d.querySelector('#photonote').textContent = 'Exposing…';
    await V.photo(6);
    b.disabled = false; el.pauseBtn.textContent = 'Resume';
    d.querySelector('#photonote').textContent = 'Done: Save PNG keeps the photo, Resume goes on.';
  };
}
