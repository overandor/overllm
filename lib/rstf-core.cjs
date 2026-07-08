'use strict';

const crypto = require('crypto');

const DEFAULT_MAX_INPUT_BYTES = 64 * 1024;

// Bidi controls: LRE/RLE/PDF/LRO/RLO and isolate controls.
const BIDI_CONTROL_RE = /[\u202A-\u202E\u2066-\u2069]/gu;
const ZERO_WIDTH_RE = /[\u200B-\u200F\uFEFF]/gu;

const UPSIDE_DOWN_MAP = new Map(Object.entries({
  'ɐ': 'a', 'ɑ': 'a', 'ᵇ': 'b', 'ɔ': 'c', 'ǝ': 'e', 'ɟ': 'f',
  'ƃ': 'g', 'ɥ': 'h', 'ᴉ': 'i', 'ı': 'i', 'ɾ': 'j', 'ʞ': 'k',
  'ɯ': 'm', 'ɹ': 'r', 'ʇ': 't', 'ʌ': 'v', 'ʍ': 'w', 'ʎ': 'y',
  '∀': 'A', 'ᗺ': 'B', 'Ɔ': 'C', 'ᗡ': 'D', 'Ǝ': 'E', 'Ⅎ': 'F',
  '⅁': 'G', 'ſ': 'J', 'Ʞ': 'K', '˥': 'L', 'Ԁ': 'P', 'Ό': 'Q',
  'ᴚ': 'R', '⊥': 'T', '∩': 'U', 'Λ': 'V', '⅄': 'Y',
  '¡': '!', '¿': '?', '˙': '.', 'ʻ': ','
}));

const HOMOGLYPH_MAP = new Map(Object.entries({
  // Cyrillic uppercase confusables.
  'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
  'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X', 'У': 'Y',
  // Cyrillic lowercase confusables.
  'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'х': 'x',
  'у': 'y', 'і': 'i', 'ј': 'j', 'ӏ': 'l', 'ѕ': 's', 'ԁ': 'd',
  // Greek uppercase confusables.
  'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I',
  'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T',
  'Χ': 'X', 'Υ': 'Y',
  // Greek lowercase confusables.
  'ο': 'o', 'ρ': 'p', 'ν': 'v', 'χ': 'x', 'ι': 'i', 'α': 'a',
  'β': 'b', 'γ': 'y'
}));

function utf8ByteLength(text) {
  return Buffer.byteLength(String(text), 'utf8');
}

function sha256Hex(text) {
  return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

function unique(items) {
  return Array.from(new Set(items));
}

function normalizeInput(value, options = {}) {
  let text = String(value ?? '');
  if (options.nfkc === true) text = text.normalize('NFKC');
  if (options.stripZeroWidth !== false) text = text.replace(ZERO_WIDTH_RE, '');
  return text;
}

function canonicalize(text, options = {}) {
  const rawText = normalizeInput(text, options);
  const chars = Array.from(rawText);
  const out = [];
  const transforms = [];

  for (const ch of chars) {
    if (BIDI_CONTROL_RE.test(ch)) {
      transforms.push('bidi_control_stripped');
      BIDI_CONTROL_RE.lastIndex = 0;
      continue;
    }
    BIDI_CONTROL_RE.lastIndex = 0;

    if (UPSIDE_DOWN_MAP.has(ch)) {
      transforms.push('upside_down');
      out.push(UPSIDE_DOWN_MAP.get(ch));
      continue;
    }

    if (HOMOGLYPH_MAP.has(ch)) {
      transforms.push('homoglyph');
      out.push(HOMOGLYPH_MAP.get(ch));
      continue;
    }

    out.push(ch);
  }

  const shouldReverse = transforms.includes('upside_down') || options.forceReverse === true;
  if (shouldReverse) {
    out.reverse();
    if (options.forceReverse === true && !transforms.includes('upside_down')) {
      transforms.push('reversed_forced');
    }
  }

  const canonicalText = out.join('');
  const rawBytes = utf8ByteLength(rawText);
  const canonicalBytes = utf8ByteLength(canonicalText);
  const bytesSaved = rawBytes - canonicalBytes;

  return {
    version: 'overllm-rstf-serverless-0.1.1',
    raw_text: rawText,
    canonical_text: canonicalText,
    changed: rawText !== canonicalText || transforms.length > 0,
    transforms: unique(transforms),
    raw_utf8_bytes: rawBytes,
    canonical_utf8_bytes: canonicalBytes,
    bytes_saved: bytesSaved,
    byte_savings_ratio: rawBytes === 0 ? 0 : bytesSaved / rawBytes,
    raw_sha256: sha256Hex(rawText),
    canonical_sha256: sha256Hex(canonicalText),
    truth_label: 'utf8_byte_length_proxy_not_real_tokenizer_count'
  };
}

function jsonResponse(body, statusCode = 200, headers = {}) {
  return {
    statusCode,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff',
      'referrer-policy': 'no-referrer',
      ...headers
    },
    body: JSON.stringify(body)
  };
}

function badRequest(message) {
  const err = new Error(message);
  err.statusCode = 400;
  return err;
}

function parseBody(body, contentType = '') {
  if (body == null || body === '') return {};
  const bodyText = Buffer.isBuffer(body) ? body.toString('utf8') : String(body);
  if (contentType.includes('application/json') || bodyText.trim().startsWith('{')) {
    try {
      const parsed = JSON.parse(bodyText);
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw badRequest('Expected JSON object body: { "text": "..." }');
      }
      return parsed;
    } catch (error) {
      if (error.statusCode) throw error;
      throw badRequest('Malformed JSON body');
    }
  }
  return { text: bodyText };
}

function validateTextPayload(payload, maxInputBytes = DEFAULT_MAX_INPUT_BYTES) {
  if (!payload || typeof payload.text !== 'string') {
    const err = new Error('Expected JSON body: { "text": "..." }');
    err.statusCode = 400;
    throw err;
  }
  const bytes = utf8ByteLength(payload.text);
  if (bytes > maxInputBytes) {
    const err = new Error(`Input too large: ${bytes} bytes > ${maxInputBytes} byte limit`);
    err.statusCode = 413;
    throw err;
  }
}

function corsHeaders(origin) {
  const configured = String(process.env.RSTF_ALLOW_ORIGIN || '').trim();
  let allowOrigin = '*';

  if (configured) {
    const allowed = configured.split(',').map((item) => item.trim()).filter(Boolean);
    if (allowed.includes('*')) {
      allowOrigin = '*';
    } else if (origin && allowed.includes(origin)) {
      allowOrigin = origin;
    } else {
      // Deliberately return the first configured origin rather than reflecting an
      // untrusted origin. Browsers will block non-matching origins.
      allowOrigin = allowed[0] || 'null';
    }
  } else if (origin) {
    allowOrigin = origin;
  }

  return {
    'access-control-allow-origin': allowOrigin,
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'access-control-allow-headers': 'content-type,authorization,x-request-id',
    'access-control-max-age': '86400',
    'vary': 'origin'
  };
}

function healthPayload() {
  return {
    ok: true,
    service: 'overllm-rstf',
    version: 'overllm-rstf-serverless-0.1.1',
    endpoints: {
      post: 'Send { text, forceReverse?, nfkc?, stripZeroWidth? }',
      note: 'Returns UTF-8 byte proxy savings, not verified tokenizer billing savings.'
    }
  };
}

module.exports = {
  DEFAULT_MAX_INPUT_BYTES,
  canonicalize,
  corsHeaders,
  healthPayload,
  jsonResponse,
  parseBody,
  sha256Hex,
  utf8ByteLength,
  validateTextPayload
};
