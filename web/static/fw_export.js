// Exports of the realistic display, all in the browser: PNG/WebP stills, animated GIF (gif_worker.js, own encoder)
// and video (MediaRecorder: MP4/H.264 where supported, else WebM). Captures step the simulation at a fixed time step
// while the live loop is paused, so a recording never stutters or skips on a slow device: GIFs are fully
// deterministic; videos are paced in real time (a device that cannot keep up gives a slower-paced but smooth file).
const sleep = ms => new Promise(r => setTimeout(r, ms));

export const VIDEO_TYPES = ['video/mp4;codecs=avc1.42E01E,mp4a.40.2', 'video/mp4;codecs=avc1', 'video/mp4',
  'video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm'];
export function bestVideoType() {
  if (typeof MediaRecorder === 'undefined' || !HTMLCanvasElement.prototype.captureStream) return null;
  return VIDEO_TYPES.find(t => MediaRecorder.isTypeSupported(t)) || null;
}
export const videoExt = type => (type && type.startsWith('video/mp4') ? 'mp4' : 'webm');

export function canvasBlob(canvas, type = 'image/png', quality = 0.92) {
  return new Promise((res, rej) => canvas.toBlob(b => (b ? res(b) : rej(new Error(type + ' not supported'))), type, quality));
}
export async function still(V, type = 'image/png') {
  V.draw();                                                   // render and read back in the same task (WebGL)
  const b = await canvasBlob(V.canvas, type);
  if (b.type !== type) throw new Error(type + ' is not supported by this browser');
  return b;
}

// opts: { seconds, fps, width, dither, onProgress(phase, done, total), signal }
export async function recordGIF(V, { seconds = 5, fps = 15, width = 480, dither = true, onProgress = () => {}, signal } = {}) {
  const per = Math.max(1, Math.round(60 / fps)), frames = Math.round(seconds * 60 / per);
  const w = Math.round(width / 2) * 2, h = Math.round(width * V.canvas.height / V.canvas.width / 2) * 2;
  const off = document.createElement('canvas'); off.width = w; off.height = h;
  const c = off.getContext('2d', { willReadFrequently: true });
  const worker = new Worker(new URL('./gif_worker.js', import.meta.url), { type: 'module' });
  const wasPaused = V.paused; V.paused = true; V.capturing = true;
  try {
    const done = new Promise((res, rej) => {
      worker.onmessage = e => {
        const m = e.data;
        if (m.type === 'progress') onProgress('encode', m.done, m.total);
        else if (m.type === 'done') res(new Blob([m.bytes], { type: 'image/gif' }));
        else if (m.type === 'cancelled') rej(new DOMException('cancelled', 'AbortError'));
        else if (m.type === 'error') rej(new Error(m.message));
      };
      worker.onerror = e => rej(new Error(e.message || 'GIF worker failed'));
    });
    worker.postMessage({ type: 'start', width: w, height: h, delayCs: Math.round(100 * per / 60), dither, total: frames, loop: 0 });
    for (let i = 0; i < frames; i++) {
      if (signal?.aborted) throw new DOMException('cancelled', 'AbortError');
      for (let s = 0; s < per; s++) V.step();
      V.draw();
      c.drawImage(V.canvas, 0, 0, w, h);
      const px = c.getImageData(0, 0, w, h).data;
      worker.postMessage({ type: 'frame', rgba: px.buffer }, [px.buffer]);
      onProgress('capture', i + 1, frames);
      if (i % 3 === 2) await sleep(0);
    }
    signal?.addEventListener('abort', () => worker.postMessage({ type: 'cancel' }));
    worker.postMessage({ type: 'finish' });
    return await done;
  } finally {
    V.paused = wasPaused; V.capturing = false;
    setTimeout(() => worker.terminate(), 100);
  }
}

// opts: { seconds, fps, audio (MediaStream or null), onProgress(phase, done, total), signal }
export async function recordVideo(V, { seconds = 10, fps = 30, audio = null, onProgress = () => {}, signal } = {}) {
  const type = bestVideoType();
  if (!type) throw new Error('This browser cannot record video from a canvas');
  const stream = V.canvas.captureStream(fps);
  if (audio) for (const t of audio.getAudioTracks()) stream.addTrack(t);
  const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 8e6 }), chunks = [];
  rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
  const stopped = new Promise(r => { rec.onstop = r; });
  const per = Math.round(60 / fps), frames = Math.round(seconds * fps), wasPaused = V.paused;
  V.paused = true;
  rec.start(500);
  const t0 = performance.now();
  try {
    for (let i = 0; i < frames; i++) {
      if (signal?.aborted) throw new DOMException('cancelled', 'AbortError');
      for (let s = 0; s < per; s++) V.step();
      V.draw();
      onProgress('record', i + 1, frames);
      const wait = t0 + (i + 1) * 1000 / fps - performance.now();
      await sleep(Math.max(0, wait));
    }
  } finally {
    rec.stop(); await stopped;
    for (const t of stream.getVideoTracks()) t.stop();
    V.paused = wasPaused;
  }
  return new Blob(chunks, { type: type.split(';')[0] });
}

export function downloadBlob(blob, name) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
const asFile = (blob, name) => (typeof File !== 'undefined' ? new File([blob], name, { type: blob.type }) : null);
// Can this browser share files (Web Share API level 2, mostly phones)?
export function canShareFile(blob, name) { const f = asFile(blob, name); return !!(f && navigator.canShare?.({ files: [f] })); }
// Share the file (needs a click: call from a button handler). Falls back to a download.
export async function shareFile(blob, name, title = 'Fireworks') {
  if (canShareFile(blob, name)) {
    try { await navigator.share({ files: [asFile(blob, name)], title }); return 'shared'; }
    catch (e) { if (e.name === 'AbortError') return 'cancelled'; }
  }
  downloadBlob(blob, name);
  return 'downloaded';
}

export const fmtBytes = n => (n > 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.round(n / 1e3) + ' kB');
