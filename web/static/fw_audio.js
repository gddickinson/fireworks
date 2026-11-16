// Synthesised firework sound (WebAudio, off until the user turns it on): mortar thumps at launch, a low boom and a
// rumbling noise tail for each burst, crackle clicks, all delayed by the time sound takes to travel from the shell
// (distance / 343 m/s) and quieter with distance. A compressor keeps finales from clipping. `stream()` gives a
// MediaStream of the mix so video exports can include it.
const SPEED_OF_SOUND = 343;

export class FireworkAudio {
  constructor() { this.ctx = null; this.on = false; this.budget = 0; }
  enable() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      const c = this.ctx = new AC();
      this.comp = c.createDynamicsCompressor();
      this.comp.threshold.value = -18; this.comp.ratio.value = 6;
      this.master = c.createGain(); this.master.gain.value = 0.8;
      this.master.connect(this.comp); this.comp.connect(c.destination);
      const n = c.sampleRate * 2, buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
      let b = 0;
      for (let i = 0; i < n; i++) { const w = Math.random() * 2 - 1; b = 0.97 * b + 0.03 * w; d[i] = w * 0.6 + b * 4; }
      this.noise = buf;
    }
    this.ctx.resume?.();
    this.on = true;
    return true;
  }
  disable() { this.on = false; }
  stream() {
    if (!this.ctx) return null;
    if (!this.dest) { this.dest = this.ctx.createMediaStreamDestination(); this.comp.connect(this.dest); }
    return this.dest.stream;
  }
  // Called with each frame's sim events (fw_pyro.js): ['launch', x, z, type] | ['burst', x, y, z, col, s] | ['crackle', x, y, z]
  onEvents(events) {
    if (!this.on || !this.ctx || this.ctx.state !== 'running') return;
    this.budget = Math.min(this.budget + 1, 6);
    for (const e of events) {
      if (e[0] === 'launch') this.thump(this.delay(e[1], 0, e[2]), e[2]);
      else if (e[0] === 'burst') this.boom(this.delay(e[1], e[2], e[3]), Math.hypot(e[1], e[2], e[3]), e[5]);
      else if (e[0] === 'crackle' && this.budget > 0) { this.budget--; this.crackle(this.delay(e[1], e[2], e[3]), e[3]); }
    }
  }
  delay(x, y, z) { return this.ctx.currentTime + Math.hypot(x, y, z) / SPEED_OF_SOUND; }
  src(t, dur, rate = 1) {
    const s = this.ctx.createBufferSource();
    s.buffer = this.noise; s.playbackRate.value = rate;
    s.start(t, Math.random() * 1.5, dur);
    return s;
  }
  env(t, peak, attack, decay) {
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(peak, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    return g;
  }
  thump(t, dist) {                                            // mortar lift charge: short low thud and a hiss
    const c = this.ctx, v = 0.5 * (400 / dist) ** 1.5;
    const o = c.createOscillator(); o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.15);
    const g = this.env(t, v, 0.004, 0.2); o.connect(g).connect(this.master); o.start(t); o.stop(t + 0.3);
    const f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 2500; f.Q.value = 0.6;
    const h = this.env(t, v * 0.12, 0.05, 0.9); this.src(t, 1.1, 1).connect(f).connect(h).connect(this.master);
  }
  boom(t, dist, strength = 1) {                               // burst: sub thump + filtered noise with a long rumble
    const c = this.ctx, v = Math.min(1.2, (0.9 + 0.3 * strength) * (450 / dist) ** 1.2);
    const o = c.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(75 + Math.random() * 20, t); o.frequency.exponentialRampToValueAtTime(28, t + 0.5);
    const g = this.env(t, v * 0.9, 0.003, 0.7); o.connect(g).connect(this.master); o.start(t); o.stop(t + 0.8);
    const f = c.createBiquadFilter(); f.type = 'lowpass';
    f.frequency.setValueAtTime(1800, t); f.frequency.exponentialRampToValueAtTime(140, t + 1.6);
    const h = this.env(t, v * 0.8, 0.004, 2.2); this.src(t, 2.4, 0.7).connect(f).connect(h).connect(this.master);
  }
  crackle(t, dist) {                                          // a handful of sharp clicks
    const v = 0.35 * (450 / dist);
    for (let i = 0; i < 6; i++) {
      const tt = t + Math.random() * 0.6, f = this.ctx.createBiquadFilter();
      f.type = 'highpass'; f.frequency.value = 1500 + Math.random() * 2500;
      const g = this.env(tt, v * (0.4 + Math.random() * 0.6), 0.001, 0.03);
      this.src(tt, 0.05, 1.5).connect(f).connect(g).connect(this.master);
    }
  }
}
