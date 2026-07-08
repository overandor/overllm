'use strict';

const {
  DEFAULT_MAX_INPUT_BYTES,
  canonicalize,
  corsHeaders,
  healthPayload,
  parseBody,
  validateTextPayload
} = require('../lib/rstf-core.cjs');

module.exports = async function handler(req, res) {
  const headers = corsHeaders(req.headers.origin);
  for (const [key, value] of Object.entries(headers)) res.setHeader(key, value);
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'no-store');
  res.setHeader('x-content-type-options', 'nosniff');
  res.setHeader('referrer-policy', 'no-referrer');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method === 'GET') return res.status(200).json(healthPayload());
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const maxInputBytes = Number(process.env.RSTF_MAX_BYTES || DEFAULT_MAX_INPUT_BYTES);
    const payload = typeof req.body === 'object' && req.body !== null
      ? req.body
      : parseBody(req.body, req.headers['content-type'] || '');

    validateTextPayload(payload, maxInputBytes);

    const result = canonicalize(payload.text, {
      forceReverse: payload.forceReverse === true,
      nfkc: payload.nfkc === true,
      stripZeroWidth: payload.stripZeroWidth !== false
    });

    return res.status(200).json({ ok: true, result });
  } catch (error) {
    const status = error.statusCode || 500;
    return res.status(status).json({ ok: false, error: error.message || 'Internal error' });
  }
};
