// Aurora sky effect (registerSkyFx 'aurora'): two or three curtains of vertical rays - bright green lower edge with
// a thin pink fringe, fading to violet-red tops - that ripple along their length and drift. Painted every frame at
// a quarter of the CSS size from a cached ray sprite (one drawImage per ray column, additive), scaled up (which
// softens it), cut to the open sky, and mirrored onto water. A faint green glow lifts the sky under the curtains.
// Reduced motion: slower, calmer movement. Dusk: much fainter.
// Porting note: the rays are a 1-px-wide vertical gradient stretched per column; in numpy this is an outer product
// of a column brightness vector and the ray profile, added into a small buffer.
import { registerSkyFx } from './fw_fx.js';
import { noise1, prng } from './fw_noise.js';
import { horizonCss, isDuskEnv, masked, waterCss } from './fw_fx_masks.js';

let ray = null;
function raySprite() {
  if (ray) return ray;
  ray = document.createElement('canvas'); ray.width = 2; ray.height = 128;
  const g = ray.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 128);
  gr.addColorStop(0, 'rgba(150,50,170,0)'); gr.addColorStop(0.3, 'rgba(160,60,160,0.12)');
  gr.addColorStop(0.6, 'rgba(60,190,130,0.25)'); gr.addColorStop(0.88, 'rgba(80,250,140,0.7)');
  gr.addColorStop(0.96, 'rgba(170,255,190,0.85)'); gr.addColorStop(0.985, 'rgba(240,110,190,0.35)'); gr.addColorStop(1, 'rgba(255,110,190,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 2, 128);
  return ray;
}

export function aurora(env) {
  const rnd = prng((env.seed ^ 0xa0a0b0b) >>> 0), n = 2 + (rnd() < 0.5 ? 1 : 0);
  const curtains = [];
  for (let i = 0; i < n; i++) curtains.push({
    base: 0.38 + rnd() * 0.32, amp: 0.05 + rnd() * 0.08, freq: 0.6 + rnd() * 1.2, speed: 0.05 + rnd() * 0.08,
    ph: rnd() * 6.28, h: 0.28 + rnd() * 0.3, I: 0.55 + rnd() * 0.45, u0: rnd() * 0.3 - 0.1, u1: 0.7 + rnd() * 0.4, seed: (rnd() * 1e6) | 0,
  });
  const st = { t: 0 };
  let buf = null;
  // Column brightness and geometry of curtain `C` at u in [0, 1] (fractions of the sky height): pure numbers.
  const column = (C, u, t = st.t) => {
      const win = Math.max(0, Math.min(1, (u - C.u0) * 6, (C.u1 - u) * 6));
      const y = C.base + C.amp * Math.sin(u * C.freq * 6.283 + t * C.speed * 6 + C.ph) + 0.06 * (noise1(C.seed, u * 3 + t * 0.04) - 0.5);
      const b = Math.pow(noise1(C.seed + 1, u * 110 - t * 0.6), 2) * 0.45 + 0.25 * noise1(C.seed + 4, u * 30 + t * 0.3) + 0.3 * noise1(C.seed + 3, u * 7 + t * 0.15);
      const pulse = 0.75 + 0.25 * Math.sin(t * 0.7 + C.ph + u * 3);
      return { y, h: C.h * (0.6 + 0.7 * noise1(C.seed + 2, u * 5 + t * 0.08)), b: b * win * pulse * C.I };
  };
  return {
    curtains, column,
    update(dt, env) { st.t += dt * (env.reduced ? 0.3 : 1); },
    drawSky(c, env) {
      const W = env.cssW, hz = horizonCss(env), bw = Math.max(16, Math.ceil(W / 4)), bh = Math.max(8, Math.ceil(hz / 4));
      if (!buf || buf.width !== bw || buf.height !== bh) { buf = document.createElement('canvas'); buf.width = bw; buf.height = bh; }
      const b = buf.getContext('2d'), sp = raySprite(), I = isDuskEnv(env) ? 0.35 : 1;
      b.globalCompositeOperation = 'source-over'; b.clearRect(0, 0, bw, bh);
      b.globalCompositeOperation = 'lighter';
      for (const C of curtains) for (let x = 0; x < bw; x++) {
        const col = column(C, x / bw);
        if (col.b < 0.02) continue;
        const h = col.h * bh, y = col.y * bh;
        b.globalAlpha = Math.min(1, col.b * I * 0.75); b.drawImage(sp, x, y - h, 1.6, h);
      }
      b.globalAlpha = 1;
      masked(c, env, 'sky', l => {
        const gl = l.createLinearGradient(0, hz * 0.3, 0, hz);  // diffuse glow under the curtains (sky only)
        gl.addColorStop(0, 'rgba(40,160,100,0)'); gl.addColorStop(1, `rgba(40,160,100,${0.07 * I})`);
        l.fillStyle = gl; l.fillRect(0, 0, W, hz);
        l.imageSmoothingEnabled = true; l.drawImage(buf, 0, 0, W, hz);
      });
      const wl = waterCss(env);
      if (wl !== null) masked(c, env, 'water', l => {
        l.translate(0, wl); l.scale(1, -0.85); l.translate(0, -wl); l.drawImage(buf, 0, wl - hz, W, hz);
      }, 0.5);
    },
    state: () => ({ t: st.t, curtains: curtains.map(C => ({ ...C })) }),
  };
}

registerSkyFx('aurora', 'Aurora', aurora);
