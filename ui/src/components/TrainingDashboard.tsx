import React, { useState, useEffect } from 'react'
import { Activity, Zap, Clock, Database, Cpu, TrendingDown, CheckCircle, Loader } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

interface TrainingMetrics {
  status: string
  current_epoch: number
  total_epochs: number
  dpo_loss: number
  preference_pairs: number
  vocab_size: number
  model_params: { d_model: number; n_heads: number; n_layers: number; d_ff: number }
  elapsed_s: number
  epoch_history: { epoch: number; loss: number; time_s: number }[]
  updated_at: number
}

const API_URL = ''

export default function TrainingDashboard() {
  const [metrics, setMetrics] = useState<TrainingMetrics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState(Date.now())

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch(`${API_URL}/api/metrics`)
        const data = await res.json()
        if (data.status !== 'no_data') {
          setMetrics(data)
          setError(null)
        }
      } catch (e) {
        setError('Unable to reach metrics endpoint')
      }
      setLastRefresh(Date.now())
    }
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 3000)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (s: number) => {
    if (s < 60) return `${s.toFixed(0)}s`
    if (s < 3600) return `${Math.floor(s / 60)}m ${Math.floor(s % 60)}s`
    return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
  }

  const isLive = metrics && metrics.status === 'training'
  const isComplete = metrics && metrics.status === 'complete'

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Cpu className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-300 to-cyan-300 bg-clip-text text-transparent">
                OverLLM Training
              </h1>
              <p className="text-sm text-emerald-400/60">DPO • Punishment-as-Reward • Live KPIs</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isLive && (
              <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-sm">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                LIVE
              </span>
            )}
            {isComplete && (
              <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-sm">
                <CheckCircle className="w-4 h-4" />
                COMPLETE
              </span>
            )}
            {!metrics && (
              <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-500/20 border border-gray-500/40 text-gray-400 text-sm">
                <Loader className="w-4 h-4 animate-spin" />
                WAITING
              </span>
            )}
          </div>
        </div>

        {error && !metrics && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-300 text-sm">{error}</div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard
            icon={Activity}
            label="Epoch"
            value={metrics ? `${metrics.current_epoch}/${metrics.total_epochs}` : '--'}
            sub={metrics ? `${((metrics.current_epoch / metrics.total_epochs) * 100).toFixed(0)}% done` : ''}
            gradient="from-emerald-500 to-green-500"
          />
          <KPICard
            icon={TrendingDown}
            label="DPO Loss"
            value={metrics ? metrics.dpo_loss.toFixed(4) : '--'}
            sub={metrics?.epoch_history?.length > 1
              ? `Δ ${(metrics.epoch_history[metrics.epoch_history.length - 1].loss - metrics.epoch_history[0].loss).toFixed(4)}`
              : ''}
            gradient="from-orange-500 to-amber-500"
          />
          <KPICard
            icon={Database}
            label="Training Pairs"
            value={metrics ? metrics.preference_pairs.toLocaleString() : '--'}
            sub={metrics ? `${metrics.vocab_size.toLocaleString()} vocab` : ''}
            gradient="from-violet-500 to-purple-500"
          />
          <KPICard
            icon={Clock}
            label="Elapsed"
            value={metrics ? formatTime(metrics.elapsed_s) : '--'}
            sub={metrics?.epoch_history?.length
              ? `~${formatTime(metrics.epoch_history[metrics.epoch_history.length - 1].time_s)}/epoch`
              : ''}
            gradient="from-cyan-500 to-blue-500"
          />
        </div>

        {/* Loss Chart */}
        {metrics?.epoch_history && metrics.epoch_history.length > 0 && (
          <div className="bg-[#111128] rounded-2xl border border-emerald-500/20 p-6">
            <h2 className="text-lg font-semibold text-emerald-200 mb-4">DPO Loss Curve</h2>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={metrics.epoch_history}>
                <defs>
                  <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3f" />
                <XAxis dataKey="epoch" stroke="#4ade80" fontSize={12} label={{ value: 'Epoch', position: 'insideBottom', offset: -5, fill: '#4ade8080' }} />
                <YAxis stroke="#4ade80" fontSize={12} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{ background: '#111128', border: '1px solid #10b98140', borderRadius: '12px' }}
                  labelStyle={{ color: '#4ade80' }}
                  itemStyle={{ color: '#a7f3d0' }}
                />
                <Area type="monotone" dataKey="loss" stroke="#10b981" strokeWidth={2} fill="url(#lossGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Epoch Time + Model Architecture */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {metrics?.epoch_history && metrics.epoch_history.length > 0 && (
            <div className="bg-[#111128] rounded-2xl border border-cyan-500/20 p-6">
              <h2 className="text-lg font-semibold text-cyan-200 mb-4">Epoch Duration</h2>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={metrics.epoch_history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3f" />
                  <XAxis dataKey="epoch" stroke="#22d3ee" fontSize={12} />
                  <YAxis stroke="#22d3ee" fontSize={12} unit="s" />
                  <Tooltip
                    contentStyle={{ background: '#111128', border: '1px solid #22d3ee40', borderRadius: '12px' }}
                    labelStyle={{ color: '#22d3ee' }}
                  />
                  <Line type="monotone" dataKey="time_s" stroke="#22d3ee" strokeWidth={2} dot={{ r: 3, fill: '#22d3ee' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {metrics?.model_params && (
            <div className="bg-[#111128] rounded-2xl border border-violet-500/20 p-6">
              <h2 className="text-lg font-semibold text-violet-200 mb-4">Model Architecture</h2>
              <div className="grid grid-cols-2 gap-4">
                <ArchParam label="Embedding Dim" value={metrics.model_params.d_model} />
                <ArchParam label="Attention Heads" value={metrics.model_params.n_heads} />
                <ArchParam label="Transformer Layers" value={metrics.model_params.n_layers} />
                <ArchParam label="FFN Dim" value={metrics.model_params.d_ff} />
                <ArchParam label="Vocab Size" value={metrics.vocab_size} />
                <ArchParam label="Training Pairs" value={metrics.preference_pairs} />
              </div>
              <div className="mt-4 pt-4 border-t border-violet-500/20">
                <div className="text-xs text-violet-400/60">Training Method</div>
                <div className="text-sm text-violet-200 mt-1">Direct Preference Optimization (DPO)</div>
                <div className="text-xs text-violet-400/60 mt-2">Architecture</div>
                <div className="text-sm text-violet-200 mt-1">Custom NumPy Transformer → C++ Export</div>
              </div>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        {metrics && (
          <div className="bg-[#111128] rounded-2xl border border-emerald-500/20 p-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-emerald-300">Training Progress</span>
              <span className="text-emerald-400/70">{metrics.current_epoch}/{metrics.total_epochs} epochs</span>
            </div>
            <div className="h-3 bg-[#0a0a1a] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-1000"
                style={{ width: `${(metrics.current_epoch / metrics.total_epochs) * 100}%` }}
              />
            </div>
          </div>
        )}

        <div className="text-center text-xs text-gray-600 mt-8">
          OverLLM • Punishment-as-Reward DPO • Built from scratch in C++ / Go / Rust
        </div>
      </div>
    </div>
  )
}

function KPICard({ icon: Icon, label, value, sub, gradient }: {
  icon: React.ElementType; label: string; value: string; sub: string; gradient: string
}) {
  return (
    <div className="bg-[#111128] rounded-2xl border border-white/5 p-5 hover:border-white/10 transition-all">
      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-3 shadow-lg`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}

function ArchParam({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xs text-violet-400/60">{label}</div>
      <div className="text-lg font-semibold text-violet-200">{value.toLocaleString()}</div>
    </div>
  )
}
