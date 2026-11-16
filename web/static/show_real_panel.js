// Display page: the "Show" controls of the realistic renderer (renderer choice, shell type, finale, sound, wind)
// placed above the desktop app's controls (show_panel.js).
import { esc } from './core.js';
import { LABELS, TYPES } from './fw_shells.js';

export const RENDERERS = [['realistic', 'Realistic (WebGL, 3-D physics)'], ['realistic2d', 'Realistic, 2D canvas (no WebGL)'],
  ['classic', 'Classic (the desktop app\'s model, verified)']];

export function buildShowGroup(host, V, st, actions) {
  const d = document.createElement('details');
  d.className = 'grp'; d.open = true;
  const real = st.renderer !== 'classic';
  d.innerHTML = `<summary>Show</summary><div class="body">
    <label for="renderer">Renderer</label>
    <select id="renderer">${RENDERERS.map(([v, l]) => `<option value="${v}"${v === st.renderer ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>
    <div ${real ? '' : 'hidden'}>
      <label for="shell">Shell type</label>
      <select id="shell"><option value="mixed">Mixed (a real show)</option>${TYPES.map(t => `<option value="${t}"${t === st.shell_type ? ' selected' : ''}>${esc(LABELS[t])}</option>`).join('')}</select>
      <div class="btns"><button id="finale">Start the finale</button><a class="btn alt" href="#/messages">Messages…</a></div>
      <label class="chk" for="sound"><input type="checkbox" id="sound"${st.sound ? ' checked' : ''}> Sound (booms arrive late: sound travels 343 m/s)</label>
    </div>
    <p class="small mute" id="rnote">${real ? 'Pattern, colour, particle count, gravity and launch speed below apply to new shells.'
      : 'The classic display is the JavaScript port of the desktop app, checked number for number on the Python vs JS page.'}</p>
  </div>`;
  host.appendChild(d);
  const q = s => d.querySelector(s);
  q('#renderer').onchange = () => { st.renderer = q('#renderer').value; actions.renderer(); };
  if (real) {
    q('#shell').value = st.shell_type;
    q('#shell').onchange = () => { st.shell_type = q('#shell').value; V.director.shell_type = st.shell_type; };
    q('#finale').onclick = () => actions.finale();
    q('#sound').onchange = () => { st.sound = q('#sound').checked; actions.sound(st.sound); };
    V.director.shell_type = st.shell_type;
  }
}
