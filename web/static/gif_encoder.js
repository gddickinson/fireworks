// Self-contained animated-GIF (GIF89a) encoder: palette quantisation, ordered dithering, LZW. Pure JS, no DOM, so it
// runs on the main thread, in a Worker (gif_worker.js) and in node (gif_encoder.test.mjs).
//   quantize(frames)          one global palette for all frames. If the sampled pixels hold <= maxColors distinct
//                             colours they are used exactly; otherwise median cut over a 15-bit histogram, run separately
//                             on dark and bright pixels so firework frames (mostly near-black, with small saturated
//                             highlights) keep both their dark shades and their bright colours; pure black is reserved.
//   GifWriter                 header, global colour table, NETSCAPE2.0 loop, per frame GCE + image + LZW data, trailer;
//                             later frames cropped to what changed, unchanged pixels transparent (optimize, default).
//   encodeGIF(frames, w, h)   both in one call.          estimateGifBytes(w, h, n)   rough size for a warning.

const DARK_LUMA = 48;        // luma (0..255) below which a histogram bin counts as dark for the palette split
const SAMPLE_TARGET = 250000; // pixels sampled across all frames for the palette

const luma = (r, g, b) => (r * 77 + g * 150 + b * 29) >> 8;
const dist = (r, g, b, p, i) => {
  const dr = r - p[i], dg = g - p[i + 1], db = b - p[i + 2];
  return 2 * dr * dr + 4 * dg * dg + 3 * db * db;
};

// Nearest-colour lookup over a palette (Uint8Array r,g,b triples, n entries), cached per 15-bit cell (centre of the
// cell decides). exact: optional Map 0xRRGGBB -> index tried first, so exact palettes round-trip losslessly.
export function makeLookup(palette, n = palette.length / 3, exact = null) {
  const cache = new Int16Array(32768).fill(-1);
  const nearest = (r, g, b) => {
    let best = 0, bd = Infinity;
    for (let i = 0, j = 0; i < n; i++, j += 3) {
      const d = dist(r, g, b, palette, j);
      if (d < bd) { bd = d; best = i; if (d === 0) break; }
    }
    return best;
  };
  return (r, g, b) => {
    if (exact) { const e = exact.get((r << 16) | (g << 8) | b); if (e !== undefined) return e; }
    const k = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
    let v = cache[k];
    if (v < 0) v = cache[k] = nearest((r & 0xf8) | 4, (g & 0xf8) | 4, (b & 0xf8) | 4);
    return v;
  };
}

const pow2Size = n => { let s = 2; while (s < n) s <<= 1; return s; };

// Median cut over histogram bins (ids into cnt/sr/sg/sb). Returns up to budget [r,g,b] colours (bin-weighted means).
// Phase 1 (first half of the splits) splits the most populated box, phase 2 the box with the largest colour range,
// so rare bright colours still get their own entries.
function medianCut(bins, budget, cnt, sr, sg, sb) {
  if (!bins.length || budget <= 0) return [];
  const comp = (id, a) => a === 0 ? id >> 10 : a === 1 ? (id >> 5) & 31 : id & 31;
  const mkBox = (lo, hi) => {
    const mn = [31, 31, 31], mx = [0, 0, 0];
    let c = 0;
    for (let i = lo; i < hi; i++) {
      const id = bins[i];
      c += cnt[id];
      for (let a = 0; a < 3; a++) { const v = comp(id, a); if (v < mn[a]) mn[a] = v; if (v > mx[a]) mx[a] = v; }
    }
    const rg = [mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]];
    const axis = rg[1] >= rg[0] && rg[1] >= rg[2] ? 1 : rg[0] >= rg[2] ? 0 : 2;
    return { lo, hi, count: c, range: rg[axis], axis };
  };
  const boxes = [mkBox(0, bins.length)];
  const phase1 = Math.max(1, budget >> 1);
  while (boxes.length < budget) {
    let bi = -1, bs = -1;
    for (let i = 0; i < boxes.length; i++) {
      const b = boxes[i];
      if (b.hi - b.lo < 2 || b.range === 0) continue;
      const s = boxes.length < phase1 ? b.count : b.range * 1e9 + b.count;
      if (s > bs) { bs = s; bi = i; }
    }
    if (bi < 0) break;
    const b = boxes[bi], a = b.axis;
    const part = bins.subarray(b.lo, b.hi).sort((x, y) => comp(x, a) - comp(y, a));
    let acc = 0, cut = 1;
    for (let i = 0; i < part.length - 1; i++) { acc += cnt[part[i]]; cut = i + 1; if (acc * 2 >= b.count) break; }
    // never split inside a run of equal coordinates (keeps boxes disjoint along the axis)
    while (cut < part.length && comp(part[cut], a) === comp(part[cut - 1], a)) cut++;
    if (cut >= part.length) { cut = 1; while (cut < part.length && comp(part[cut], a) === comp(part[0], a)) cut++; }
    boxes.splice(bi, 1, mkBox(b.lo, b.lo + cut), mkBox(b.lo + cut, b.hi));
  }
  return boxes.map(b => {
    let c = 0, r = 0, g = 0, bl = 0;
    for (let i = b.lo; i < b.hi; i++) { const id = bins[i]; c += cnt[id]; r += sr[id]; g += sg[id]; bl += sb[id]; }
    return [Math.round(r / c), Math.round(g / c), Math.round(bl / c)];
  });
}

// Global palette for a list of RGBA frames (Uint8ClampedArray / Uint8Array, alpha ignored).
// Returns { palette: Uint8Array(3 * size), size (power of two >= 2), colors (used entries), lookup(r, g, b) -> index }.
export function quantize(rgbaList, maxColors = 256) {
  maxColors = Math.max(2, Math.min(256, maxColors | 0));
  const total = rgbaList.reduce((s, f) => s + (f.length >> 2), 0);
  const step = Math.max(1, Math.floor(total / SAMPLE_TARGET));
  const cnt = new Uint32Array(32768), sr = new Float64Array(32768), sg = new Float64Array(32768), sb = new Float64Array(32768);
  let exact = new Map();
  rgbaList.forEach((f, fi) => {
    for (let p = ((fi * 7919) % step) * 4; p < f.length; p += step * 4) {
      const r = f[p], g = f[p + 1], b = f[p + 2], k = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
      cnt[k]++; sr[k] += r; sg[k] += g; sb[k] += b;
      if (exact) {
        const c = (r << 16) | (g << 8) | b;
        if (!exact.has(c)) { if (exact.size >= maxColors) exact = null; else exact.set(c, exact.size); }
      }
    }
  });
  let cols;
  if (exact) {
    cols = [...exact.keys()].map(c => [c >> 16, (c >> 8) & 255, c & 255]);
    if (!cols.length) cols = [[0, 0, 0]];
  } else {
    const dark = [], bright = [];
    for (let k = 0; k < 32768; k++) {
      if (!cnt[k]) continue;
      (luma(sr[k] / cnt[k], sg[k] / cnt[k], sb[k] / cnt[k]) < DARK_LUMA ? dark : bright).push(k);
    }
    const avail = maxColors - 1;                               // entry 0 is pure black
    let nd = bright.length ? Math.min(dark.length, Math.max(4, Math.round(avail / 4))) : Math.min(dark.length, avail);
    const nb = Math.min(bright.length, avail - nd);
    nd = Math.min(dark.length, avail - nb);                     // give leftovers back to the dark side
    cols = [[0, 0, 0], ...medianCut(Int32Array.from(dark), nd, cnt, sr, sg, sb),
      ...medianCut(Int32Array.from(bright), nb, cnt, sr, sg, sb)];
  }
  const size = pow2Size(cols.length), palette = new Uint8Array(size * 3);
  cols.forEach((c, i) => palette.set(c, i * 3));
  return { palette, size, colors: cols.length, lookup: makeLookup(palette, cols.length, exact) };
}

// Growable byte buffer.
class Bytes {
  constructor(cap = 1 << 16) { this.buf = new Uint8Array(cap); this.n = 0; }
  ensure(k) {
    if (this.n + k <= this.buf.length) return;
    let c = this.buf.length * 2;
    while (c < this.n + k) c *= 2;
    const b = new Uint8Array(c); b.set(this.buf.subarray(0, this.n)); this.buf = b;
  }
  byte(v) { this.ensure(1); this.buf[this.n++] = v; }
  u16(v) { this.ensure(2); this.buf[this.n++] = v & 255; this.buf[this.n++] = (v >> 8) & 255; }
  bytes(a) { this.ensure(a.length); this.buf.set(a, this.n); this.n += a.length; }
  str(s) { for (let i = 0; i < s.length; i++) this.byte(s.charCodeAt(i)); }
}

// GIF LZW: codes LSB-first, width minCode+1 growing to 12 bits, clear code when the 4096-entry table is full.
// Dictionary: open addressing on (prefix << 8 | byte), 16384 slots, invalidated in O(1) by a generation stamp.
const HSIZE = 16384;
const hKey = new Int32Array(HSIZE), hVal = new Int16Array(HSIZE), hGen = new Int32Array(HSIZE);
let gen = 0;
export function lzwEncode(indices, minCode, out) {
  const clear = 1 << minCode, eoi = clear + 1;
  let size = minCode + 1, next = eoi + 1, acc = 0, nbits = 0;
  let blk = new Uint8Array(Math.max(256, indices.length + (indices.length >> 1) + 16)), bn = 0;
  const emit = c => {
    acc |= c << nbits; nbits += size;
    while (nbits >= 8) {
      if (bn === blk.length) { const b = new Uint8Array(blk.length * 2); b.set(blk); blk = b; }
      blk[bn++] = acc & 255; acc >>>= 8; nbits -= 8;
    }
  };
  gen++;
  emit(clear);
  if (indices.length) {
    let prefix = indices[0];
    for (let i = 1, len = indices.length; i < len; i++) {
      const k = indices[i], key = (prefix << 8) | k;
      let h = Math.imul(key, 0x9e3779b1) >>> 18;
      while (hGen[h] === gen && hKey[h] !== key) h = (h + 1) & (HSIZE - 1);
      if (hGen[h] === gen) { prefix = hVal[h]; continue; }
      emit(prefix);
      if (next === 4096) { emit(clear); gen++; size = minCode + 1; next = eoi + 1; }
      else {
        if (next >= 1 << size) size++;
        hGen[h] = gen; hKey[h] = key; hVal[h] = next++;
      }
      prefix = k;
    }
    emit(prefix);
  }
  emit(eoi);
  if (nbits > 0) { if (bn === blk.length) { const b = new Uint8Array(bn + 1); b.set(blk); blk = b; } blk[bn++] = acc & 255; }
  out.byte(minCode);
  for (let p = 0; p < bn; p += 255) {
    const m = Math.min(255, bn - p);
    out.byte(m); out.bytes(blk.subarray(p, p + m));
  }
  out.byte(0);
}

// Bayer 4x4 offsets, mild: +-6 levels (of 255). Pixels whose brightest channel is < 12 are not dithered so black
// skies stay clean (and compress well).
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
const DITHER_AMP = 12;
const DITHER = Int8Array.from(BAYER, b => Math.round(((b + 0.5) / 16 - 0.5) * DITHER_AMP));
const clamp = v => v < 0 ? 0 : v > 255 ? 255 : v;

export class GifWriter {
  // palette: a quantize() result, or a Uint8Array of r,g,b triples (padded to a power of two here if needed).
  // loop: 0 = forever, n = n repeats, < 0 = no NETSCAPE extension (play once). delayCs: frame delay in 1/100 s.
  // optimize: frames after the first are cropped to the bounding box of pixels whose palette index changed, and
  // unchanged pixels inside it become a reserved transparent index (disposal 1 keeps the previous frame underneath)
// when that encodes smaller than the plain crop.
  // The transparent index is the first palette slot after the used colours (the table is doubled if it is full and
  // < 256 entries); with 256 used colours only the cropping applies, so quantize to maxColors - 1 when optimising.
  constructor(width, height, { loop = 0, palette, delayCs = 5, optimize = true } = {}) {
    if (!palette) throw new Error('GifWriter needs a palette (use quantize())');
    let pal = palette.palette || palette;
    const used = palette.colors ?? pal.length / 3;
    let size = pow2Size(pal.length / 3);
    if (optimize && used >= size && size < 256) size *= 2;
    if (size * 3 !== pal.length) { const p = new Uint8Array(size * 3); p.set(pal); pal = p; }
    Object.assign(this, { width, height, delayCs, optimize, lookup: palette.lookup || makeLookup(pal, used), out: new Bytes() });
    this.trans = optimize && used < size ? used : -1;
    this.minCode = Math.max(2, Math.log2(size));
    this.idx = new Uint8Array(width * height);
    this.prev = optimize ? new Uint8Array(width * height) : null;
    this.frames = 0;
    const o = this.out;
    o.str('GIF89a'); o.u16(width); o.u16(height);
    o.byte(0xf0 | (Math.log2(size) - 1)); o.byte(0); o.byte(0);   // GCT present, 8-bit colour resolution, bg 0
    o.bytes(pal);
    if (loop >= 0) { o.bytes([0x21, 0xff, 0x0b]); o.str('NETSCAPE2.0'); o.bytes([3, 1, loop & 255, (loop >> 8) & 255, 0]); }
  }

  // rgba: width*height*4 bytes. Maps to palette indices (optionally Bayer-dithered; the pattern is fixed per pixel
  // position, so static areas keep their indices frame to frame) and appends one frame.
  addFrame(rgba, { dither = true, delayCs = this.delayCs } = {}) {
    const { width: w, height: h, idx, lookup, out: o } = this;
    if (rgba.length < w * h * 4) throw new Error(`frame has ${rgba.length} bytes, expected ${w * h * 4}`);
    for (let y = 0, p = 0, q = 0; y < h; y++) {
      const row = (y & 3) << 2;
      for (let x = 0; x < w; x++, p += 4, q++) {
        let r = rgba[p], g = rgba[p + 1], b = rgba[p + 2];
        if (dither && (r >= 12 || g >= 12 || b >= 12)) {
          const d = DITHER[row | (x & 3)];
          r = clamp(r + d); g = clamp(g + d); b = clamp(b + d);
        }
        idx[q] = lookup(r, g, b);
      }
    }
    let x0 = 0, y0 = 0, x1 = w - 1, y1 = h - 1, data = idx, ti = -1;
    const lzw = new Bytes(1 << 12);
    if (this.optimize && this.frames > 0) {
      const prev = this.prev;
      x0 = w; y0 = h; x1 = -1; y1 = -1;
      for (let y = 0, q = 0; y < h; y++) {
        for (let x = 0; x < w; x++, q++) {
          if (idx[q] === prev[q]) continue;
          if (x < x0) x0 = x;
          if (x > x1) x1 = x;
          if (y0 === h) y0 = y;
          y1 = y;
        }
      }
      if (x1 < 0) {                                     // nothing changed: a 1x1 frame that keeps the picture
        x0 = y0 = x1 = y1 = 0;
        ti = this.trans;
        data = Uint8Array.of(ti >= 0 ? ti : prev[0]);
      } else {
        // the crop as it is, and (if an index is free) with unchanged pixels transparent; the smaller one is kept,
        // since where nearly everything changes (dense, flickering bursts) transparency only breaks up LZW runs
        const cw = x1 - x0 + 1, ch = y1 - y0 + 1, raw = new Uint8Array(cw * ch), tr = this.trans;
        const masked = tr >= 0 ? new Uint8Array(cw * ch) : null;
        for (let y = 0, k = 0; y < ch; y++) {
          for (let x = 0, q = (y0 + y) * w + x0; x < cw; x++, q++, k++) {
            raw[k] = idx[q];
            if (masked) masked[k] = idx[q] === prev[q] ? tr : idx[q];
          }
        }
        data = raw;
        if (masked) {
          lzwEncode(masked, this.minCode, lzw);
          const alt = new Bytes(lzw.n + 256);
          lzwEncode(raw, this.minCode, alt);
          data = null;
          if (alt.n >= lzw.n) ti = tr; else { lzw.buf = alt.buf; lzw.n = alt.n; }
        }
      }
    }
    if (data) lzwEncode(data, this.minCode, lzw);
    if (this.prev) this.prev.set(idx);
    this.frames++;
    // GCE: disposal 1 (do not dispose), transparency flag + index when the frame uses it
    o.bytes([0x21, 0xf9, 4, (1 << 2) | (ti >= 0 ? 1 : 0), delayCs & 255, (delayCs >> 8) & 255, ti >= 0 ? ti : 0, 0]);
    o.byte(0x2c); o.u16(x0); o.u16(y0); o.u16(x1 - x0 + 1); o.u16(y1 - y0 + 1); o.byte(0);   // no local table
    o.bytes(lzw.buf.subarray(0, lzw.n));
    return this;
  }

  finish() {
    this.out.byte(0x3b);
    return this.out.buf.slice(0, this.out.n);
  }
}

// Rough size: 0.22 bytes per pixel per frame plus fixed overhead (real exports of the realistic display, frame
// differencing on, measured 0.12-0.2). A synthetic 480x270
// burst over a dark gradient sky measured 0.12 B/px/frame dithered (0.06 undithered); textured backgrounds (stars,
// mountains, rain) cost more, and full-frame random noise reaches ~1 B/px.
export const estimateGifBytes = (width, height, frames) => Math.round(800 + frames * (20 + width * height * 0.22));

// frames: array of RGBA arrays. opts: { maxColors = 256, dither = true, delayCs = 5, loop = 0, optimize = true,
// onProgress(done, total) }. With optimize, one of the maxColors palette entries is the transparent index.
export function encodeGIF(frames, width, height,
  { maxColors = 256, dither = true, delayCs = 5, loop = 0, optimize = true, onProgress } = {}) {
  const q = quantize(frames, optimize ? maxColors - 1 : maxColors);
  const gw = new GifWriter(width, height, { loop, palette: q, delayCs, optimize });
  frames.forEach((f, i) => { gw.addFrame(f, { dither }); onProgress?.(i + 1, frames.length); });
  return gw.finish();
}
