// Display page: the "Show" controls of the realistic renderer (renderer choice, shell type, finale, sound, wind)
// placed above the desktop app's controls (show_panel.js).
import { esc } from './core.js';
import { LABELS, TYPES } from './fw_shells.js';
import { SKY_FX } from './fw_fx.js';

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
      <label for="lift">Lift time <b id="liftv"></b></label>
      <input type="range" id="lift" min="1.5" max="5" step="0.5" value="${st.lift_time ?? 3}">
      <p class="small mute">A real 150 m shell climbs for about 4.5 s; shorter lift times play the same climb faster. 5 = real time.</p>
      <label for="tod">Time of day</label>
      <select id="tod"><option value="night">Night</option><option value="dusk"${st.time_of_day === 'dusk' ? ' selected' : ''}>Dusk (blue hour)</option></select>
      <fieldset class="fx"><legend class="small">Sky effects</legend>${Object.entries(SKY_FX).map(([k, f]) =>
        `<label class="chk"><input type="checkbox" data-fx="${esc(k)}"${(st.sky_fx || []).includes(k) ? ' checked' : ''}> ${esc(f.label)}</label>`).join('') || '<span class="small mute">none</span>'}</fieldset>
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
    const lift = q('#lift'), show = () => { const v = +lift.value; q('#liftv').textContent = v >= 5 ? 'real time' : v + ' s'; V.liftTime = v >= 5 ? null : v; st.lift_time = v; };
    lift.oninput = show; show();
    q('#tod').onchange = () => { st.time_of_day = q('#tod').value; V.setTimeOfDay(st.time_of_day); };
    const fx = () => { st.sky_fx = [...d.querySelectorAll('[data-fx]:checked')].map(x => x.dataset.fx); V.setSkyFx(st.sky_fx); };
    d.querySelectorAll('[data-fx]').forEach(x => { x.onchange = fx; });
    if (st.time_of_day === 'dusk') V.setTimeOfDay('dusk');
    if ((st.sky_fx || []).length) fx();
  }
}
