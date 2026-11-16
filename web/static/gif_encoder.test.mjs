// node gif_encoder.test.mjs: the GIF encoder against an independent minimal GIF decoder written here (block parser +
// LZW decoder), a hand-derived byte-exact tiny GIF, a >4096-code LZW stream and the palette's dark/bright handling.
import assert from 'node:assert/strict';
import { quantize, GifWriter, encodeGIF, estimateGifBytes } from './gif_encoder.js';

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('ok  ', name); };

// --- minimal decoder --------------------------------------------------------------------------------------------
function lzwDecode(data, minCode, npix) {
  const clear = 1 << minCode, eoi = clear + 1, out = new Uint8Array(npix);
  const pre = new Int32Array(4096), suf = new Uint8Array(4096), len = new Int32Array(4096);
  let size, next, prev = -1, o = 0, bit = 0;
  const reset = () => { size = minCode + 1; next = eoi + 1; prev = -1; };
  for (let i = 0; i < clear; i++) { pre[i] = -1; suf[i] = i; len[i] = 1; }
  reset();
  const first = c => { while (pre[c] >= 0) c = pre[c]; return suf[c]; };
  const write = c => { const L = len[c]; for (let at = o + L - 1; at >= o; at--, c = pre[c]) out[at] = suf[c]; o += L; };
  for (;;) {
    if (bit + size > data.length * 8) throw new Error('LZW data ended before EOI');
    let c = 0;
    for (let k = 0; k < size; k++, bit++) c |= ((data[bit >> 3] >> (bit & 7)) & 1) << k;
    if (c === clear) { reset(); continue; }
    if (c === eoi) break;
    if (prev < 0) { write(c); prev = c; continue; }
    if (c > next) throw new Error(`bad code ${c} > ${next}`);
    const k = c < next ? first(c) : first(prev);
    if (next < 4096) { pre[next] = prev; suf[next] = k; len[next] = len[prev] + 1; next++; }
    write(c);
    if (next === 1 << size && size < 12) size++;
    prev = c;
  }
  assert.equal(o, npix, 'decoded pixel count');
  return out;
}

function decodeGIF(b) {
  const u16 = p => b[p] | (b[p + 1] << 8);
  assert.equal(String.fromCharCode(...b.subarray(0, 6)), 'GIF89a');
  const width = u16(6), height = u16(8), flags = b[10];
  let p = 13, gct = null, loop = null;
  const table = f => { const sz = 3 << ((f & 7) + 1), t = b.subarray(p, p + sz); p += sz; return t; };
  if (flags & 0x80) gct = table(flags);
  const subBlocks = () => { const parts = []; while (b[p]) { parts.push(b.subarray(p + 1, p + 1 + b[p])); p += b[p] + 1; } p++; return parts; };
  const frames = [], canvas = new Uint8Array(width * height * 3);
  let gce = null;
  for (;;) {
    const t = b[p++];
    if (t === 0x3b) break;
    if (t === 0x21) {
      const label = b[p++], parts = subBlocks();
      if (label === 0xf9) {
        const g = parts[0];
        gce = { disposal: (g[0] >> 2) & 7, delay: g[1] | (g[2] << 8), transparent: g[0] & 1 ? g[3] : -1 };
      }
      if (label === 0xff && String.fromCharCode(...parts[0]) === 'NETSCAPE2.0') loop = parts[1][1] | (parts[1][2] << 8);
    } else if (t === 0x2c) {
      const left = u16(p), top = u16(p + 2), w = u16(p + 4), h = u16(p + 6), f = b[p + 8];
      assert.ok(left + w <= width && top + h <= height, 'frame inside the logical screen');
      p += 9;
      const pal = f & 0x80 ? table(f) : gct, minCode = b[p++];
      const parts = subBlocks(), data = new Uint8Array(parts.reduce((s, x) => s + x.length, 0));
      parts.reduce((o, x) => (data.set(x, o), o + x.length), 0);
      assert.ok(parts.every(x => x.length <= 255));
      const idx = lzwDecode(data, minCode, w * h), tr = gce ? gce.transparent : -1;
      // compose onto the canvas: apply the previous frame's disposal (1 = keep, 2 = clear its rect), then draw
      // the non-transparent pixels of this frame at its offset; rgb is the composed picture after this frame
      const last = frames[frames.length - 1];
      if (last && last.gce && last.gce.disposal === 2) {
        for (let y = 0; y < last.h; y++) canvas.fill(0, ((last.top + y) * width + last.left) * 3, ((last.top + y) * width + last.left + last.w) * 3);
      }
      idx.forEach((v, i) => { if (v !== tr) canvas.set(pal.subarray(v * 3, v * 3 + 3), ((top + (i / w | 0)) * width + left + i % w) * 3); });
      frames.push({ left, top, w, h, idx, gce, rgb: canvas.slice() });
      gce = null;
    } else throw new Error(`unknown block 0x${t.toString(16)} at ${p - 1}`);
  }
  assert.equal(p, b.length, 'trailer is the last byte');
  return { width, height, gct, loop, frames };
}

// --- helpers ----------------------------------------------------------------------------------------------------
const flatFrame = (w, h, fn) => {
  const a = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { a.set(fn(x, y), (y * w + x) * 4); a[(y * w + x) * 4 + 3] = 255; }
  return a;
};
const rgbOf = rgba => Uint8Array.from({ length: rgba.length / 4 * 3 }, (_, i) => rgba[(i / 3 | 0) * 4 + i % 3]);
const sameRGB = (a, b, msg) => {                                     // short failure message instead of a huge diff
  assert.equal(a.length, b.length, msg);
  const i = a.findIndex((v, k) => v !== b[k]);
  assert.ok(i < 0, `${msg}: first difference at pixel ${(i / 3) | 0}: ${a.subarray(i - i % 3, i - i % 3 + 3)} vs ${b.subarray(i - i % 3, i - i % 3 + 3)}`);
};
let seed = 12345;
const rnd = () => (seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) / 2 ** 32;

// --- tests ------------------------------------------------------------------------------------------------------
const COLS = [[0, 0, 0], [255, 40, 20], [30, 200, 255], [250, 250, 120], [12, 6, 30]];
const W = 20, H = 12;
const frames3 = [0, 1, 2].map(f => flatFrame(W, H, (x, y) => COLS[((x >> 2) + (y >> 2) + f) % COLS.length]));

ok('round trip: 3 flat-colour frames decode to the same colours', () => {
  const gif = encodeGIF(frames3, W, H, { dither: false, delayCs: 7 });
  const d = decodeGIF(gif);
  assert.equal(d.width, W); assert.equal(d.height, H); assert.equal(d.frames.length, 3);
  d.frames.forEach((fr, i) => {
    sameRGB(fr.rgb, rgbOf(frames3[i]), `frame ${i}`);
    assert.equal(fr.gce.disposal, 1); assert.equal(fr.gce.delay, 7);
  });
});

ok('optimised animation: moving square over a static background composes back exactly, much smaller', () => {
  const w = 96, h = 64, N = 12;
  const bg = (x, y) => [(x * 5) & 255, (y * 3) & 255, ((x ^ y) * 7) & 255];   // static, many colours
  const frames = Array.from({ length: N }, (_, f) => flatFrame(w, h, (x, y) => {
    const sx = 4 + f * 6, sy = 10 + f * 3;
    return x >= sx && x < sx + 10 && y >= sy && y < sy + 10 ? [255, 255, 255] : bg(x, y);
  }));
  frames.push(frames[N - 1]);                                         // an all-unchanged frame
  const q = quantize(frames, 63);                                     // > 63 colours: a lossy (median-cut) palette
  const enc = optimize => frames.reduce((g, f) => g.addFrame(f, { dither: false }),
    new GifWriter(w, h, { palette: q, delayCs: 4, optimize })).finish();
  const opt = enc(true), plain = enc(false), d = decodeGIF(opt), dp = decodeGIF(plain);
  assert.equal(d.frames.length, N + 1);
  d.frames.forEach((fr, i) => sameRGB(fr.rgb, dp.frames[i].rgb, `frame ${i} equals the unoptimised one`));
  const f1 = d.frames[1];
  assert.ok(f1.w < w && f1.h < h && f1.gce.transparent >= 0 && f1.gce.disposal === 1, 'cropped, transparent');
  assert.ok(f1.idx.includes(f1.gce.transparent), 'unchanged pixels inside the crop are transparent');
  const fl = d.frames[N];
  assert.deepEqual([fl.w, fl.h, fl.idx[0], fl.gce.delay], [1, 1, fl.gce.transparent, 4], 'unchanged frame: 1x1 transparent');
  assert.ok(opt.length * 4 < plain.length, `optimised ${opt.length} B vs ${plain.length} B`);
  // exact round trip with few colours (exact palette path)
  const few = Array.from({ length: 6 }, (_, f) => flatFrame(w, h, (x, y) => {
    const sx = f * 9;
    return x >= sx && x < sx + 8 && y >= 20 && y < 28 ? COLS[1 + f % 3] : COLS[(x >> 4) % 2 ? 4 : 0];
  }));
  decodeGIF(encodeGIF(few, w, h, { dither: false })).frames.forEach((fr, i) => sameRGB(fr.rgb, rgbOf(few[i]), `few ${i}`));
});

ok('header, logical screen, NETSCAPE loop extension and trailer bytes', () => {
  const gif = encodeGIF(frames3, W, H, { dither: false });
  assert.deepEqual([...gif.subarray(0, 13)], [71, 73, 70, 56, 57, 97, W, 0, H, 0, 0xf2, 0, 0]);   // 5 colours -> 8
  const ext = 13 + 8 * 3;
  assert.deepEqual([...gif.subarray(ext, ext + 19)],
    [0x21, 0xff, 0x0b, ...Buffer.from('NETSCAPE2.0'), 3, 1, 0, 0, 0]);
  assert.equal(gif[gif.length - 1], 0x3b);
  assert.equal(decodeGIF(gif).loop, 0);
  const g3 = new GifWriter(2, 2, { palette: new Uint8Array(6), loop: 3 }).addFrame(new Uint8Array(16)).finish();
  assert.equal(decodeGIF(g3).loop, 3);
  const once = new GifWriter(2, 2, { palette: new Uint8Array(6), loop: -1 }).addFrame(new Uint8Array(16)).finish();
  assert.equal(decodeGIF(once).loop, null);
});

ok('2x2 single-colour GIF is byte-exact', () => {
  // Palette: one colour (255,0,0), padded to 2 entries (GCT size field 0 -> 2^(0+1)). Frame: 4 pixels of index 0.
  // LZW, min code size 2: clear = 4, eoi = 5, first free code 6, code width 3 bits.
  //   emit clear(4); prefix=0. pixel 2: (0,0) unknown -> emit 0, add 6=(0,0); prefix=0.
  //   pixel 3: (0,0) known -> prefix=6. pixel 4: (6,0) unknown -> emit 6, add 7; prefix=0. end: emit 0, eoi(5).
  //   No width bump: next code 8 is never assigned (>= 1<<3 only after adding 7).
  // Codes 4,0,6,0,5 at 3 bits each, LSB first: 4 | 0<<3 | 6<<6 | 0<<9 | 5<<12 = 0x5184 -> bytes 0x84 0x51
  // (15 bits, padded to 16), one sub-block of length 2, then the 0 terminator.
  const gif = new GifWriter(2, 2, { palette: new Uint8Array([255, 0, 0]), delayCs: 10 })
    .addFrame(new Uint8Array([255, 0, 0, 255, 255, 0, 0, 255, 255, 0, 0, 255, 255, 0, 0, 255]), { dither: false }).finish();
  const expected = [
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61,                 // 'GIF89a'
    2, 0, 2, 0, 0xf0, 0, 0,                             // 2x2, GCT flag | 8-bit colour res | size 0; bg 0; aspect 0
    255, 0, 0, 0, 0, 0,                                 // global colour table (red, padding black)
    0x21, 0xff, 0x0b, 0x4e, 0x45, 0x54, 0x53, 0x43, 0x41, 0x50, 0x45, 0x32, 0x2e, 0x30,  // app ext 'NETSCAPE2.0'
    3, 1, 0, 0, 0,                                      // sub-block: loop count 0 (forever), terminator
    0x21, 0xf9, 4, 0x04, 10, 0, 0, 0,                   // GCE: disposal 1 (<<2), delay 10 cs, no transparency
    0x2c, 0, 0, 0, 0, 2, 0, 2, 0, 0,                    // image descriptor at (0,0), 2x2, no local table
    2, 2, 0x84, 0x51, 0,                                // min code size 2, sub-block [0x84 0x51], terminator
    0x3b,                                               // trailer
  ];
  assert.deepEqual([...gif], expected);
});

ok('LZW with > 4096 codes (128x128 noise, clear codes and 12-bit width) round-trips', () => {
  const pal = new Uint8Array(256 * 3);
  for (let i = 0; i < 256; i++) pal.set([i, (i * 7) & 255, (i * 13) & 255], i * 3);
  const idx = Uint8Array.from({ length: 128 * 128 }, () => rnd() * 256 | 0);
  const rgba = new Uint8Array(128 * 128 * 4);
  idx.forEach((v, i) => rgba.set([pal[v * 3], pal[v * 3 + 1], pal[v * 3 + 2], 255], i * 4));
  const q = quantize([rgba]);
  assert.equal(q.colors, 256);
  const gif = new GifWriter(128, 128, { palette: q }).addFrame(rgba, { dither: false }).finish();
  const d = decodeGIF(gif);
  assert.deepEqual(d.frames[0].rgb, rgbOf(rgba));
  // also a long low-entropy run (few colours, long strings) to cross 4096 entries with long prefixes
  const runs = Uint8Array.from({ length: 128 * 128 }, (_, i) => ((i * 31) ^ (i >> 5)) & 3);
  const rgba2 = new Uint8Array(runs.length * 4);
  runs.forEach((v, i) => rgba2.set([COLS[v][0], COLS[v][1], COLS[v][2], 255], i * 4));
  const d2 = decodeGIF(encodeGIF([rgba2], 128, 128, { dither: false }));
  assert.deepEqual(d2.frames[0].rgb, rgbOf(rgba2));
});

ok('quantize keeps pure black and a bright colour distinct in a dark many-colour scene', () => {
  const w = 160, h = 90;
  const f = flatFrame(w, h, (x, y) => {
    if (x > 150 && y < 3) return [255, 60, 200];                       // tiny bright magenta highlight
    if (x < 40) return [0, 0, 0];
    return [rnd() * 40 | 0, rnd() * 30 | 0, rnd() * 50 | 0];            // dark noisy glow, > 256 colours
  });
  const q = quantize([f], 64);
  assert.ok(q.colors <= 64 && q.size === 64);
  const black = q.lookup(0, 0, 0), mag = q.lookup(255, 60, 200);
  assert.notEqual(black, mag);
  assert.deepEqual([...q.palette.subarray(black * 3, black * 3 + 3)], [0, 0, 0]);
  const m = q.palette.subarray(mag * 3, mag * 3 + 3);
  assert.ok(Math.abs(m[0] - 255) < 16 && Math.abs(m[1] - 60) < 16 && Math.abs(m[2] - 200) < 16, `magenta -> ${m}`);
  const gif = encodeGIF([f], w, h, { maxColors: 64 });                // dithered path decodes too
  assert.equal(decodeGIF(gif).frames.length, 1);
});

ok('estimateGifBytes scales with pixels and frames', () => {
  assert.ok(estimateGifBytes(480, 270, 100) > estimateGifBytes(480, 270, 50));
  assert.ok(Math.abs(estimateGifBytes(480, 270, 100) / 1e6 - 4.5) < 0.2);
});

console.log(`${n} tests passed`);
