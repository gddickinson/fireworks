// node fw_text.test.mjs: message text handling (fw_text.js) and the shareable greeting link (msg_link.js).
import assert from 'node:assert/strict';
import { cleanText, splitMessages, wrapLines, MAX_CHARS, MAX_MESSAGES } from './fw_text.js';
import { decodeQuery, encodeQuery } from './msg_link.js';

let n = 0;
const test = (name, fn) => { fn(); n++; console.log('ok', name); };

test('messages are split on blank lines, cleaned and limited', () => {
  assert.deepEqual(splitMessages('Happy New Year!\n\n  2027 \n\n\n'), ['Happy New Year!', '2027']);
  assert.deepEqual(splitMessages('Happy\nBirthday\n\nAlex'), ['Happy\nBirthday', 'Alex']);
  assert.equal(splitMessages(Array(20).fill('x').join('\n\n')).length, MAX_MESSAGES);
  assert.equal([...cleanText('é'.repeat(200))].length, MAX_CHARS);
  assert.equal(cleanText('a\u0000b\u0007c'), 'abc');
  assert.equal(cleanText('🎉 新年快乐 ♥'), '🎉 新年快乐 ♥');           // Unicode kept, code points counted
});

test('word wrapping into balanced lines keeps explicit line breaks', () => {
  assert.deepEqual(wrapLines('Happy Birthday dear Alex', 2), ['Happy Birthday', 'dear Alex']);
  assert.deepEqual(wrapLines('One\nTwo three', 1), ['One', 'Two three']);
  assert.deepEqual(wrapLines('Supercalifragilistic', 3), ['Supercalifragilistic']);
});

test('greeting link round-trips the options', () => {
  const o = { text: 'Happy Birthday\n{name}!', name: 'Zoë', font: 'script', mode: 'gradient', c1: '#ff0000', c2: '#00ff88',
    size: 70, hold: 4, bg: 'Beach', opener: 'medium', finale: true };
  const hash = encodeQuery(o);
  assert.ok(hash.startsWith('#/messages?') && !hash.includes(' '));
  const q = Object.fromEntries(new URLSearchParams(hash.split('?')[1]));
  assert.deepEqual(decodeQuery(q), o);
});

test('hostile or broken links fall back to safe values', () => {
  const d = decodeQuery({ m: '<img src=x onerror=alert(1)>', f: 'javascript:', c: '"><b>', c1: 'red;x', s: '1e9', h: 'NaN', bg: '<x>' });
  assert.equal(d.text, '<img src=x onerror=alert(1)>');    // kept as text: the page escapes it, never parses it
  assert.equal(d.font, 'sans'); assert.equal(d.mode, 'rainbow'); assert.equal(d.c1, '#ffc83d');
  assert.equal(d.size, 100); assert.equal(d.hold, 3); assert.equal(d.bg, 'Cityscape');
  assert.ok(decodeQuery({ m: 'x'.repeat(5000) }).text.length <= MAX_CHARS * 6);
});

console.log(`${n} tests passed`);
