'use strict';

const assert = require('assert');
const { canonicalize, utf8ByteLength, parseBody, validateTextPayload, corsHeaders } = require('../lib/rstf-core.cjs');

assert.strictEqual(utf8ByteLength('test'), 4);
assert.strictEqual(utf8ByteLength('ʇsǝʇ'), Buffer.byteLength('ʇsǝʇ', 'utf8'));

const upside = canonicalize('ʇsǝʇ');
assert.strictEqual(upside.canonical_text, 'test');
assert.ok(upside.transforms.includes('upside_down'));
assert.ok(upside.bytes_saved > 0);

const homoglyph = canonicalize('раураl');
assert.strictEqual(homoglyph.canonical_text, 'paypal');
assert.ok(homoglyph.transforms.includes('homoglyph'));
assert.ok(homoglyph.bytes_saved > 0);

const bidi = canonicalize('safe\u202Etext');
assert.strictEqual(bidi.canonical_text, 'safetext');
assert.ok(bidi.transforms.includes('bidi_control_stripped'));
assert.strictEqual(bidi.bytes_saved, 3);

const plain = canonicalize('tset');
assert.strictEqual(plain.canonical_text, 'tset');
assert.strictEqual(plain.bytes_saved, 0);

const forced = canonicalize('tset', { forceReverse: true });
assert.strictEqual(forced.canonical_text, 'test');
assert.strictEqual(forced.bytes_saved, 0);
assert.ok(forced.transforms.includes('reversed_forced'));

const jsonPayload = parseBody('{"text":"ʇsǝʇ"}', 'application/json');
assert.strictEqual(jsonPayload.text, 'ʇsǝʇ');
validateTextPayload(jsonPayload, 1024);

assert.throws(() => validateTextPayload({ text: 'x'.repeat(10) }, 3), /Input too large/);
assert.throws(() => parseBody('{bad json', 'application/json'), /Malformed JSON body/);

const oldAllow = process.env.RSTF_ALLOW_ORIGIN;
process.env.RSTF_ALLOW_ORIGIN = 'https://app.example';
assert.strictEqual(corsHeaders('https://evil.example')['access-control-allow-origin'], 'https://app.example');
assert.strictEqual(corsHeaders('https://app.example')['access-control-allow-origin'], 'https://app.example');
if (oldAllow === undefined) delete process.env.RSTF_ALLOW_ORIGIN; else process.env.RSTF_ALLOW_ORIGIN = oldAllow;

console.log('overllm-serverless-rstf tests passed');
