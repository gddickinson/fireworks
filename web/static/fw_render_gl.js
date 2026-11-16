// WebGL2 renderer of the realistic display: stars as additive HDR point sprites in a persistent (fading) buffer,
// smoke puffs lit by the bursts, a three-level bloom, and one composite pass (fw_shaders.js) that lights the scenery,
// reflects the fireworks in water, tone-maps and adds vignette and grain. Throws if WebGL2 is unavailable (the view
// then uses fw_render_2d.js).
import * as SH from './fw_shaders.js';
import { STRIDE } from './fw_atmos.js';
import { fbm2 } from './fw_noise.js';

function compile(gl, vs, fs) {
  const p = gl.createProgram();
  for (const [type, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('shader: ' + gl.getShaderInfoLog(s));
    gl.attachShader(p, s);
  }
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(p));
  const u = {}, n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i); u[info.name.replace('[0]', '')] = gl.getUniformLocation(p, info.name); }
  return { p, u };
}

export class GLRenderer {
  constructor(canvas) {
    const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, premultipliedAlpha: false, preserveDrawingBuffer: false });
    if (!gl) throw new Error('WebGL2 unavailable');
    this.gl = gl; this.canvas = canvas; this.kind = 'webgl2';
    this.hdr = !!gl.getExtension('EXT_color_buffer_float');
    gl.getExtension('OES_texture_float_linear');
    this.P = {
      star: compile(gl, SH.STAR_VS, SH.STAR_FS), smoke: compile(gl, SH.SMOKE_VS, SH.SMOKE_FS),
      fade: compile(gl, SH.QUAD_VS, SH.FADE_FS), down: compile(gl, SH.QUAD_VS, SH.DOWN_FS),
      blur: compile(gl, SH.QUAD_VS, SH.BLUR_FS), comp: compile(gl, SH.QUAD_VS, SH.COMPOSITE_FS),
    };
    this.quad = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    this.starBuf = gl.createBuffer(); this.smokeBuf = gl.createBuffer();
    this.vaoQuad = this.vao(this.P.comp.p, [['p', this.quad, 2, 0, 0]]);
    this.vaoStar = this.vao(this.P.star.p, [['pos', this.starBuf, 2, STRIDE * 4, 0], ['size', this.starBuf, 1, STRIDE * 4, 8],
      ['col', this.starBuf, 3, STRIDE * 4, 12], ['core', this.starBuf, 1, STRIDE * 4, 24]]);
    this.vaoSmoke = this.vao(this.P.smoke.p, [['p', this.quad, 2, 0, 0], ['inst', this.smokeBuf, 4, 32, 0, 1], ['icol', this.smokeBuf, 4, 32, 16, 1]]);
    this.puffTex = this.texFromPixels(puffPixels(64), 64, 64);
    this.tex = {}; this.wxCanvas = null; this.W = 0; this.H = 0;
  }
  vao(prog, attrs) {
    const gl = this.gl, v = gl.createVertexArray();
    gl.bindVertexArray(v);
    for (const [name, buf, size, stride, off, div] of attrs) {
      const loc = gl.getAttribLocation(prog, name);
      if (loc < 0) continue;
      gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, stride, off);
      if (div) gl.vertexAttribDivisor(loc, div);
    }
    gl.bindVertexArray(null);
    return v;
  }
  texFromPixels(px, w, h) {
    const gl = this.gl, t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, w, h, 0, gl.RED, gl.UNSIGNED_BYTE, px);
    this.params(gl.LINEAR);
    return t;
  }
  params(filter) {
    const gl = this.gl;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  }
  target(w, h, hdr = this.hdr) {
    const gl = this.gl, t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, hdr ? gl.RGBA16F : gl.RGBA8, w, h, 0, gl.RGBA, hdr ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE, null);
    this.params(gl.LINEAR);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    return { t, fb, w, h };
  }
  resize(W, H) {
    if (W === this.W && H === this.H) return;
    const gl = this.gl;
    for (const k of Object.keys(this.rt || {})) { gl.deleteTexture(this.rt[k].t); gl.deleteFramebuffer(this.rt[k].fb); }
    this.W = W; this.H = H;
    const q = (d) => [Math.max(1, Math.round(W / d)), Math.max(1, Math.round(H / d))];
    this.rt = { fw: this.target(W, H), smoke: this.target(...q(2), false),
      a0: this.target(...q(4)), c0: this.target(...q(4)), a1: this.target(...q(8)), c1: this.target(...q(8)),
      a2: this.target(...q(16)), c2: this.target(...q(16)) };
  }
  upload(name, canvas) {
    const gl = this.gl;
    if (!this.tex[name]) this.tex[name] = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.tex[name]);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    this.params(gl.LINEAR);
  }
  setScenery(S) { this.upload('back', S.back); this.upload('front', S.front); this.upload('mat', S.mat); this.scenery = S; }
  clearTrails() { const gl = this.gl; gl.bindFramebuffer(gl.FRAMEBUFFER, this.rt.fw.fb); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); }

  pass(prog, rt, setup) {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, rt ? rt.fb : null);
    gl.viewport(0, 0, rt ? rt.w : this.W, rt ? rt.h : this.H);
    gl.useProgram(prog.p); setup(prog.u);
    gl.bindVertexArray(this.vaoQuad); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
  bind(unit, tex, loc) { const gl = this.gl; gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); gl.uniform1i(loc, unit); }

  // F: { parts (Float32Array), n, puffs (from Atmos.screenPuffs), lights (Atmos.screenLights), flash, time,
  //      persist, exposure, bloom, grain, weather (canvas or null) }
  render(F) {
    const gl = this.gl, rt = this.rt, W = this.W, H = this.H;
    gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND);
    // 1. fireworks buffer: fade, then add the stars
    gl.blendFunc(gl.ZERO, gl.SRC_COLOR);
    this.pass(this.P.fade, rt.fw, u => gl.uniform1f(u.k, F.persist));
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.useProgram(this.P.star.p); gl.uniform2f(this.P.star.u.res, W, H);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.starBuf); gl.bufferData(gl.ARRAY_BUFFER, F.parts.subarray(0, F.n * STRIDE), gl.STREAM_DRAW);
    gl.bindVertexArray(this.vaoStar); gl.drawArrays(gl.POINTS, 0, F.n);
    // 2. smoke (half resolution, premultiplied)
    gl.bindFramebuffer(gl.FRAMEBUFFER, rt.smoke.fb); gl.viewport(0, 0, rt.smoke.w, rt.smoke.h);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    if (F.puffs.length) {
      const d = new Float32Array(F.puffs.length * 8);
      F.puffs.forEach((p, i) => { d.set([p.x, p.y, p.r, p.rot, p.rgb[0], p.rgb[1], p.rgb[2], p.a], i * 8); });
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.useProgram(this.P.smoke.p); gl.uniform2f(this.P.smoke.u.res, W, H); this.bind(0, this.puffTex, this.P.smoke.u.puff);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.smokeBuf); gl.bufferData(gl.ARRAY_BUFFER, d, gl.STREAM_DRAW);
      gl.bindVertexArray(this.vaoSmoke); gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, F.puffs.length);
    }
    // 3. bloom chain
    gl.disable(gl.BLEND);
    let src = rt.fw;
    for (const [a, c] of [[rt.a0, rt.c0], [rt.a1, rt.c1], [rt.a2, rt.c2]]) {
      this.pass(this.P.down, a, u => { this.bind(0, src.t, u.src); gl.uniform2f(u.texel, 1 / src.w, 1 / src.h); });
      this.pass(this.P.blur, c, u => { this.bind(0, a.t, u.src); gl.uniform2f(u.dir, 1 / a.w, 0); });
      this.pass(this.P.blur, a, u => { this.bind(0, c.t, u.src); gl.uniform2f(u.dir, 0, 1 / a.h); });
      src = a;
    }
    // 4. composite to the screen
    if (F.weather) this.upload('wx', F.weather);
    const S = this.scenery, Ls = F.lights;
    this.pass(this.P.comp, null, u => {
      this.bind(0, this.tex.back, u.back); this.bind(1, this.tex.front, u.front); this.bind(2, this.tex.mat, u.mat);
      this.bind(3, rt.fw.t, u.fw); this.bind(4, rt.smoke.t, u.smoke);
      this.bind(5, rt.a0.t, u.b0); this.bind(6, rt.a1.t, u.b1); this.bind(7, rt.a2.t, u.b2);
      this.bind(8, F.weather ? this.tex.wx : this.tex.back, u.wx);
      const Lv = new Float32Array(32), Lc = new Float32Array(24);
      Ls.forEach((L, i) => { Lv.set([L.x, L.y, L.r, L.I], i * 4); Lc.set(L.col.map(v => v / 255), i * 3); });
      gl.uniform4fv(u.L, Lv); gl.uniform3fv(u.LC, Lc); gl.uniform1i(u.nL, Ls.length);
      gl.uniform2f(u.res, W, H); gl.uniform1f(u.wl, S.water ? S.water / S.H : 2.0);
      gl.uniform1f(u.time, F.time); gl.uniform1f(u.flash, F.flash); gl.uniform1f(u.exposure, F.exposure);
      gl.uniform1f(u.bloom, F.bloom); gl.uniform1f(u.grain, F.grain); gl.uniform1f(u.useWx, F.weather ? 1 : 0);
      gl.uniform1f(u.sky, 1);
    });
  }
}

// A soft, cloudy puff: radial falloff modulated by fractal noise (R8, size x size).
function puffPixels(size) {
  const px = new Uint8Array(size * size);
  for (let j = 0; j < size; j++) for (let i = 0; i < size; i++) {
    const x = (i + 0.5) / size * 2 - 1, y = (j + 0.5) / size * 2 - 1, r = Math.sqrt(x * x + y * y);
    const fall = Math.max(0, 1 - r) ** 1.5, n = fbm2(17, i / size * 4, j / size * 4, 4);
    px[j * size + i] = Math.round(255 * Math.min(1, fall * (0.4 + 1.2 * n)));
  }
  return px;
}
