// "Export & share" panel (Display and Messages pages): PNG/WebP stills, animated GIF, video; download, then Web Share
// where the browser can share files,
// and copying a link. getView() returns the current RealView; prepare() (optional) is run before a recording (e.g.
// restart the message show); link() (optional) returns a URL to copy; audio() returns a MediaStream or null.
import { esc } from './core.js';
import { estimateGifBytes } from './gif_encoder.js';
import { bestVideoType, canShareFile, downloadBlob, fmtBytes, recordGIF, recordVideo, shareFile, still, videoExt } from './fw_export.js';

const phone = () => Math.min(innerWidth, screen?.width || innerWidth) < 700;
const opt = (vals, sel, fmt = v => v) => vals.map(v => `<option value="${v}"${v === sel ? ' selected' : ''}>${esc(fmt(v))}</option>`).join('');

export function buildExportPanel(host, { getView, prepare = null, link = null, audio = () => null, name = 'fireworks' }) {
  const vt = bestVideoType(), small = phone();
  const widths = small ? [320, 480] : [320, 480, 720], durs = small ? [5, 10, 20] : [5, 10, 20, 30];
  host.innerHTML = `
    <div class="btns"><button class="alt" data-x="png">PNG image</button><button class="alt" data-x="webp">WebP image</button>
      ${link ? '<button class="alt" data-x="link">Copy link</button>' : ''}</div>
    <h4 class="xh">Animated GIF</h4>
    <div class="xrow"><label>Length <select id="g-sec">${opt([3, 5, 8, 10], 5, v => v + ' s')}</select></label>
      <label>Frames/s <select id="g-fps">${opt([10, 15, 20], 15)}</select></label>
      <label>Width <select id="g-w">${opt(widths, 480, v => v + ' px')}</select></label></div>
    <label class="chk"><input type="checkbox" id="g-dither" checked> Dither (smoother glows, bigger file)</label>
    <p class="small mute" id="g-est"></p>
    <div class="btns"><button data-x="gif">Make GIF</button></div>
    <h4 class="xh">Video</h4>
    <div class="xrow"><label>Length <select id="v-sec">${opt(durs, 10, v => v + ' s')}</select></label></div>
    <p class="small mute">${vt ? `Records ${esc(videoExt(vt).toUpperCase())} (${esc(vt.split(';')[0])})${vt.includes('mp4') ? '' : '; MP4 is not available in this browser'}, with sound if it is on.` : 'This browser cannot record video from a canvas.'}</p>
    <div class="btns"><button data-x="video"${vt ? '' : ' disabled'}>Record video</button></div>
    ${prepare ? `<label class="chk"><input type="checkbox" id="x-prep" checked> ${esc(prepare.label)}</label>` : ''}
    <div id="x-busy" hidden><progress id="x-prog" max="1" value="0"></progress> <span class="small" id="x-what"></span>
      <button class="alt" data-x="cancel">Cancel</button></div>
    <p class="small" id="x-out" aria-live="polite"></p>`;
  const $ = s => host.querySelector(s), out = $('#x-out');
  // A prepared recording with its own length (the whole message show) overrides the Length menus, capped.
  const whole = () => (prepare?.seconds && $('#x-prep')?.checked ? prepare.seconds() : 0);
  const secs = (sel, cap) => (whole() ? Math.min(cap, Math.ceil(whole())) : +$(sel).value);
  const est = () => {
    const V = getView(), w = +$('#g-w').value, h = Math.round(w * V.canvas.height / Math.max(1, V.canvas.width));
    const n = secs('#g-sec', 20) * +$('#g-fps').value;
    $('#g-est').textContent = `${whole() ? `Whole show: ${Math.ceil(whole())} s (GIF up to 20 s, video up to 60 s). ` : ''}${n} frames at ${w} × ${h}: about ${fmtBytes(estimateGifBytes(w, h, n) * ($('#g-dither').checked ? 1 : 0.6))} (estimate).`;
  };
  for (const id of ['#g-sec', '#g-fps', '#g-w', '#g-dither', '#x-prep']) $(id)?.addEventListener('change', est);
  host.closest('details')?.addEventListener('toggle', est);
  est();
  let ctl = null, last = null;
  const busy = on => { $('#x-busy').hidden = !on; host.querySelectorAll('button[data-x]:not([data-x=cancel])').forEach(b => { b.disabled = on || (b.dataset.x === 'video' && !vt); }); };
  const progress = (phase, d, t) => { $('#x-prog').value = d / t; $('#x-what').textContent = `${phase} ${d}/${t}`; };
  const finish = async (blob, file, t0) => {
    last = { blob, file };
    downloadBlob(blob, file);
    out.innerHTML = `${esc(file)}: ${fmtBytes(blob.size)}${t0 ? `, made in ${((performance.now() - t0) / 1000).toFixed(1)} s` : ''} (downloaded).
      <span class="btns"><button class="alt" data-x="again">Download again</button>${canShareFile(blob, file) ? '<button class="alt" data-x="share">Share…</button>' : ''}</span>`;
  };
  const run = async (fn) => {
    ctl = new AbortController(); busy(true); out.textContent = '';
    const t0 = performance.now();
    try {
      if (prepare && $('#x-prep')?.checked) prepare.run();
      await fn(ctl.signal, t0);
    } catch (e) { out.textContent = e.name === 'AbortError' ? 'Cancelled.' : 'Export failed: ' + e.message; }
    finally { busy(false); ctl = null; }
  };
  host.addEventListener('click', async e => {
    const x = e.target.closest('button[data-x]')?.dataset.x;
    if (!x) return;
    const V = getView();
    if (x === 'cancel') ctl?.abort();
    else if (x === 'again' && last) downloadBlob(last.blob, last.file);
    else if (x === 'share' && last) out.insertAdjacentText('beforeend', ' ' + await shareFile(last.blob, last.file) + '.');
    else if (x === 'png' || x === 'webp') {
      try { const b = await still(V, 'image/' + x); await finish(b, `${name}.${x}`); }
      catch (err) { out.textContent = err.message; }
    } else if (x === 'link') {
      const url = link();
      try { await navigator.clipboard.writeText(url); out.textContent = 'Link copied.'; }
      catch { out.innerHTML = `Copy this link: <input readonly value="${esc(url)}" aria-label="Link">`; }
    } else if (x === 'gif') run(async (signal, t0) => {
      const b = await recordGIF(V, { seconds: secs('#g-sec', 20), fps: +$('#g-fps').value, width: +$('#g-w').value,
        dither: $('#g-dither').checked, onProgress: progress, signal });
      await finish(b, `${name}.gif`, t0);
    });
    else if (x === 'video') run(async (signal, t0) => {
      const b = await recordVideo(V, { seconds: secs('#v-sec', 60), audio: audio(), onProgress: progress, signal });
      await finish(b, `${name}.${videoExt(vt)}`, t0);
    });
  });
}
