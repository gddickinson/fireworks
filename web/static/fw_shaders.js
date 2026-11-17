// GLSL (WebGL2) programs of the realistic renderer (fw_render_gl.js). Screen-space convention: pixel coordinates
// with y down; textures uploaded from canvases are sampled at uv (y down), render targets at (u, 1 - v).
export const QUAD_VS = `#version 300 es
in vec2 p; out vec2 uv;
void main() { uv = vec2(p.x * 0.5 + 0.5, 0.5 - p.y * 0.5); gl_Position = vec4(p, 0.0, 1.0); }`;

// Stars as additive point sprites: a tight hot core and a soft halo (the bloom passes add the wide glow).
export const STAR_VS = `#version 300 es
uniform vec2 res; in vec2 pos; in float size; in vec3 col; in float core;
out vec3 vcol; out float vcore;
void main() {
  gl_Position = vec4(pos.x / res.x * 2.0 - 1.0, 1.0 - pos.y / res.y * 2.0, 0.0, 1.0);
  gl_PointSize = size * 5.0; vcol = col; vcore = core;
}`;
export const STAR_FS = `#version 300 es
precision mediump float; in vec3 vcol; in float vcore; out vec4 o;
void main() {
  vec2 d = gl_PointCoord - 0.5; float r2 = dot(d, d) * 25.0;   // r in core radii; the sprite's edge is r = 2.5
  float edge = max(0.0, 1.0 - r2 / 6.25); edge *= edge;          // reaches exactly 0 at the circle: never a square
  float a = (exp(-r2 * 1.6) * 2.2 * vcore + exp(-r2 * 0.25) * 0.14) * edge;
  o = vec4(vcol * a, 0.0);
}`;

// Smoke: instanced quads with a cloudy texture, premultiplied alpha.
export const SMOKE_VS = `#version 300 es
uniform vec2 res; in vec2 p; in vec4 inst; in vec4 icol;    // inst: x, y, radius, rotation; icol: rgb, alpha
out vec2 tuv; out vec4 vcol;
void main() {
  float c = cos(inst.w), s = sin(inst.w); vec2 q = vec2(c * p.x - s * p.y, s * p.x + c * p.y) * inst.z;
  vec2 px = inst.xy + q; tuv = p * 0.5 + 0.5; vcol = icol;
  gl_Position = vec4(px.x / res.x * 2.0 - 1.0, 1.0 - px.y / res.y * 2.0, 0.0, 1.0);
}`;
export const SMOKE_FS = `#version 300 es
precision mediump float; uniform sampler2D puff; in vec2 tuv; in vec4 vcol; out vec4 o;
void main() { float a = texture(puff, tuv).r * vcol.a; o = vec4(vcol.rgb * a, a); }`;

// Fade the persistent firework buffer (short "exposure" trails).
export const FADE_FS = `#version 300 es
precision mediump float; uniform float k; out vec4 o; void main() { o = vec4(k); }`;

// Downsample (13-tap-ish box) and separable Gaussian blur for the bloom chain.
export const DOWN_FS = `#version 300 es
precision mediump float; uniform sampler2D src; uniform vec2 texel; in vec2 uv; out vec4 o;
void main() {
  vec2 t = vec2(uv.x, 1.0 - uv.y);
  vec3 c = texture(src, t + texel * vec2(-1, -1)).rgb + texture(src, t + texel * vec2(1, -1)).rgb +
           texture(src, t + texel * vec2(-1, 1)).rgb + texture(src, t + texel * vec2(1, 1)).rgb;
  o = vec4(c * 0.25, 1.0);
}`;
export const BLUR_FS = `#version 300 es
precision mediump float; uniform sampler2D src; uniform vec2 dir; in vec2 uv; out vec4 o;
void main() {
  vec2 t = vec2(uv.x, 1.0 - uv.y);
  vec3 c = texture(src, t).rgb * 0.227027;
  c += (texture(src, t + dir * 1.3846).rgb + texture(src, t - dir * 1.3846).rgb) * 0.316216;
  c += (texture(src, t + dir * 3.2308).rgb + texture(src, t - dir * 3.2308).rgb) * 0.070270;
  o = vec4(c, 1.0);
}`;

// Final composite: scenery lit by the bursts, sky glow, water reflections, smoke, fireworks, front silhouettes,
// weather overlay, bloom, tone mapping, vignette and film grain.
export const COMPOSITE_FS = `#version 300 es
precision highp float;
uniform sampler2D back, front, mat, fw, smoke, b0, b1, b2, wx, skyfx;
uniform vec4 L[8]; uniform vec3 LC[8]; uniform int nL;
uniform vec2 res; uniform float wl, time, flash, exposure, bloom, grain, useWx, sky, useSky;
in vec2 uv; out vec4 o;
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
vec3 rt(sampler2D t, vec2 u) { return texture(t, vec2(u.x, 1.0 - u.y)).rgb; }
vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
vec3 lightAt(vec2 px) {
  vec3 s = vec3(0.0);
  for (int i = 0; i < 8; i++) {
    if (i >= nL) break;
    vec2 d = (px - L[i].xy) / L[i].z; float q = 1.0 + dot(d, d); s += LC[i] * L[i].w / (q * q);
  }
  return s / (1.0 + dot(s, vec3(0.3, 0.5, 0.2)) * 0.6);         // soft limit: many bursts do not wash the scene out
}
void main() {
  vec2 px = uv * res;
  vec4 m = texture(mat, uv);
  vec3 lt = lightAt(px) * exposure;                                  // exposure scales only what the fireworks add,
                                                                     // so the static scene stays put (GIF exports)
  vec3 col = lin(texture(back, uv).rgb);
  col += lt * (m.r * 0.16 + m.b * sky * 0.018 + m.g * 0.02) + vec3(0.6, 0.65, 0.8) * min(flash, 1.5) * 0.004 * m.b;
  if (useSky > 0.5) { vec4 sf = texture(skyfx, uv); col = col * (1.0 - sf.a) + lin(sf.rgb) * sf.a; }  // sky effects layer
  vec3 f = rt(fw, uv) * exposure;
  if (m.g > 0.5 && uv.y > wl) {                                       // reflections on water
    float d = uv.y - wl;
    vec2 r = vec2(uv.x + (sin(uv.y * 900.0 + time * 2.1) * 0.6 + sin(uv.y * 310.0 - time * 1.3)) * d * 0.012,
                  wl - d * 0.85);
    vec3 refl = rt(fw, r) * 0.9 + rt(b0, r) * 0.6 + rt(b1, r) * 0.5;
    col += refl * exposure * m.g * (0.35 + 0.4 * d / (1.0 - wl));
  }
  vec4 sm = texture(smoke, vec2(uv.x, 1.0 - uv.y));
  col = col * (1.0 - sm.a) + sm.rgb;
  col += f * (1.0 - 0.35 * sm.a);
  vec4 fr = texture(front, uv);
  vec3 fl = lin(fr.rgb) + lt * m.r * 0.12;
  col = mix(col, fl, fr.a);
  if (useWx > 0.5) { vec4 w = texture(wx, uv); col = mix(col, lin(w.rgb), w.a); }
  col += (rt(b0, uv) * 0.55 + rt(b1, uv) * 0.45 + rt(b2, uv) * 0.5) * bloom * exposure;
  col = aces(col);
  col = pow(col, vec3(1.0 / 2.2));
  vec2 q = uv - 0.5; col *= 1.0 - dot(q, q) * 0.55;                   // vignette
  col += (h(px + fract(time) * 91.7) - 0.5) * grain;                 // film grain
  o = vec4(col, 1.0);
}`;
