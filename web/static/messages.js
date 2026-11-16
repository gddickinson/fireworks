// Messages page (#/messages?m=Happy%20New%20Year&f=serif&c=rainbow&s=85&h=3&bg=Beach): words written in the sky by
// message shells. The text (a sequence of messages, blank line between them) is drawn with a real font, fitted to
// the screen and sampled into star positions (fw_text.js). Everything is in the link, so a greeting can be shared.
import { route, app, onLeave, esc, $ } from './core.js';
import { RealView, reducedMotion } from './real_view.js';
import { FONTS, COLOR_MODES, MAX_CHARS, splitMessages, textPoints } from './fw_text.js';
import { BGS, decodeQuery, encodeQuery } from './msg_link.js';
import { buildExportPanel } from './export_panel.js';
import { audio } from './show.js';
import { hexToRgb, rgbToHex } from './fw_color.js';

const PRESETS = [
  ['New Year', 'Happy New Year!\n\n2027'], ['Birthday', 'Happy Birthday\n{name}!'], ['Congratulations', 'Congratulations!'],
  ['Thank you', 'Thank you'], ['Love', 'I ♥ you'], ['Wedding', 'Just married\n\n{name}'], ['Bonne année', 'Bonne année !'],
  ['Feliz cumpleaños', 'Feliz cumpleaños\n{name}'], ['新年快乐', '新年快乐'], ['Well done 🎉', 'Well done 🎉'],
];
route('messages', async (args, query) => {
  const o = decodeQuery(query);
  app().innerHTML = `
  <div class="msg-page">
    <div class="show-col">
      <div class="show-stage" id="stage"><canvas id="sky"></canvas></div>
      <p class="small mute center" id="lines" aria-live="polite">&nbsp;</p>
    </div>
    <aside class="panel" aria-label="Message controls">
      <h1 class="glow h-small">Messages in the sky</h1>
      <label for="mt">Message (a blank line starts the next message; {name} is replaced)</label>
      <textarea id="mt" maxlength="${MAX_CHARS * 6}">${esc(o.text)}</textarea>
      <label for="mn">Name</label><input id="mn" maxlength="30" value="${esc(o.name)}" placeholder="for {name}">
      <div class="presets" role="group" aria-label="Presets">${PRESETS.map(([l], i) => `<button class="alt" data-p="${i}">${esc(l)}</button>`).join('')}</div>
      <div class="xrow"><label>Font <select id="mf">${Object.entries(FONTS).map(([k, [l]]) => `<option value="${k}"${k === o.font ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select></label>
        <label>Colours <select id="mc">${Object.entries(COLOR_MODES).map(([k, l]) => `<option value="${k}"${k === o.mode ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select></label></div>
      <div class="xrow" id="cols"><label>Colour <input type="color" id="c1" value="${o.c1}"></label><label id="c2l">to <input type="color" id="c2" value="${o.c2}"></label></div>
      <div class="xrow"><label>Size <b id="sv">${o.size}%</b><input type="range" id="ms" min="40" max="100" value="${o.size}"></label>
        <label>Hold <b id="hv">${o.hold} s</b><input type="range" id="mh" min="1" max="8" value="${o.hold}"></label></div>
      <label for="mb">Scene</label><select id="mb">${BGS.map(b => `<option${b === o.bg ? ' selected' : ''}>${esc(b)}</option>`).join('')}</select>
      <label class="chk"><input type="checkbox" id="loop" checked> Repeat</label>
      <label class="chk"><input type="checkbox" id="snd"> Sound</label>
      <div class="btns"><button id="play">Play the message show</button><button class="alt" id="copy">Copy greeting link</button></div>
      <p class="small mute" id="note" aria-live="polite"></p>
      <details class="grp"><summary>Export &amp; share</summary><div class="body" id="xp"></div></details>
    </aside>
  </div>`;
  const V = new RealView($('#sky'), { background: o.bg, label: 'Fireworks writing your message in the sky', seed: 2027 });
  V.show.autoLaunch = false; V.show.use_random_colors = true;
  V.bloom = 0.35;                                            // less glow: letters stay crisp
  V.on(ev => audio.onEvents(ev));
  const ui = {
    get text() { return $('#mt').value; }, get name() { return $('#mn').value.trim(); },
    get font() { return $('#mf').value; }, get mode() { return $('#mc').value; }, get c1() { return $('#c1').value; },
    get c2() { return $('#c2').value; }, get size() { return +$('#ms').value; }, get hold() { return +$('#mh').value; },
    get bg() { return $('#mb').value; },
  };
  const messages = () => splitMessages(ui.text.replace(/\{name\}/g, ui.name || ''));
  const play = () => {
    const list = messages(), out = [];
    for (const m of list) {
      const { points, lines } = textPoints(m, V.sim.aspect, V.sim.horizon, { font: ui.font, mode: ui.mode, color: hexToRgb(ui.c1),
        color2: hexToRgb(ui.c2), size: ui.size / 100,
        density: Math.min(1800, Math.max(500, [...m].length * 115)) * (V.quality < 0.8 ? 0.7 : 1) });
      if (points.length) out.push({ points, hold: ui.hold, lines });
    }
    $('#lines').textContent = out.length ? out.map(m => m.lines.join(' / ')).join('  →  ') : 'Type a message.';
    V.sim.stars = V.sim.stars.filter(s => !s.target);
    if (out.length) V.messages(out);
    if (V.paused && !reducedMotion()) V.paused = false;
    return out.length;
  };
  const sync = () => {
    $('#cols').hidden = !['single', 'gradient'].includes(ui.mode); $('#c2l').hidden = ui.mode !== 'gradient';
    $('#sv').textContent = ui.size + '%'; $('#hv').textContent = ui.hold + ' s';
    history.replaceState(null, '', encodeQuery(ui));
  };
  let timer = 0;
  const changed = () => { sync(); clearTimeout(timer); timer = setTimeout(play, 600); };
  for (const id of ['#mt', '#mn', '#mf', '#mc', '#c1', '#c2', '#ms', '#mh']) $(id).addEventListener('input', changed);
  $('#mb').addEventListener('change', () => { V.setBackground(ui.bg); changed(); });
  $('#snd').addEventListener('change', () => (($('#snd').checked ? audio.enable() : audio.disable())));
  document.querySelector('.presets').addEventListener('click', e => {
    const b = e.target.closest('[data-p]'); if (!b) return;
    $('#mt').value = PRESETS[+b.dataset.p][1];
    if ($('#mt').value.includes('{name}') && !ui.name) $('#mn').value = 'Alex';
    changed();
  });
  $('#play').onclick = play;
  $('#copy').onclick = async () => {
    const url = location.href.split('#')[0] + encodeQuery(ui);
    try { await navigator.clipboard.writeText(url); $('#note').textContent = 'Link copied: anyone opening it sees this show.'; }
    catch { $('#note').innerHTML = `Copy this link: <input readonly value="${esc(url)}" aria-label="Greeting link">`; }
  };
  buildExportPanel($('#xp'), { getView: () => V, name: 'fireworks-message', link: () => location.href.split('#')[0] + encodeQuery(ui),
    audio: () => ($('#snd').checked ? audio.stream() : null), prepare: { label: 'Record the message show from its start (skips the climb)', run: () => { play(); for (let i = 0; i < 270; i++) V.step(); } } });
  V.opts.onFrame = v => {                                    // repeat once the last letters have fallen
    if (v.sim.frame % 30 === 0 && $('#loop').checked && v.director.mode === 'auto'
      && !v.sim.stars.some(s => s.target || s.recipe?.type === 'message')) play();   // incl. message shells still rising
  };
  sync();
  play();
  if (reducedMotion()) { for (let i = 0; i < 150; i++) V.step(); V.paused = true; V.draw(); $('#note').textContent = 'Reduced motion: press Play to animate.'; }
  const stop = V.start().stop;
  onLeave(() => { stop(); V.ro.disconnect(); audio.disable(); });
});
