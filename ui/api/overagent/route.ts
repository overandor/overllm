import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'

const STORE = join('/tmp', 'overagent-metrics.json')

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
    return new Response(JSON.stringify({
      status: 'awaiting_data',
      generation: 0,
      best_fitness: 0,
      avg_fitness: 0,
      diversity: 0,
      memory_size: 0,
      total_api_keys: 0,
      total_revenue: 0,
      total_payments: 0,
      errors_rewarded: 0,
      data_sources_active: 0,
      crawls_per_min: 0,
      ipfs_uploads: 0,
      ticks_processed: 0,
      uptime_seconds: 0,
    }), {
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
  return new Response(JSON.stringify({ ok: true, received: Date.now() }), {
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
