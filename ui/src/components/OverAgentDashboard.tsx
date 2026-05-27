import React, { useEffect, useState, useCallback } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, ScatterChart, Scatter, Cell,
} from 'recharts'
import {
  Dna, Zap, Brain, Database, Key, DollarSign, AlertTriangle,
  Globe, HardDrive, Activity, Clock, Wifi, WifiOff,
} from 'lucide-react'

const API = ''

interface Metrics {
  generation: number
  best_fitness: number
  avg_fitness: number
  diversity: number
  memory_size: number
  total_api_keys: number
  total_revenue: number
  total_payments: number
  errors_rewarded: number
  data_sources_active: number
  crawls_per_min: number
  ipfs_uploads: number
  ticks_processed: number
  uptime_seconds: number
  status: string
  last_tick: string
}

interface Genome {
  id: string
  fitness: number
  error_reward: number
  age: number
  weights: number[]
}

interface DataSource {
  name: string
  url: string
  type: string
  active: boolean
  error_rate: number
  yield: number
  fetch_count: number
}

interface APIKeyInfo {
  key: string
  owner: string
  calls: number
  revenue: number
  rate_limit: number
  active: boolean
}

function formatUptime(s: number): string {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0) return `${h}h ${m}m ${sec}s`
  if (m > 0) return `${m}m ${sec}s`
  return `${sec}s`
}

export default function OverAgentDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [population, setPopulation] = useState<Genome[]>([])
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [apiKeys, setApiKeys] = useState<APIKeyInfo[]>([])
  const [fitnessHistory, setFitnessHistory] = useState<{ gen: number; best: number; avg: number; div: number }[]>([])
  const [online, setOnline] = useState(false)
  const [newKeyOwner, setNewKeyOwner] = useState('')

  const fetchAll = useCallback(async () => {
    try {
      const [mRes, pRes, dRes, kRes] = await Promise.all([
        fetch(`${API}/api/overagent`),
        fetch(`${API}/api/overagent/population`),
        fetch(`${API}/api/overagent/datasources`),
        fetch(`${API}/api/overagent/keys`),
      ])
      if (mRes.ok) {
        const m: Metrics = await mRes.json()
        setMetrics(m)
        setOnline(m.status === 'running')
        setFitnessHistory(prev => {
          const next = [...prev, { gen: m.generation, best: m.best_fitness, avg: m.avg_fitness, div: m.diversity }]
          return next.slice(-120)
        })
      }
      if (pRes.ok) {
        const p = await pRes.json()
        setPopulation(p.population || [])
      }
      if (dRes.ok) {
        const d = await dRes.json()
        setDataSources(d.sources || [])
      }
      if (kRes.ok) {
        const k = await kRes.json()
        setApiKeys(k.keys || [])
      }
    } catch {
      setOnline(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const iv = setInterval(fetchAll, 2000)
    return () => clearInterval(iv)
  }, [fetchAll])

  const issueKey = async () => {
    if (!newKeyOwner.trim()) return
    await fetch(`${API}/api/overagent/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner: newKeyOwner, rate_limit: 100 }),
    })
    setNewKeyOwner('')
    fetchAll()
  }

  const m = metrics

  return (
    <div className="min-h-screen bg-[#060612] text-white pt-16 pb-12 px-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 border border-orange-500/30 flex items-center justify-center">
              <Dna className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold">OverAgent</h1>
              <p className="text-xs text-gray-500">Autonomous GA+RL / Error-is-Reward / 1s tick</p>
            </div>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${online ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            {online ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {online ? 'AUTONOMOUS' : 'OFFLINE'}
          </div>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          {[
            { label: 'Generation', value: m?.generation ?? 0, icon: Dna, color: 'orange' },
            { label: 'Best Fitness', value: (m?.best_fitness ?? 0).toFixed(3), icon: Zap, color: 'yellow' },
            { label: 'Avg Fitness', value: (m?.avg_fitness ?? 0).toFixed(3), icon: Activity, color: 'cyan' },
            { label: 'Diversity', value: (m?.diversity ?? 0).toFixed(2), icon: Brain, color: 'purple' },
            { label: 'Memory', value: m?.memory_size ?? 0, icon: HardDrive, color: 'blue' },
            { label: 'Errors Rewarded', value: m?.errors_rewarded ?? 0, icon: AlertTriangle, color: 'red' },
            { label: 'Data Sources', value: m?.data_sources_active ?? 0, icon: Database, color: 'green' },
            { label: 'API Keys', value: m?.total_api_keys ?? 0, icon: Key, color: 'amber' },
            { label: 'Revenue', value: `$${(m?.total_revenue ?? 0).toFixed(4)}`, icon: DollarSign, color: 'emerald' },
            { label: 'IPFS Uploads', value: m?.ipfs_uploads ?? 0, icon: Globe, color: 'indigo' },
            { label: 'Ticks', value: m?.ticks_processed ?? 0, icon: Clock, color: 'sky' },
            { label: 'Uptime', value: formatUptime(m?.uptime_seconds ?? 0), icon: Activity, color: 'teal' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white/[0.02] rounded-xl border border-white/5 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Icon className={`w-3.5 h-3.5 text-${color}-400`} />
                <span className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</span>
              </div>
              <div className="text-lg font-bold font-mono">{value}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Fitness History Chart */}
          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-4">
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              Fitness Evolution
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={fitnessHistory}>
                <XAxis dataKey="gen" tick={{ fill: '#666', fontSize: 10 }} />
                <YAxis tick={{ fill: '#666', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 8, fontSize: 11 }} />
                <Line type="monotone" dataKey="best" stroke="#f59e0b" strokeWidth={2} dot={false} name="Best" />
                <Line type="monotone" dataKey="avg" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="Avg" />
                <Line type="monotone" dataKey="div" stroke="#a855f7" strokeWidth={1} dot={false} name="Diversity" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* GA Population Scatter */}
          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-4">
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Dna className="w-4 h-4 text-orange-400" />
              Population ({population.length} genomes)
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <ScatterChart>
                <XAxis dataKey="age" name="Age" tick={{ fill: '#666', fontSize: 10 }} />
                <YAxis dataKey="fitness" name="Fitness" tick={{ fill: '#666', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 8, fontSize: 11 }}
                  formatter={(v: number) => v.toFixed(4)} />
                <Scatter data={population}>
                  {population.map((g, i) => (
                    <Cell key={i} fill={g.fitness > (m?.avg_fitness ?? 0) ? '#f59e0b' : '#666'} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Data Sources */}
          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-4">
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Database className="w-4 h-4 text-green-400" />
              Data Sources (self-adjusting)
            </h2>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {dataSources.map(ds => (
                <div key={ds.name} className={`flex items-center justify-between p-2.5 rounded-lg border ${ds.active ? 'bg-emerald-500/5 border-emerald-500/10' : 'bg-red-500/5 border-red-500/10 opacity-60'}`}>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${ds.active ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
                    <div>
                      <div className="text-xs font-medium">{ds.name}</div>
                      <div className="text-[10px] text-gray-500">{ds.type} | fetches: {ds.fetch_count}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px]">
                      <span className="text-emerald-400">yield: {ds.yield.toFixed(2)}</span>
                      {' / '}
                      <span className="text-red-400">err: {ds.error_rate.toFixed(2)}</span>
                    </div>
                    <div className="w-24 h-1.5 bg-white/5 rounded-full mt-1 overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full" style={{ width: `${Math.min(ds.yield * 100, 100)}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* API Keys + Issue */}
          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-4">
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Key className="w-4 h-4 text-amber-400" />
              API Keys ({apiKeys.length})
            </h2>
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={newKeyOwner}
                onChange={e => setNewKeyOwner(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && issueKey()}
                placeholder="Owner name..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-orange-500/50"
              />
              <button onClick={issueKey} className="px-3 py-1.5 bg-orange-500/20 border border-orange-500/30 rounded-lg text-xs text-orange-400 hover:bg-orange-500/30 transition-colors">
                Issue Key
              </button>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {apiKeys.map(ak => (
                <div key={ak.key} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <div className="text-xs font-mono">{ak.key.slice(0, 14)}...{ak.key.slice(-4)}</div>
                    <div className="text-[10px] text-gray-500">{ak.owner} | calls: {ak.calls} | limit: {ak.rate_limit}/min</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-emerald-400">${ak.revenue.toFixed(4)}</div>
                    <div className={`text-[10px] ${ak.active ? 'text-emerald-400' : 'text-red-400'}`}>{ak.active ? 'ACTIVE' : 'REVOKED'}</div>
                  </div>
                </div>
              ))}
              {apiKeys.length === 0 && (
                <div className="text-center text-gray-600 text-xs py-4">No API keys issued yet</div>
              )}
            </div>
          </div>
        </div>

        {/* Genome Weight Heatmap (top 5) */}
        <div className="bg-white/[0.02] rounded-xl border border-white/5 p-4">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            Top Genomes — Weight Distribution
          </h2>
          <div className="space-y-2">
            {population.slice(0, 5).map((g, gi) => (
              <div key={g.id} className="flex items-center gap-2">
                <span className="text-[10px] text-gray-500 w-20 shrink-0 font-mono">
                  {g.id.slice(0, 8)} f={g.fitness.toFixed(2)}
                </span>
                <div className="flex-1 flex gap-px h-4">
                  {g.weights.slice(0, 64).map((w, wi) => {
                    const intensity = Math.min(Math.abs(w), 2) / 2
                    const color = w > 0
                      ? `rgba(249, 115, 22, ${intensity})`
                      : `rgba(59, 130, 246, ${intensity})`
                    return <div key={wi} className="flex-1 rounded-sm" style={{ backgroundColor: color }} />
                  })}
                </div>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-500">
            <span className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-blue-500/60" /> Negative</span>
            <span className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-white/10" /> Zero</span>
            <span className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-orange-500/60" /> Positive</span>
          </div>
        </div>
      </div>
    </div>
  )
}
