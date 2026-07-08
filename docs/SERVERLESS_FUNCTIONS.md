# OverLLM RSTF Netlify and Vercel Functions

This package exposes the OverLLM RSTF canonicalizer as two serverless endpoints:

- Vercel: `api/rstf.js`, available at `/api/rstf` and `/rstf`.
- Netlify: `netlify/functions/rstf.js`, available at `/.netlify/functions/rstf` and `/api/rstf` via redirect.

The implementation is intentionally dependency-free JavaScript. That is safer for Netlify/Vercel production deployment than requiring CMake or a native C++ shared object at cold start. The C++ package can remain the reference/embedded library; this package is the cloud function surface.

## API

### Health

```bash
curl https://YOUR_DOMAIN/api/rstf
```

### Canonicalize

```bash
curl -X POST https://YOUR_DOMAIN/api/rstf \
  -H 'content-type: application/json' \
  -d '{"text":"ʇsǝʇ"}'
```

### Response

```json
{
  "ok": true,
  "result": {
    "canonical_text": "test",
    "transforms": ["upside_down"],
    "raw_utf8_bytes": 7,
    "canonical_utf8_bytes": 4,
    "bytes_saved": 3,
    "byte_savings_ratio": 0.42857142857142855,
    "truth_label": "utf8_byte_length_proxy_not_real_tokenizer_count"
  }
}
```

## Request body

```json
{
  "text": "required string",
  "forceReverse": false,
  "nfkc": false,
  "stripZeroWidth": true
}
```

`forceReverse` is explicit because plain reversal cannot be safely inferred from bytes alone. `nfkc` is opt-in because compatibility normalization can erase distinctions that matter in math, legal, or multilingual text. `stripZeroWidth` defaults to true because invisible controls are usually not meaningful for LLM prompting.

## Local test

```bash
npm test
```

## Netlify deploy

```bash
npm i -g netlify-cli
netlify dev
netlify deploy --build
netlify deploy --prod --build
```

Netlify Functions are serverless files that respond to web requests. Netlify runs functions in ephemeral runtime environments and automatically scales them with traffic.

## Vercel deploy

```bash
npm i -g vercel
vercel dev
vercel
vercel --prod
```

Vercel Functions run server-side code without server management and support Node.js. This package uses a simple Node.js function and keeps the bundle small.

## Audit notes

Version 0.1.1 fixes CORS origin precedence when `RSTF_ALLOW_ORIGIN` is set, returns 400 for malformed JSON, and adds basic no-sniff/referrer security headers.

## Production checklist

- Set `RSTF_MAX_BYTES` to a safe request limit, for example `65536`.
- Set `RSTF_ALLOW_ORIGIN` to your app domain instead of `*` for browser use.
- Add platform-level rate limiting or firewall rules.
- Keep `truth_label` in every response so finance/API-cost claims remain defensible.
- Benchmark real tokenizers before claiming real billing savings.
- Add request logging with redaction if processing sensitive documents.
- Deploy preview first, then production.
