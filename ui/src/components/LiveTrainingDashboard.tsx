import React, { useState, useEffect, useRef } from 'react'
import { Activity, Zap, Clock, Database, Cpu, TrendingDown, TrendingUp, Play, Pause, RefreshCw, Globe, Signal, BarChart3, Target, Award } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from 'recharts'

interface LiveKPIs {
  timestamp: number
  epoch: number
  total_epochs: number
  loss: number
  learning_rate: number
  samples_processed: number
  samples_per_second: float
  accuracy: number
  reward: number
  epsilon: number
  buffer_size: number
  gpu_memory: float
  cpu_usage: float
  memory_usage: float
  data_source: string
  prediction_quality: number
  convergence_rate: number
}

interface TrainingState {
  status: string
  epoch: number
  total_epochs: number
  samples_processed: number
  elapsed_time: number
  sampling_stats: {
    total_sources: number
    active_sources: number
    total_samples: number
    samples_by_source: Record<string, number>
  }
  epoch_history: Array<{
    epoch: number
    loss: number
    accuracy: number
    timestamp: number
  }>
}

const WS_URL = 'ws://localhost:8765'

export default function LiveTrainingDashboard() {
  const [kpis, setKpis] = useState<LiveKPIs | null>(null)
  const [state, setState] = useState<TrainingState | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isTraining, setIsTraining] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const kpiHistoryRef = useRef<LiveKPIs[]>([])

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'state') {
            setState(data.data)
            setIsTraining(data.data.status === 'training')
          } else if (data.type === 'kpis') {
            const newKPIs = data as LiveKPIs
            setKpis(newKPIs)
            
            // Keep history for charts (last 100 points)
            kpiHistoryRef.current = [...kpiHistoryRef.current.slice(-99), newKPIs]
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
        setConnected(false)
      }

      ws.onclose = () => {
        setConnected(false)
        console.log('WebSocket disconnected')
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000)
      }
    } catch (e) {
      setError('Failed to connect to WebSocket server')
      setConnected(false)
    }
  }

  const startTraining = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'start_training' }))
    }
  }

  const stopTraining = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'stop_training' }))
    }
  }

  const formatTime = (s: number) => {
    if (s < 60) return `${s.toFixed(0)}s`
    if (s < 3600) return `${Math.floor(s / 60)}m ${Math.floor(s % 60)}s`
    return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toFixed(0)
  }

  const kpiHistory = kpiHistoryRef.current

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Activity className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-emerald-300 to-cyan-300 bg-clip-text text-transparent">
                OverLLM Live Training
              </h1>
              <p className="text-sm text-emerald-400/60">Real-time Online Learning • 1-Second Sampling • Live KPIs</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm ${
              connected 
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' 
                : 'bg-red-500/20 border-red-500/40 text-red-300'
            }`}>
              <Signal className={`w-4 h-4 ${connected ? 'animate-pulse' : ''}`} />
              {connected ? 'CONNECTED' : 'DISCONNECTED'}
            </div>
            {isTraining && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-sm">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                TRAINING
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-300 text-sm flex items-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            {error}
          </div>
        )}

        {/* Control Buttons */}
        <div className="flex gap-3">
          <button
            onClick={startTraining}
            disabled={!connected || isTraining}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-all"
          >
            <Play className="w-4 h-4" />
            Start Training
          </button>
          <button
            onClick={stopTraining}
            disabled={!connected || !isTraining}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-all"
          >
            <Pause className="w-4 h-4" />
            Stop Training
          </button>
        </div>

        {/* Primary KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard
            icon={Activity}
            label="Epoch"
            value={kpis ? `${kpis.epoch}/${kpis.total_epochs}` : state ? `${state.epoch}/${state.total_epochs}` : '--'}
            sub={kpis ? `${((kpis.epoch / kpis.total_epochs) * 100).toFixed(1)}%` : ''}
            gradient="from-emerald-500 to-green-500"
          />
          <KPICard
            icon={TrendingDown}
            label="Loss"
            value={kpis ? kpis.loss.toFixed(4) : '--'}
            sub={kpis ? `LR: ${kpis.learning_rate.toFixed(6)}` : ''}
            gradient="from-orange-500 to-amber-500"
          />
          <KPICard
            icon={Target}
            label="Accuracy"
            value={kpis ? `${(kpis.accuracy * 100).toFixed(1)}%` : '--'}
            sub={kpis ? `Reward: ${kpis.reward.toFixed(2)}` : ''}
            gradient="from-violet-500 to-purple-500"
          />
          <KPICard
            icon={Database}
            label="Samples"
            value={kpis ? formatNumber(kpis.samples_processed) : state ? formatNumber(state.samples_processed) : '--'}
            sub={kpis ? `${kpis.samples_per_second.toFixed(1)}/s` : ''}
            gradient="from-cyan-500 to-blue-500"
          />
        </div>

        {/* Secondary KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard
            icon={Zap}
            label="Samples/Sec"
            value={kpis ? kpis.samples_per_second.toFixed(1) : '--'}
            sub={kpis ? `Buffer: ${formatNumber(kpis.buffer_size)}` : ''}
            gradient="from-yellow-500 to-orange-500"
          />
          <KPICard
            icon={Award}
            label="Epsilon"
            value={kpis ? kpis.epsilon.toFixed(4) : '--'}
            sub="Exploration Rate"
            gradient="from-pink-500 to-rose-500"
          />
          <KPICard
            icon={Cpu}
            label="CPU Usage"
            value={kpis ? `${kpis.cpu_usage.toFixed(1)}%` : '--'}
            sub={kpis ? `GPU: ${kpis.gpu_memory.toFixed(1)}GB` : ''}
            gradient="from-blue-500 to-indigo-500"
          />
          <KPICard
            icon={Clock}
            label="Elapsed"
            value={state ? formatTime(state.elapsed_time) : '--'}
            sub={kpis ? `Source: ${kpis.data_source}` : ''}
            gradient="from-teal-500 to-cyan-500"
          />
        </div>

        {/* Data Source Stats */}
        {state?.sampling_stats && (
          <div className="bg-[#111128] rounded-2xl border border-emerald-500/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-emerald-200 flex items-center gap-2">
                <Globe className="w-5 h-5" />
                Online Data Sources
              </h2>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-emerald-400">{state.sampling_stats.active_sources}/{state.sampling_stats.total_sources} Active</span>
                <span className="text-cyan-400">{formatNumber(state.sampling_stats.total_samples)} Samples</span>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {Object.entries(state.sampling_stats.samples_by_source).map(([source, count]) => (
                <div key={source} className="bg-[#0a0a1a] rounded-xl p-3 border border-white/5">
                  <div className="text-xs text-gray-400 capitalize">{source.replace('_', ' ')}</div>
                  <div className="text-lg font-semibold text-white">{formatNumber(count)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Real-time Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Loss Chart */}
          {kpiHistory.length > 0 && (
            <div className="bg-[#111128] rounded-2xl border border-emerald-500/20 p-6">
              <h2 className="text-lg font-semibold text-emerald-200 mb-4">Real-time Loss</h2>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={kpiHistory}>
                  <defs>
                    <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3f" />
                  <XAxis dataKey="epoch" stroke="#4ade80" fontSize={12} />
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

          {/* Accuracy Chart */}
          {kpiHistory.length > 0 && (
            <div className="bg-[#111128] rounded-2xl border border-violet-500/20 p-6">
              <h2 className="text-lg font-semibold text-violet-200 mb-4">Real-time Accuracy</h2>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={kpiHistory}>
                  <defs>
                    <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3f" />
                  <XAxis dataKey="epoch" stroke="#a78bfa" fontSize={12} />
                  <YAxis stroke="#a78bfa" fontSize={12} domain={[0, 1]} />
                  <Tooltip
                    contentStyle={{ background: '#111128', border: '1px solid #8b5cf640', borderRadius: '12px' }}
                    labelStyle={{ color: '#a78bfa' }}
                    itemStyle={{ color: '#c4b5fd' }}
                  />
                  <Area type="monotone" dataKey="accuracy" stroke="#8b5cf6" strokeWidth={2} fill="url(#accGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Samples per Second Chart */}
        {kpiHistory.length > 0 && (
          <div className="bg-[#111128] rounded-2xl border border-cyan-500/20 p-6">
            <h2 className="text-lg font-semibold text-cyan-200 mb-4">Training Throughput</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={kpiHistory.slice(-50)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3f" />
                <XAxis dataKey="epoch" stroke="#22d3ee" fontSize={12} />
                <YAxis stroke="#22d3ee" fontSize={12} />
                <Tooltip
                  contentStyle={{ background: '#111128', border: '1px solid #22d3ee40', borderRadius: '12px' }}
                  labelStyle={{ color: '#22d3ee' }}
                />
                <Bar dataKey="samples_per_second" fill="#22d3ee" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Progress Bar */}
        {kpis && (
          <div className="bg-[#111128] rounded-2xl border border-emerald-500/20 p-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-emerald-300">Training Progress</span>
              <span className="text-emerald-400/70">{kpis.epoch}/{kpis.total_epochs} epochs</span>
            </div>
            <div className="h-3 bg-[#0a0a1a] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full transition-all duration-300"
                style={{ width: `${(kpis.epoch / kpis.total_epochs) * 100}%` }}
              />
            </div>
          </div>
        )}

        <div className="text-center text-xs text-gray-600 mt-8">
          OverLLM Live Training • Real-time Online Learning • 1-Second Data Sampling
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