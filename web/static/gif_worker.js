// Module Worker wrapping gif_encoder.js so GIF export never blocks the page.
//   new Worker(new URL('./gif_worker.js', import.meta.url), { type: 'module' })
// Main -> worker: {type:'start', width, height, delayCs, dither, total, loop?, maxColors?}; {type:'frame', rgba}
// (ArrayBuffer, transferred) per frame; {type:'finish'}; {type:'cancel'} at any time.
// Worker -> main: {type:'progress', done, total} while encoding; {type:'done', bytes} (Uint8Array, buffer transferred);
// {type:'cancelled'}; {type:'error', message}.
// Frames are buffered until 'finish' so one global palette can be built from a sample of all of them; encoding yields
// to the event loop between frames so a 'cancel' arriving mid-encode is seen.
import { quantize, GifWriter } from './gif_encoder.js';

let job = null;
const post = (m, t) => self.postMessage(m, t || []);
const tick = () => new Promise(r => setTimeout(r, 0));

async function encode(j) {
  const { width, height, delayCs = 5, dither = true, loop = 0, maxColors = 256, frames } = j;
  if (!frames.length) throw new Error('no frames to encode');
  const pal = quantize(frames, maxColors);
  await tick();
  if (j.cancelled) return;
  const gw = new GifWriter(width, height, { loop, palette: pal, delayCs });
  for (let i = 0; i < frames.length; i++) {
    gw.addFrame(frames[i], { dither });
    frames[i] = null;                                          // release memory as we go
    post({ type: 'progress', done: i + 1, total: frames.length });
    if ((i & 3) === 3) { await tick(); if (j.cancelled) return; }
  }
  const bytes = gw.finish();
  if (!j.cancelled) post({ type: 'done', bytes }, [bytes.buffer]);
}

self.onmessage = async ({ data: m }) => {
  try {
    if (m.type === 'start') job = { ...m, frames: [], cancelled: false };
    else if (m.type === 'frame') {
      if (!job) throw new Error("'frame' before 'start'");
      const n = job.width * job.height * 4, r = m.rgba;
      const a = ArrayBuffer.isView(r) ? new Uint8Array(r.buffer, r.byteOffset, r.byteLength) : new Uint8Array(r);
      if (a.length < n) throw new Error(`frame ${job.frames.length} has ${a.length} bytes, expected ${n}`);
      job.frames.push(a);
    } else if (m.type === 'finish') {
      if (!job) throw new Error("'finish' before 'start'");
      const j = job;
      await encode(j);
      if (job === j) job = null;
    } else if (m.type === 'cancel') {
      if (job) job.cancelled = true;
      job = null;
      post({ type: 'cancelled' });
    }
  } catch (e) {
    job = null;
    post({ type: 'error', message: String(e && e.message || e) });
  }
};
