'use strict';

const {
  DEFAULT_MAX_INPUT_BYTES,
  canonicalize,
  corsHeaders,
  healthPayload,
  jsonResponse,
  parseBody,
  validateTextPayload
} = require('../../lib/rstf-core.cjs');

exports.handler = async function handler(event) {
  const headers = corsHeaders(event.headers && (event.headers.origin || event.headers.Origin));

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }

  if (event.httpMethod === 'GET') {
    return jsonResponse(healthPayload(), 200, headers);
  }

  if (event.httpMethod !== 'POST') {
    return jsonResponse({ ok: false, error: 'Method not allowed' }, 405, headers);
  }

  try {
    const maxInputBytes = Number(process.env.RSTF_MAX_BYTES || DEFAULT_MAX_INPUT_BYTES);
    const bodyText = event.isBase64Encoded
      ? Buffer.from(event.body || '', 'base64').toString('utf8')
      : (event.body || '');

    const payload = parseBody(bodyText, (event.headers && (event.headers['content-type'] || event.headers['Content-Type'])) || '');
    validateTextPayload(payload, maxInputBytes);

    const result = canonicalize(payload.text, {
      forceReverse: payload.forceReverse === true,
      nfkc: payload.nfkc === true,
      stripZeroWidth: payload.stripZeroWidth !== false
    });

    return jsonResponse({ ok: true, result }, 200, headers);
  } catch (error) {
    return jsonResponse({ ok: false, error: error.message || 'Internal error' }, error.statusCode || 500, headers);
  }
};
