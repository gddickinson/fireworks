// Helpers for the sky-effect and scene plug-ins (fw_sky_fx.js, fw_sky_aurora.js, fw_scene_fx.js): masks of the open
// sky and of the water taken from the scenery's material map (blue = sky, green = water), at CSS size and cached per
// scenery and size, so a moon or an aurora disappears behind hills and buildings and is reflected only on water;
// a scratch layer to draw through a mask; soft round sprites; and small numeric helpers. Nothing here runs in
// update(), so the plug-ins' state stays testable without a canvas.
const cache = new WeakMap();
const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, w); c.height = Math.max(1, h); return c; };

export function masks(env) {
  const S = env.scenery, w = env.cssW, h = env.cssH, key = `${w}x${h}`;
  let e = cache.get(S);
  if (e && e.key === key) return e;
  const src = canvas(w, h), sc = src.getContext('2d', { willReadFrequently: true });
  sc.drawImage(S.mat, 0, 0, w, h);
  const d = sc.getImageData(0, 0, w, h).data, sky = canvas(w, h), water = canvas(w, h);
  const si = sky.getContext('2d').createImageData(w, h), wi = water.getContext('2d').createImageData(w, h);
  for (let i = 0; i < d.length; i += 4) {
    si.data[i] = si.data[i + 1] = si.data[i + 2] = 255; si.data[i + 3] = d[i + 2];
    wi.data[i] = wi.data[i + 1] = wi.data[i + 2] = 255; wi.data[i + 3] = d[i + 1];
  }
  sky.getContext('2d').putImageData(si, 0, 0); water.getContext('2d').putImageData(wi, 0, 0);
  e = { key, sky, water, scratch: canvas(w, h) };
  cache.set(S, e);
  return e;
}

// Draw through a mask: fn(ctx) paints into a scratch layer, which is cut to the sky (or water) and composited onto
// `ctx` with `alpha`. The scratch layer is shared by the plug-ins (each use clears it first).
export function masked(ctx, env, which, fn, alpha = 1) {
  const M = masks(env), L = M.scratch, l = L.getContext('2d');
  l.setTransform(1, 0, 0, 1, 0, 0); l.globalCompositeOperation = 'source-over'; l.globalAlpha = 1; l.clearRect(0, 0, L.width, L.height);
  l.save(); fn(l); l.restore();
  l.globalCompositeOperation = 'destination-in'; l.globalAlpha = 1; l.drawImage(M[which], 0, 0);
  ctx.globalAlpha = alpha; ctx.drawImage(L, 0, 0); ctx.globalAlpha = 1;
}

// Soft radial sprite (cached per colour): draw with drawImage(sprite, x - r, y - r, 2r, 2r).
const sprites = new Map();
export function softSprite(col, core = 0.15) {
  const key = col.join() + core;
  if (!sprites.has(key)) {
    const c = canvas(128, 128), g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, `rgba(${col},1)`); gr.addColorStop(core, `rgba(${col},0.5)`); gr.addColorStop(1, `rgba(${col},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128); sprites.set(key, c);
  }
  return sprites.get(key);
}

// Device px of the scenery -> CSS px of the plug-in canvases.
export const cssK = env => env.cssW / Math.max(1, env.scenery?.W || env.cssW);
// Waterline in CSS px (or null) and the launch horizon in CSS px.
export const waterCss = env => env.scenery?.water ? env.scenery.water * cssK(env) : null;
export const horizonCss = env => (env.scenery?.horizon ?? 0.9) * env.cssH;
export const isDuskEnv = env => env.scenery?.time === 'dusk';

// Exponential waiting time (seeded uniform u in [0, 1)).
export const expWait = (u, mean) => -Math.log(1 - u) * mean;

// Run several plug-ins as one (a scene with several animated objects).
export function combine(...parts) {
  parts = parts.filter(Boolean);
  return {
    parts,
    resize: env => parts.forEach(p => p.resize?.(env)),
    update: (dt, env) => parts.forEach(p => p.update?.(dt, env)),
    drawSky: (c, env) => parts.forEach(p => { if (p.drawSky) { c.save(); p.drawSky(c, env); c.restore(); } }),
    state: () => parts.map(p => p.state?.()),
  };
}
