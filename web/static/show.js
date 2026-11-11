// Display page (#/show?pattern=Heart&background=Beach&weather=Snow&random=1): the full firework display with the
// desktop app's controls. Settings can be saved in this browser (the desktop app keeps them in QSettings).
import { route, app, api, onLeave, download, $ } from './core.js';
import { ShowView } from './show_view.js';
import { buildPanel } from './show_panel.js';
import { DEFAULT_COLOR } from './fw_engine.js';

const KEY = 'fireworks.settings';
const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; } };
const store = v => { try { localStorage.setItem(KEY, JSON.stringify(v)); return true; } catch { return false; } };

export function defaultSettings(D) {
  const s = Object.fromEntries(D.sliders.map(x => [x.key, x.default]));
  return { ...s, color: [...(D.firework_rgb || DEFAULT_COLOR)], random_colors: false, pattern: 'None', random_patterns: false,
    text: '', background: 'Night Sky', weather: 'None', auto_launch: true };
}

route('show', async (args, query) => {
  const D = await api('/defaults');
  const st = { ...defaultSettings(D), ...(load() || {}) };
  if (query.pattern) st.pattern = query.pattern;
  if (query.background) st.background = query.background;
  if (query.weather) st.weather = query.weather;
  if (query.random) { st.random_colors = true; }
  app().innerHTML = `
    <div class="show-page">
      <div class="show-col">
        <div class="show-stage" id="stage"><canvas id="sky"></canvas></div>
        <p class="small mute center" id="stats" aria-live="off">&nbsp;</p>
        <p class="small mute center">Click the sky to launch at that spot · L launch · Space pause · T toggle controls · F fullscreen · R reset · S save settings</p>
      </div>
      <aside class="panel show-panel" id="panel" aria-label="Display controls">
        <h1 class="glow h-small">Firework display</h1>
        <div id="ctl"></div>
      </aside>
    </div>`;
  let el = null;
  const V = new ShowView($('#sky'), { label: 'Animated fireworks display (click to launch)',
    onFrame: s => { if (s.frame % 15 === 0) $('#stats').textContent = `${s.fireworks.length} fireworks · ${s.particleCount()} particles in the air`; } });
  const actions = {
    launch: () => V.show.add_firework(),
    pause: () => { V.paused = !V.paused; el.pauseBtn.textContent = V.paused ? 'Resume' : 'Pause'; },
    png: () => fetch(V.toPNG()).then(r => r.blob()).then(b => download('fireworks.png', b)),
    save: () => { el.savedNote.textContent = store(st) ? 'Settings saved in this browser.' : 'Could not save (storage blocked).'; },
    reset: () => {
      if (!confirm('Reset all settings to defaults?')) return;
      try { localStorage.removeItem(KEY); } catch { /* storage blocked */ }
      Object.assign(st, defaultSettings(D)); V.show.fireworks = [];
      rebuild();
    },
    full: () => { const s = $('#stage'); if (document.fullscreenElement) document.exitFullscreen(); else s.requestFullscreen?.(); },
    toggle: () => { $('#panel').hidden = !$('#panel').hidden; $('.show-page').classList.toggle('solo', $('#panel').hidden); },
  };
  const rebuild = () => { $('#ctl').innerHTML = ''; el = buildPanel($('#ctl'), V, D, st, actions); };
  rebuild();
  const keys = e => {
    if (e.target.closest('input, select, textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
    const map = { l: 'launch', ' ': 'pause', t: 'toggle', f: 'full', r: 'reset', s: 'save' };
    const k = e.key.toLowerCase();
    if (map[k] && !(k === ' ' && e.target.closest('button, summary, a'))) { e.preventDefault(); actions[map[k]](); }
  };
  document.addEventListener('keydown', keys);
  const stop = V.start().stop;
  onLeave(() => { stop(); V.ro.disconnect(); document.removeEventListener('keydown', keys); });
});
