// Built structures of the realistic scenery: city skylines with lit windows and aviation lights (moved unchanged
// from fw_scenery.js), street-light rows, soft light glows, and the newer waterfront pieces: tall towers with lit
// crowns, a ferris wheel, and a cable-stayed bridge. Colour goes to `c`, material (albedo) to `m`; positions of
// blinking lights are pushed to S.beacons (device px) for the scene plug-ins (fw_scene_fx.js).
import { prng } from './fw_noise.js';
import { mat, rgb } from './fw_scenery_parts.js';
import { tone } from './fw_scenery_sky.js';

// Soft round glow (a lamp, a lit window's halo): radial gradient, `core` fraction of r at full strength.
export function glow(c, x, y, r, col, a = 0.6, core = 0.12) {
  const g = c.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgb(...col, a)); g.addColorStop(core, rgb(...col, a * 0.45)); g.addColorStop(1, rgb(...col, 0));
  c.fillStyle = g; c.fillRect(x - r, y - r, 2 * r, 2 * r);
}

// City skyline standing on the far bank at wl. Far: lower, hazier, tiny windows. Near: towers with roof details.
// opts.S (optional): scene, for dusk tones and beacon positions; opts.tall: taller cluster (big-city waterfront).
export function skyline(c, m, W, H, wl, seed, { far, S = null, tall = 1, sc: scIn = null }) {
  const rnd = prng(seed), sc = scIn ?? H / 800;
  const centre = 0.3 + rnd() * 0.4;
  let x = -rnd() * 30 * sc;
  while (x < W) {
    const w = (far ? 14 + rnd() * 30 : 22 + rnd() * 48) * sc;
    const d = (x / W - centre) / 0.28, cluster = Math.exp(-d * d);
    let h = (far ? 30 + rnd() * 50 + 90 * cluster * rnd() : 24 + rnd() * 50 + 170 * tall * cluster * Math.pow(rnd(), 0.7)) * sc;
    if (!far && rnd() < 0.12) h *= 0.35;
    building(c, m, x, wl, w, h, rnd, far, sc, S);
    x += w + (rnd() < 0.2 ? rnd() * 8 * sc : 0);
  }
}

export function building(c, m, x, base, w, h, rnd, far, sc, S = null) {
  const top = base - h, col = S ? tone(S, far ? [24, 24, 36] : [9, 10, 16], far ? 0.8 : 0.4) : far ? [24, 24, 36] : [9, 10, 16];
  const g = c.createLinearGradient(0, top, 0, base);
  g.addColorStop(0, rgb(...col.map(v => v * 1.25))); g.addColorStop(1, rgb(...col));
  c.fillStyle = g; c.fillRect(x, top, w, h);
  m.fillStyle = mat(far ? 0.25 : 0.35); m.fillRect(x, top, w, h);
  let roof = top;
  const r = rnd();                                            // roof details
  c.fillStyle = rgb(...col);
  if (!far && r < 0.3 && h > 120 * sc) {                      // setbacks
    const w2 = w * 0.7, h2 = h * 0.12; c.fillRect(x + (w - w2) / 2, top - h2, w2, h2);
    const w3 = w * 0.4, h3 = h * 0.08; c.fillRect(x + (w - w3) / 2, top - h2 - h3, w3, h3);
    m.fillRect(x + (w - w2) / 2, top - h2, w2, h2); roof = top - h2 - h3;
  } else if (!far && r < 0.45 && h > 150 * sc) {               // spire
    c.beginPath(); c.moveTo(x + w * 0.3, top); c.lineTo(x + w / 2, top - h * 0.22); c.lineTo(x + w * 0.7, top); c.fill();
    roof = top - h * 0.22;
  } else if (r < 0.65) {                                      // plant room / water tank
    c.fillRect(x + w * (0.1 + rnd() * 0.4), top - 6 * sc, w * 0.3, 6 * sc);
  }
  if (!far && (r > 0.85 || h > 220 * sc)) {                  // antenna with a red aviation light
    c.fillStyle = rgb(20, 20, 26); c.fillRect(x + w / 2 - sc * 0.6, roof - 26 * sc, 1.2 * sc, 26 * sc);
    c.fillStyle = rgb(255, 40, 30, 0.9); c.beginPath(); c.arc(x + w / 2, roof - 26 * sc, 1.6 * sc, 0, 6.28); c.fill();
    const gl = c.createRadialGradient(x + w / 2, roof - 26 * sc, 0, x + w / 2, roof - 26 * sc, 9 * sc);
    gl.addColorStop(0, rgb(255, 40, 30, 0.35)); gl.addColorStop(1, rgb(255, 40, 30, 0));
    c.fillStyle = gl; c.fillRect(x + w / 2 - 9 * sc, roof - 35 * sc, 18 * sc, 18 * sc);
    S?.beacons.push([x + w / 2, roof - 26 * sc, 1.6 * sc]);
  }
  windows(c, x, top, w, base, rnd, far, sc);
}

// Window grid of a building face: a random share lit, warm or cool, sometimes whole floors.
export function windows(c, x, top, w, base, rnd, far, sc) {
  const cw = (far ? 2.2 : 3.2) * sc, chh = (far ? 3.2 : 4.4) * sc, lit = 0.06 + rnd() * (far ? 0.2 : 0.32);
  const warm = rnd() < 0.7, floorLit = rnd() < 0.3;
  for (let fy = top + chh; fy < base - chh * 1.5; fy += chh * 1.6) {
    const wholeFloor = floorLit && rnd() < 0.15;
    for (let fx = x + cw * 0.7; fx < x + w - cw * 1.2; fx += cw * 1.7) {
      if (!(wholeFloor || rnd() < lit)) continue;
      const t = warm ? (rnd() < 0.85 ? [255, 196, 120] : [190, 215, 255]) : (rnd() < 0.7 ? [200, 225, 255] : [255, 210, 150]);
      c.fillStyle = rgb(...t, (far ? 0.35 : 0.55) + rnd() * 0.4);
      c.fillRect(fx, fy, cw, chh * 0.75);
    }
  }
}

export function streetLights(c, W, H, wl, seed, sc = H / 800) {
  const rnd = prng(seed);
  for (let x = rnd() * 20 * sc; x < W; x += (14 + rnd() * 18) * sc) {
    const y = wl - (2 + rnd() * 3) * sc, r = (6 + rnd() * 6) * sc, col = rnd() < 0.75 ? [255, 170, 80] : [220, 235, 255];
    const g = c.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgb(...col, 0.9)); g.addColorStop(0.15, rgb(...col, 0.35)); g.addColorStop(1, rgb(...col, 0));
    c.fillStyle = g; c.fillRect(x - r, y - r, 2 * r, 2 * r);
  }
}

// A slender tower with a floodlit crown: a tapering shaft, a glowing pyramidal or stepped crown, a mast with a
// beacon. Generic shapes only (no real buildings).
export function crownTower(S, c, m, x, base, w, h, rnd, sc, col) {
  const body = tone(S, [8, 9, 15], 0.35), top = base - h;
  const g = c.createLinearGradient(x, 0, x + w, 0);           // a faint lit edge on one side
  g.addColorStop(0, rgb(...body.map(v => v * 1.6))); g.addColorStop(0.25, rgb(...body)); g.addColorStop(1, rgb(...body.map(v => v * 0.8)));
  c.fillStyle = g; c.fillRect(x, top, w, h); m.fillStyle = mat(0.35); m.fillRect(x, top, w, h);
  windows(c, x, top + 4 * sc, w, base, rnd, false, sc);
  c.fillStyle = rgb(...col, 0.25); c.fillRect(x + w * 0.15, top, 1.2 * sc, h * 0.7); c.fillRect(x + w * 0.85 - 1.2 * sc, top, 1.2 * sc, h * 0.7);
  const kind = rnd(), ch = h * (0.1 + rnd() * 0.06);
  c.save();
  if (kind < 0.5) {                                           // pyramid crown, lit from below
    c.beginPath(); c.moveTo(x, top); c.lineTo(x + w / 2, top - ch); c.lineTo(x + w, top); c.closePath();
  } else {                                                    // stepped crown
    c.beginPath(); c.moveTo(x, top);
    for (let i = 0; i < 4; i++) { const ix = w * 0.12 * (i + 1), y = top - ch * (i + 1) / 4; c.lineTo(x + ix - w * 0.12, y); c.lineTo(x + ix, y); }
    c.lineTo(x + w - w * 0.48, top - ch); for (let i = 3; i >= 0; i--) { const ix = w * 0.12 * (i + 1), y = top - ch * (i + 1) / 4; c.lineTo(x + w - ix, y); c.lineTo(x + w - ix + w * 0.12, y); }
    c.lineTo(x + w, top); c.closePath();
  }
  const cg = c.createLinearGradient(0, top - ch, 0, top);
  cg.addColorStop(0, rgb(...col, 0.35)); cg.addColorStop(1, rgb(...col, 0.95));
  c.fillStyle = cg; c.fill(); c.clip();
  c.fillStyle = rgb(0, 0, 0, 0.35); for (let i = 1; i < 6; i++) c.fillRect(x + w * i / 6 - sc * 0.4, top - ch, sc * 0.8, ch);
  c.restore();
  m.fillStyle = mat(0.5); m.fillRect(x, top - ch, w, ch);
  glow(c, x + w / 2, top - ch * 0.4, w * 1.4, col, 0.22, 0.2);
  const mh = h * 0.12;                                        // mast with an aviation light
  c.fillStyle = rgb(...body.map(v => v * 1.8)); c.fillRect(x + w / 2 - sc * 0.6, top - ch - mh, 1.2 * sc, mh);
  S.beacons.push([x + w / 2, top - ch - mh, 1.8 * sc]);
  return top - ch - mh;
}

// Ferris wheel with lit rim and cabins on the waterfront (rim radius r, hub at cx, cy).
export function ferrisWheel(c, m, cx, cy, r, sc, rnd) {
  c.save();
  c.strokeStyle = rgb(30, 32, 44); c.lineWidth = 2.2 * sc;     // A-frame legs
  c.beginPath(); c.moveTo(cx - r * 0.45, cy + r * 1.12); c.lineTo(cx, cy); c.lineTo(cx + r * 0.45, cy + r * 1.12); c.stroke();
  m.strokeStyle = mat(0.4); m.lineWidth = 2.2 * sc; m.beginPath(); m.moveTo(cx - r * 0.45, cy + r * 1.12); m.lineTo(cx, cy); m.lineTo(cx + r * 0.45, cy + r * 1.12); m.stroke();
  const n = 32, hue = rnd() < 0.5 ? [120, 200, 255] : [255, 120, 210];
  c.strokeStyle = rgb(...hue, 0.35); c.lineWidth = 0.7 * sc;  // spokes
  c.beginPath(); for (let i = 0; i < n; i += 2) { const a = i / n * 6.2832; c.moveTo(cx, cy); c.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); } c.stroke();
  for (const [rr, a, w] of [[r, 0.9, 1.6], [r * 0.93, 0.5, 1]]) {
    c.strokeStyle = rgb(...hue, a); c.lineWidth = w * sc; c.beginPath(); c.arc(cx, cy, rr, 0, 6.2832); c.stroke();
  }
  glow(c, cx, cy, r * 1.35, hue, 0.12, 0.5);
  for (let i = 0; i < n; i++) {                               // cabins: bright dots on the rim
    const a = i / n * 6.2832, x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    c.fillStyle = rgb(255, 235, 200, 0.95); c.fillRect(x - 1.3 * sc, y, 2.6 * sc, 2.4 * sc);
  }
  c.restore();
}

// Cable-stayed bridge across the frame (side view): deck at `deck` (px), pylons at fractions `pylons` of W rising to
// `topY`, fans of lit stay cables, a row of deck lights. Paints into c (colour) and m (material); returns nothing.
export function cableBridge(S, c, m, { deck, topY, pylons, sc, seed, wl }) {
  const { W } = S, rnd = prng(seed), dk = tone(S, [10, 11, 16], 0.3), thick = 7 * sc;
  for (const k of [c, m]) {                                   // deck girder and its piers
    k.fillStyle = k === m ? mat(0.35) : rgb(...dk); k.fillRect(0, deck, W, thick);
    for (const p of pylons) { const x = p * W; k.fillRect(x - 9 * sc, deck, 18 * sc, wl - deck); }
  }
  const span = (pylons[1] - pylons[0]) * W, nC = 9;
  for (const p of pylons) {                                   // pylons: tapered inverted-Y legs merging into a mast
    const x = p * W, mid = deck - (deck - topY) * 0.35;
    for (const k of [c, m]) {
      k.fillStyle = k === m ? mat(0.45) : rgb(...dk.map(v => v * 1.3));
      k.beginPath(); k.moveTo(x - 16 * sc, deck + thick); k.lineTo(x - 4 * sc, mid); k.lineTo(x - 3 * sc, topY);
      k.lineTo(x + 3 * sc, topY); k.lineTo(x + 4 * sc, mid); k.lineTo(x + 16 * sc, deck + thick);
      k.lineTo(x + 10 * sc, deck + thick); k.lineTo(x, mid + 14 * sc); k.lineTo(x - 10 * sc, deck + thick); k.closePath(); k.fill();
    }
    const fl = c.createLinearGradient(0, topY, 0, deck);       // floodlight washing up the pylon
    fl.addColorStop(0, rgb(200, 220, 255, 0.05)); fl.addColorStop(1, rgb(200, 220, 255, 0.28));
    c.fillStyle = fl; c.fillRect(x - 4 * sc, topY, 8 * sc, deck - topY);
    S.beacons.push([x, topY - 2 * sc, 2 * sc]);
    c.lineWidth = 0.9 * sc;
    for (let i = 1; i <= nC; i++) {                           // stay cables both ways, anchored along the mast top
      const ay = topY + (mid - topY) * 0.45 * i / nC, reach = span * 0.46 * i / nC;
      for (const s of [-1, 1]) {
        const ex = x + s * reach;
        const cg = c.createLinearGradient(x, ay, ex, deck);
        cg.addColorStop(0, rgb(170, 200, 255, 0.35)); cg.addColorStop(1, rgb(210, 230, 255, 0.6));
        c.strokeStyle = cg; c.beginPath(); c.moveTo(x, ay); c.lineTo(ex, deck); c.stroke();
        m.strokeStyle = mat(0.3); m.lineWidth = 0.9 * sc; m.beginPath(); m.moveTo(x, ay); m.lineTo(ex, deck); m.stroke();
      }
    }
  }
  for (let x = rnd() * 10 * sc; x < W; x += 22 * sc) {         // deck lights: lamps along the parapet, glow on the girder
    c.fillStyle = rgb(255, 205, 140, 0.95); c.fillRect(x - sc, deck - 3 * sc, 2 * sc, 2 * sc);
    glow(c, x, deck - 2 * sc, 7 * sc, [255, 180, 100], 0.4);
  }
  c.fillStyle = rgb(120, 150, 210, 0.22); c.fillRect(0, deck + thick - 1.2 * sc, W, 1.2 * sc);   // lit underside edge
}
