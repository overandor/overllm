import React, { useState, useEffect, useCallback } from 'react'
import {
  TrendingUp, TrendingDown, Activity, Clock, Zap, BarChart3, Settings,
  RefreshCw, Play, Square, AlertTriangle, CheckCircle, XCircle, Shield,
  Hash, FileText, Server, Cpu
} from 'lucide-react'

interface Prediction {
  prediction_id: string
  symbol: string
  created_at: string
  horizon_seconds: number
  side: string
  confidence: number
  reference_price: number
  spread_bps: number
  features_hash: string
  model_hash: string
  policy_hash: string
  reason: string
  status: string
  receipt_hash?: string
}

interface OutcomeRecord {
  prediction_id: string
  judged_at: string
  exit_reference_price: number
  gross_return_bps: number
  estimated_fee_bps: number
  estimated_slippage_bps: number
  net_return_bps: number
  outcome: string
  reward: number
  model_update_applied: boolean
  receipt_hash?: string
}

interface JudgedRow {
  prediction: Prediction
  outcome: OutcomeRecord
}

interface PerformanceStats {
  total: number
  wins: number
  losses: number
  accuracy: number
  total_net_bps: number
  avg_net_bps: number
  avg_reward: number
}

interface CalibrationBin {
  range: string
  predicted: number
  actual: number
  count: number
}

export default function GateioTradingDashboard() {
  const [apiEndpoint, setApiEndpoint] = useState('http://localhost:8001')
  const [isConnected, setIsConnected] = useState(false)
  const [engineRunning, setEngineRunning] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(5000)

  const [pending, setPending] = useState<Prediction[]>([])
  const [history, setHistory] = useState<JudgedRow[]>([])
  const [stats, setStats] = useState<PerformanceStats | null>(null)
  const [accuracyBySymbol, setAccuracyBySymbol] = useState<Record<string, any>>({})
  const [calibration, setCalibration] = useState<{ bins: CalibrationBin[]; reliability: number }>({ bins: [], reliability: 0 })
  const [receipts, setReceipts] = useState<any[]>([])
  const [status, setStatus] = useState<any>({})
  const [truthLabels, setTruthLabels] = useState<Record<string, string>>({})
  const [lastError, setLastError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const [statusRes, pendingRes, historyRes, perfRes, receiptsRes] = await Promise.all([
        fetch(`${apiEndpoint}/api/status`),
        fetch(`${apiEndpoint}/api/predictions/pending`),
        fetch(`${apiEndpoint}/api/predictions/history?limit=100`),
        fetch(`${apiEndpoint}/api/performance`),
        fetch(`${apiEndpoint}/api/receipts?limit=100`),
      ])

      if (statusRes.ok) {
        const s = await statusRes.json()
        setStatus(s.alpha_engine || {})
        setTruthLabels(s.truth_labels || {})
        setEngineRunning(s.alpha_engine?.running || false)
        setIsConnected(true)
        setLastError(null)
      }

      if (pendingRes.ok) {
        const p = await pendingRes.json()
        setPending(p.predictions || [])
      }

      if (historyRes.ok) {
        const h = await historyRes.json()
        const judged = (h.predictions || []).map((pred: Prediction) => {
          // History endpoint returns predictions only; we need to enrich with outcomes.
          // For dashboard simplicity, we fetch receipts which contain outcome info.
          return { prediction: pred } as JudgedRow
        })
        setHistory(judged)
      }

      if (perfRes.ok) {
        const p = await perfRes.json()
        setStats(p.stats || null)
        setAccuracyBySymbol(p.accuracy_by_symbol || {})
        setCalibration(p.calibration || { bins: [], reliability: 0 })
      }

      if (receiptsRes.ok) {
        const r = await receiptsRes.json()
        setReceipts(r.receipts || [])
      }

      setLastUpdate(new Date())
    } catch (err: any) {
      setIsConnected(false)
      setLastError(err.message)
    }
  }, [apiEndpoint])

  const startEngine = async () => {
    try {
      const res = await fetch(`${apiEndpoint}/api/engine/start`, { method: 'POST' })
      if (res.ok) setEngineRunning(true)
    } catch (e) {
      setLastError('Failed to start engine')
    }
  }

  const stopEngine = async () => {
    try {
      const res = await fetch(`${apiEndpoint}/api/engine/stop`, { method: 'POST' })
      if (res.ok) setEngineRunning(false)
    } catch (e) {
      setLastError('Failed to stop engine')
    }
  }

  const judgePending = async () => {
    try {
      await fetch(`${apiEndpoint}/api/judge/pending`, { method: 'POST' })
      fetchAll()
    } catch (e) {
      setLastError('Judge call failed')
    }
  }

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(() => fetchAll(), refreshInterval)
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, fetchAll])

  const now = Date.now()

  const CountdownBadge = ({ pred }: { pred: Prediction }) => {
    const created = new Date(pred.created_at).getTime()
    const elapsedSec = Math.floor((now - created) / 1000)
    const remaining = Math.max(0, pred.horizon_seconds - elapsedSec)
    const pct = Math.min(100, (elapsedSec / pred.horizon_seconds) * 100)
    return (
      <div className="flex items-center gap-2 w-32">
        <div className="flex-1 h-2 bg-gray-700 rounded overflow-hidden">
          <div className="h-full bg-cyan-500 transition-all" style={{ width: `${pct}%` }} />
        </div>
        <span className="text-xs text-cyan-400 w-10 text-right">{remaining}s</span>
      </div>
    )
  }

  const sideColor = (side: string) => {
    if (side === 'LONG' || side === 'PREPARE_LONG') return 'text-emerald-400'
    if (side === 'SHORT' || side === 'PREPARE_SHORT') return 'text-red-400'
    return 'text-gray-400'
  }

  const outcomeBadge = (outcome: string) => {
    if (outcome === 'WIN' || outcome === 'PREPARE_WIN') return <span className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-400">{outcome}</span>
    if (outcome === 'LOSS' || outcome === 'PREPARE_LOSS') return <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400">{outcome}</span>
    return <span className="text-xs px-2 py-1 rounded bg-gray-500/20 text-gray-400">{outcome}</span>
  }

  const totalJudged = receipts.length
  const winCount = receipts.filter((r: any) => r.outcome === 'WIN' || r.outcome === 'PREPARE_WIN').length
  const accuracyPct = totalJudged ? (winCount / totalJudged) * 100 : 0

  return (
    <div className="space-y-6 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">OverLLM Gate.io Alpha Engine</h2>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'}`} />
              {isConnected ? 'Connected' : 'Disconnected'}
              {engineRunning && <span className="text-emerald-400">• Engine Running</span>}
              {lastUpdate && <span>• {lastUpdate.toLocaleTimeString()}</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowSettings(!showSettings)} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
          <button onClick={fetchAll} className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
          <button onClick={judgePending} className="px-3 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 text-sm font-medium hover:bg-cyan-500/30 transition-colors">
            Judge Now
          </button>
          <button
            onClick={engineRunning ? stopEngine : startEngine}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              engineRunning ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
            }`}
          >
            {engineRunning ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {engineRunning ? 'Stop' : 'Start'}
          </button>
        </div>
      </div>

      {/* Truth Labels */}
      <div className="neu-card p-4 border border-yellow-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="w-4 h-4 text-yellow-400" />
          <h3 className="text-sm font-semibold text-yellow-400">Truth Labels</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
          {Object.entries(truthLabels).map(([k, v]) => (
            <div key={k} className="flex items-center gap-2">
              <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}:</span>
              <span className={v === 'disabled' || v.includes('experimental') || v.includes('demo') ? 'text-yellow-400' : 'text-emerald-400'}>{String(v)}</span>
            </div>
          ))}
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Public paper prediction engine. No live trades. All predictions and outcomes are stored with receipts.
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="neu-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-gray-400" />
            <h3 className="text-xs text-gray-400">Pending Predictions</h3>
          </div>
          <div className="text-2xl font-bold text-white">{pending.length}</div>
        </div>
        <div className="neu-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-gray-400" />
            <h3 className="text-xs text-gray-400">Judged Predictions</h3>
          </div>
          <div className="text-2xl font-bold text-white">{totalJudged}</div>
        </div>
        <div className="neu-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-gray-400" />
            <h3 className="text-xs text-gray-400">Accuracy</h3>
          </div>
          <div className="text-2xl font-bold text-cyan-400">{accuracyPct.toFixed(1)}%</div>
          <div className="text-xs text-gray-500">{winCount} wins / {totalJudged - winCount} losses</div>
        </div>
        <div className="neu-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-gray-400" />
            <h3 className="text-xs text-gray-400">Total Net bps</h3>
          </div>
          <div className={`text-2xl font-bold ${(stats?.total_net_bps || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {(stats?.total_net_bps || 0).toFixed(1)}
          </div>
        </div>
      </div>

      {/* Pending Countdowns */}
      <div className="neu-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Pending 3-Minute Countdowns</h3>
          <span className="text-xs text-gray-400">{pending.length} waiting</span>
        </div>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {pending.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Clock className="w-12 h-12 mx-auto mb-2 text-gray-600" />
              <p className="text-sm">No pending predictions</p>
            </div>
          ) : (
            pending.map((pred) => (
              <div key={pred.prediction_id} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <div className={`font-semibold text-sm w-20 ${sideColor(pred.side)}`}>{pred.side}</div>
                <div className="text-sm text-white w-24">{pred.symbol}</div>
                <div className="text-xs text-gray-400 w-32">${pred.reference_price.toFixed(2)}</div>
                <div className="text-xs text-gray-400">{(pred.confidence * 100).toFixed(0)}% conf</div>
                <div className="flex-1" />
                <CountdownBadge pred={pred} />
              </div>
            ))
          )}
        </div>
      </div>

      {/* Judged History */}
      <div className="neu-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Judged Predictions</h3>
          <span className="text-xs text-gray-400">Last 100</span>
        </div>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {receipts.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <CheckCircle className="w-12 h-12 mx-auto mb-2 text-gray-600" />
              <p className="text-sm">No judged predictions yet</p>
            </div>
          ) : (
            receipts.slice(0, 100).map((r: any) => (
              <div key={r.prediction_id} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <div className={`font-semibold text-sm w-20 ${sideColor(r.side)}`}>{r.side}</div>
                <div className="text-sm text-white w-24">{r.symbol || '—'}</div>
                <div className="text-xs text-gray-400 w-28">{r.outcome}</div>
                <div className={`text-sm font-semibold w-24 ${r.net_return_bps >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {r.net_return_bps?.toFixed(1)} bps
                </div>
                <div className="text-xs text-gray-500 truncate max-w-xs">{r.prediction_id}</div>
                <div className="flex-1" />
                {outcomeBadge(r.outcome)}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Accuracy by Symbol */}
      <div className="neu-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Accuracy by Symbol</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(accuracyBySymbol).map(([sym, data]: [string, any]) => (
            <div key={sym} className="p-3 bg-white/5 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-white text-sm">{sym}</span>
                <span className="text-xs text-cyan-400">{((data.accuracy || 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="text-xs text-gray-400">Total: {data.total || 0} | Avg Net: {(data.avg_net_bps || 0).toFixed(1)} bps</div>
            </div>
          ))}
        </div>
      </div>

      {/* Calibration */}
      <div className="neu-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Confidence Calibration</h3>
          <span className="text-xs text-gray-400">Reliability: {(calibration.reliability * 100).toFixed(1)}%</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          {calibration.bins.map((bin: CalibrationBin, i: number) => (
            <div key={i} className="p-3 bg-white/5 rounded-lg text-center">
              <div className="text-xs text-gray-400 mb-1">{bin.range}</div>
              <div className="text-sm font-semibold text-white">{(bin.actual * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-500">n={bin.count}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Receipt Explorer */}
      <div className="neu-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Receipt Explorer</h3>
          <span className="text-xs text-gray-400">{receipts.length} receipts</span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {receipts.slice(0, 20).map((r: any) => (
            <div key={r.prediction_id} className="flex items-center gap-2 p-2 bg-white/5 rounded text-xs">
              <Hash className="w-3 h-3 text-gray-500" />
              <span className="text-gray-400 truncate max-w-xs">{r.prediction_receipt_hash || '—'}</span>
              <span className="text-gray-600">→</span>
              <span className="text-gray-400 truncate max-w-xs">{r.outcome_receipt_hash || '—'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="neu-card p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">Connection Settings</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">API Endpoint</label>
              <input
                type="text"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500/50"
                placeholder="http://localhost:8001"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Refresh Interval (ms)</label>
              <input
                type="number"
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500/50"
                min="1000"
                step="1000"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 rounded bg-white/5 border-white/10 text-emerald-500 focus:ring-emerald-500/50"
            />
            <label htmlFor="autoRefresh" className="text-sm text-gray-300">Auto-refresh data</label>
          </div>
        </div>
      )}

      {/* Model / Runtime Truth */}
      <div className="neu-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Cpu className="w-4 h-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-300">Model & Runtime Truth</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-400">
          <div>Policy Hash: <span className="text-gray-300 font-mono truncate">{status.policy_hash?.slice(0, 24)}...</span></div>
          <div>Epsilon: <span className="text-gray-300">{status.policy_epsilon?.toFixed(4)}</span></div>
          <div>Session Net bps: <span className="text-gray-300">{status.session_net_bps?.toFixed(1)}</span></div>
        </div>
      </div>

      {lastError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
          <AlertTriangle className="w-4 h-4 inline mr-1" />
          {lastError}
        </div>
      )}
    </div>
  )
}