import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'

const STORE = join('/tmp', 'overllm-metrics.json')

let cached: any = null

function read() {
  if (cached) return cached
  if (existsSync(STORE)) {
    try { cached = JSON.parse(readFileSync(STORE, 'utf8')); return cached } catch {}
  }
  return null
}

function write(data: any) {
  cached = data
  writeFileSync(STORE, JSON.stringify(data))
}

export async function GET() {
  const data = read()
  if (!data) {
    return new Response(JSON.stringify({ status: 'no_data', message: 'No training metrics yet' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    })
  }
  return new Response(JSON.stringify(data), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
  })
}

export async function POST(request: Request) {
  const auth = request.headers.get('x-overllm-key')
  if (auth !== (process.env.OVERLLM_PUSH_KEY || 'overllm-local-dev')) {
    return new Response('Unauthorized', { status: 401 })
  }
  const body = await request.json()
  write(body)
  return new Response(JSON.stringify({ ok: true }), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
  })
}

export async function OPTIONS() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, x-overllm-key',
    },
  })
}
