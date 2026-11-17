// Plug-in layers of the realistic display: weather (rain, snow, fog, clouds, storm), sky effects (moon, aurora,
// shooting stars, lanterns...) and animated scene objects. Each plug-in draws into one of two CSS-pixel canvases
// that the renderers composite every frame:
//   sky  - over the scenery's back layer, behind the fireworks (premultiplied "over": moon, aurora, lanterns, boats)
//   over - over everything (alpha "over": rain, snow, fog, cloud deck; fog dims the sparks behind it)
// Plug-in interface (all optional): resize(env) · update(dt, env) · drawSky(ctx, env) · drawOver(ctx, env)
// env: { sim, cam, cssW, cssH, k (CSS px per device px), lights (Atmos.screenLights, device px), time, wind (m/s),
//        scenery, seed, reduced, quality }. Plug-ins must be deterministic given env.seed and the frame sequence.
export const WEATHER = {};    // name -> { label, make(env) }
export const SKY_FX = {};     // key -> { label, make(env) }
export const SCENE_FX = {};   // scenery name -> make(env)   (animated objects of a scene, always on)

export const registerWeather = (name, label, make) => { WEATHER[name] = { label, make }; };
export const registerSkyFx = (key, label, make) => { SKY_FX[key] = { label, make }; };
export const registerSceneFx = (scene, make) => { SCENE_FX[scene] = make; };

const canvas = () => document.createElement('canvas');

export class FxLayers {
  constructor() { this.sky = canvas(); this.over = canvas(); this.plugins = []; this.w = 0; this.h = 0; }
  set(plugins, env) { this.plugins = plugins.filter(Boolean); this.resize(env, true); }
  resize(env, force = false) {
    if (force || env.cssW !== this.w || env.cssH !== this.h) {
      this.w = this.sky.width = this.over.width = Math.max(1, env.cssW);
      this.h = this.sky.height = this.over.height = Math.max(1, env.cssH);
      for (const p of this.plugins) p.resize?.(env);
    }
  }
  update(dt, env) { for (const p of this.plugins) p.update?.(dt, env); }
  // Draws the layers; returns { sky, over } (null where no plug-in drew).
  render(env) {
    let sky = null, over = null;
    const s = this.sky.getContext('2d'), o = this.over.getContext('2d');
    s.clearRect(0, 0, this.w, this.h); o.clearRect(0, 0, this.w, this.h);
    for (const p of this.plugins) {
      if (p.drawSky) { s.save(); p.drawSky(s, env); s.restore(); sky = this.sky; }
      if (p.drawOver) { o.save(); p.drawOver(o, env); o.restore(); over = this.over; }
    }
    return { sky, over };
  }
}

// Gusty wind (m/s, +x) around `base`: smooth, deterministic in time (two incommensurate swells and a gust term).
export function gustyWind(base, t, seed = 0) {
  const ph = (seed % 1000) * 0.01;
  const swell = 0.25 * Math.sin(t * 0.21 + ph) + 0.15 * Math.sin(t * 0.53 + 2 * ph);
  const gust = Math.max(0, Math.sin(t * 0.11 + ph * 3)) ** 6 * 0.8;
  return base * (1 + swell + gust);
}
