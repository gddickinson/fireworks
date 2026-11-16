// Canvas 2D fallback of the realistic renderer (no WebGL2): the same layers as fw_render_gl.js, approximated with
// 'lighter' compositing: fading firework trails, a downscaled glow for bloom, burst light masked by the scenery's
// albedo, lit smoke, a mirrored reflection on water, the front silhouettes, weather and a vignette.
import { STRIDE } from './fw_atmos.js';

const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, w); c.height = Math.max(1, h); return c; };
const lin = v => Math.min(255, Math.round(v * 150));
const tone = v => Math.min(255, Math.round(255 * Math.pow(v / (1 + v), 1 / 2.2) * 1.15));

export class Canvas2DRenderer {
  constructor(cv) { this.canvas = cv; this.ctx = cv.getContext('2d'); this.kind = 'canvas2d'; this.W = 0; this.H = 0; }
  resize(W, H) {
    if (W === this.W && H === this.H) return;
    this.W = W; this.H = H;
    this.fw = canvas(W, H); this.glow = canvas(W >> 3, H >> 3); this.light = canvas(W >> 2, H >> 2);
    this.vig = canvas(W, H);
    const v = this.vig.getContext('2d'), g = v.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.hypot(W, H) / 2);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.45)');
    v.fillStyle = g; v.fillRect(0, 0, W, H);
  }
  setScenery(S) {
    this.S = S;
    const w = this.light.width, h = this.light.height, m = canvas(w, h), c = m.getContext('2d');
    c.drawImage(S.mat, 0, 0, w, h);
    const d = c.getImageData(0, 0, w, h), p = d.data;
    for (let i = 0; i < p.length; i += 4) { const a = Math.min(255, p[i] * 0.6 + p[i + 2] * 0.12); p[i] = p[i + 1] = p[i + 2] = 255; p[i + 3] = a; }
    c.putImageData(d, 0, 0);
    this.albedo = m;
  }
  clearTrails() { this.fw.getContext('2d').clearRect(0, 0, this.W, this.H); }
  render(F) {
    const c = this.ctx, W = this.W, H = this.H, S = this.S;
    c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1;
    c.drawImage(S.back, 0, 0, W, H);
    // burst light on the scenery and sky
    const lc = this.light.getContext('2d'), lw = this.light.width, lh = this.light.height, k = lw / W;
    lc.globalCompositeOperation = 'source-over'; lc.clearRect(0, 0, lw, lh);
    if (F.lights.length) {
      lc.globalCompositeOperation = 'lighter';
      for (const L of F.lights) {
        const r = L.r * k * 3, x = L.x * k, y = L.y * k, a = Math.min(1, L.I * 0.35);
        const g = lc.createRadialGradient(x, y, 0, x, y, r);
        g.addColorStop(0, `rgba(${L.col[0]},${L.col[1]},${L.col[2]},${a})`); g.addColorStop(1, 'rgba(0,0,0,0)');
        lc.fillStyle = g; lc.fillRect(x - r, y - r, 2 * r, 2 * r);
      }
      lc.globalCompositeOperation = 'destination-in'; lc.drawImage(this.albedo, 0, 0);
      c.globalCompositeOperation = 'lighter'; c.drawImage(this.light, 0, 0, W, H);
    }
    // smoke
    c.globalCompositeOperation = 'source-over';
    for (const p of F.puffs) {
      const [r, g, b] = p.rgb.map(v => tone(v * 3)), gr = c.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r);
      gr.addColorStop(0, `rgba(${r},${g},${b},${p.a})`); gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
      c.fillStyle = gr; c.fillRect(p.x - p.r, p.y - p.r, 2 * p.r, 2 * p.r);
    }
    // firework trails buffer
    const f = this.fw.getContext('2d');
    f.globalCompositeOperation = 'destination-out'; f.fillStyle = `rgba(0,0,0,${1 - F.persist})`; f.fillRect(0, 0, W, H);
    f.globalCompositeOperation = 'lighter';
    const P = F.parts;
    for (let i = 0; i < F.n; i++) {
      const o = i * STRIDE, s = P[o + 2] * 1.6;
      f.fillStyle = `rgb(${lin(P[o + 3])},${lin(P[o + 4])},${lin(P[o + 5])})`;
      f.fillRect(P[o] - s / 2, P[o + 1] - s / 2, s, s);
    }
    c.globalCompositeOperation = 'lighter';
    c.drawImage(this.fw, 0, 0);
    const g = this.glow.getContext('2d');
    g.clearRect(0, 0, this.glow.width, this.glow.height); g.drawImage(this.fw, 0, 0, this.glow.width, this.glow.height);
    c.globalAlpha = 0.9; c.drawImage(this.glow, 0, 0, W, H); c.globalAlpha = 1;
    if (S.water) {                                            // mirrored, dimmed fireworks on the water
      c.save(); c.beginPath(); c.rect(0, S.water, W, H - S.water); c.clip();
      c.globalAlpha = 0.4; c.translate(0, S.water); c.scale(1, -0.85); c.translate(0, -S.water);
      c.drawImage(this.fw, 0, 0); c.drawImage(this.glow, 0, 0, W, H); c.restore();
    }
    c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1;
    c.drawImage(S.front, 0, 0, W, H);
    if (F.weather) c.drawImage(F.weather, 0, 0, W, H);
    c.drawImage(this.vig, 0, 0);
  }
}
