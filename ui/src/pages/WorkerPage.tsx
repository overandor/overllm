import React, { useState, useEffect, useRef, useCallback } from 'react'
import { WorkerPool, VerificationOutcome } from '../worker/worker-pool'
import { Cpu, Shield, Zap, Receipt, AlertTriangle, Play, Square, Activity, CheckCircle, XCircle, Database, Radio } from 'lucide-react'

interface WorkerSession {
  id: string
  is_active: boolean
  total_jobs: number
  total_compute_sec: number
  total_credits: number
  capabilities: string[]
}

interface LogEntry {
  timestamp: string
  type: 'info' | 'success' | 'error' | 'warn'
  message: string
}

export default function WorkerPage() {
  const poolRef = useRef<WorkerPool | null>(null)
  const [hasConsent, setHasConsent] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [workers, setWorkers] = useState<WorkerSession[]>([])
  const [poolStats, setPoolStats] = useState({
    total_workers: 0,
    active_workers: 0,
    total_jobs: 0,
    total_compute_sec: 0,
    total_credits: 0,
  })
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [currentTask, setCurrentTask] = useState<string | null>(null)
  const [lastOutcome, setLastOutcome] = useState<VerificationOutcome | null>(null)
  const [coordinatorUrl, setCoordinatorUrl] = useState('ws://localhost:8777')
  const [isConnected, setIsConnected] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)

  const addLog = useCallback((type: LogEntry['type'], message: string) => {
    setLogs(prev => [...prev, { timestamp: new Date().toLocaleTimeString(), type, message }].slice(-200))
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Stats refresh interval
  useEffect(() => {
    if (!isRunning) return
    const interval = setInterval(() => {
      const pool = poolRef.current
      if (pool) {
        setPoolStats(pool.getPoolStats())
        setWorkers(pool.getPoolStats().workers)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [isRunning])

  const startWorker = async () => {
    if (!poolRef.current) {
      poolRef.current = new WorkerPool(2, 2)
    }
    const pool = poolRef.current
    try {
      addLog('info', 'Initializing WASM runtime...')
      const workerId = await pool.spawnWorker({ cpu_limit_pct: 30, memory_limit_mb: 256 })
      addLog('success', `Worker ${workerId.slice(0, 16)}... started`)
      pool.startHeartbeat(5000)
      setIsRunning(true)
      setPoolStats(pool.getPoolStats())
    } catch (e) {
      addLog('error', `Failed to start worker: ${e}`)
    }
  }

  const stopWorker = () => {
    const pool = poolRef.current
    if (!pool) return
    for (const w of pool.getPoolStats().workers) {
      pool.stopWorker(w.id)
      addLog('info', `Stopping worker ${w.id.slice(0, 16)}...`)
    }
    setTimeout(() => {
      pool.terminateAll()
      poolRef.current = null
      setIsRunning(false)
      setWorkers([])
      setPoolStats({ total_workers: 0, active_workers: 0, total_jobs: 0, total_compute_sec: 0, total_credits: 0 })
      addLog('info', 'All workers terminated')
    }, 500)
  }

  const connectCoordinator = async () => {
    const pool = poolRef.current
    if (!pool || !isRunning) {
      addLog('warn', 'Start a worker first')
      return
    }
    try {
      addLog('info', `Connecting to coordinator at ${coordinatorUrl}...`)
      pool.setCoordinatorCallback((msg: any) => {
        if (msg.type === 'coordinator-outcome') {
          const outcome = msg.outcome as VerificationOutcome
          setLastOutcome(outcome)
          if (outcome.status === 'consensus') {
            addLog('success', `Coordinator job consensus ✓ hash=${outcome.consensus_hash?.slice(0, 16)}`)
          } else if (outcome.status === 'mismatch') {
            addLog('error', `Coordinator job mismatch! workers=${outcome.mismatched_workers?.join(', ').slice(0, 40)}`)
          } else {
            addLog('warn', `Coordinator job ${outcome.status}`)
          }
        } else if (msg.type === 'coordinator-error') {
          addLog('error', `Coordinator error: ${msg.error}`)
        }
      })
      await pool.connectCoordinator(coordinatorUrl)
      setIsConnected(true)
      addLog('success', 'Connected to coordinator. Jobs will flow automatically.')
    } catch (e) {
      addLog('error', `Coordinator connection failed: ${e}`)
    }
  }

  const disconnectCoordinator = () => {
    const pool = poolRef.current
    if (pool) {
      pool.disconnectCoordinator()
    }
    setIsConnected(false)
    addLog('info', 'Disconnected from coordinator')
  }

  const runLocalTest = async () => {
    const pool = poolRef.current
    if (!pool || !isRunning) {
      addLog('warn', 'Start a worker first')
      return
    }
    // Deterministic test: same job_id on two workers must produce same receipt hash
    const jobId = `test-${Date.now()}`
    const payload = { items: ['alpha', 'beta', 'gamma', 'delta'] }
    addLog('info', `Running local determinism test: ${jobId.slice(0, 12)}`)
    setCurrentTask(`determinism-test (${jobId.slice(0, 12)})`)

    try {
      const outcome = await pool.assignTask(jobId, 'hash-batch', payload, {
        max_duration_sec: 3,
        replica_count: 2,
        timeout_ms: 15000,
      })
      setLastOutcome(outcome)
      setCurrentTask(null)

      if (outcome.status === 'consensus') {
        addLog('success', `Determinism test PASSED ✓ hash=${outcome.consensus_hash?.slice(0, 16)}`)
      } else {
        addLog('error', `Determinism test FAILED: ${outcome.status}`)
      }
    } catch (e) {
      addLog('error', `Local test failed: ${e}`)
      setCurrentTask(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#060612] text-gray-300 pt-20 px-6 pb-12">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">OverLLM Worker</h1>
          </div>
          <p className="text-sm text-gray-500">
            Browser-native deterministic compute. Explicit consent required. No hidden mining.
          </p>
        </div>

        {/* Consent Card */}
        {!hasConsent && (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-8">
            <div className="flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-yellow-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">Before you start</h3>
                <ul className="space-y-1.5 text-sm text-gray-400 mb-4">
                  <li>This page runs WebAssembly compute inside your browser.</li>
                  <li>CPU is limited to 30% by default. You can stop anytime.</li>
                  <li>Every completed task generates a cryptographically signed receipt.</li>
                  <li>No personal data is collected. Only deterministic compute results are transmitted.</li>
                  <li>You must explicitly click Start. Nothing runs automatically.</li>
                </ul>
                <button
                  onClick={() => setHasConsent(true)}
                  className="px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 rounded-lg text-sm font-medium transition-all"
                >
                  I understand — enable worker
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Controls */}
        {hasConsent && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Control Panel */}
            <div className="lg:col-span-1 space-y-4">
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" /> Control
                </h3>
                <div className="flex gap-2 mb-4">
                  {!isRunning ? (
                    <button
                      onClick={startWorker}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 rounded-lg text-sm font-medium transition-all"
                    >
                      <Play className="w-4 h-4" /> Start Worker
                    </button>
                  ) : (
                    <button
                      onClick={stopWorker}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-300 rounded-lg text-sm font-medium transition-all"
                    >
                      <Square className="w-4 h-4" /> Stop Worker
                    </button>
                  )}
                </div>

                {isRunning && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Coordinator</p>
                    <input
                      type="text"
                      value={coordinatorUrl}
                      onChange={e => setCoordinatorUrl(e.target.value)}
                      className="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-xs text-gray-300 focus:outline-none focus:border-emerald-500/50"
                      placeholder="ws://localhost:8777"
                    />
                    {!isConnected ? (
                      <button
                        onClick={connectCoordinator}
                        className="w-full flex items-center gap-2 px-3 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 rounded-lg text-xs text-emerald-300 transition-all"
                      >
                        <Radio className="w-3.5 h-3.5" />
                        Connect Coordinator
                      </button>
                    ) : (
                      <button
                        onClick={disconnectCoordinator}
                        className="w-full flex items-center gap-2 px-3 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 rounded-lg text-xs text-red-300 transition-all"
                      >
                        <Square className="w-3.5 h-3.5" />
                        Disconnect
                      </button>
                    )}
                    <button
                      onClick={runLocalTest}
                      disabled={!!currentTask}
                      className="w-full flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg text-xs text-gray-300 transition-all disabled:opacity-40"
                    >
                      <Zap className="w-3.5 h-3.5 text-yellow-500" />
                      Local determinism test
                    </button>
                  </div>
                )}
              </div>

              {/* Pool Stats */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-emerald-400" /> Pool Stats
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Workers</span><span className="text-white">{poolStats.active_workers} / {poolStats.total_workers}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Jobs Done</span><span className="text-white">{poolStats.total_jobs}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Compute</span><span className="text-white">{poolStats.total_compute_sec}s</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Credits</span><span className="text-emerald-400">{poolStats.total_credits}</span></div>
                </div>
              </div>
            </div>

            {/* Main Display */}
            <div className="lg:col-span-2 space-y-4">
              {/* Active Task */}
              {currentTask && (
                <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-2xl p-4 flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <div>
                    <p className="text-xs text-cyan-400 font-medium">ACTIVE TASK</p>
                    <p className="text-sm text-white">{currentTask}</p>
                  </div>
                </div>
              )}

              {/* Last Outcome */}
              {lastOutcome && (
                <div className={`border rounded-2xl p-4 ${
                  lastOutcome.status === 'consensus'
                    ? 'bg-emerald-500/10 border-emerald-500/20'
                    : lastOutcome.status === 'mismatch'
                    ? 'bg-red-500/10 border-red-500/20'
                    : 'bg-yellow-500/10 border-yellow-500/20'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {lastOutcome.status === 'consensus' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className={`text-sm font-semibold ${
                      lastOutcome.status === 'consensus' ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {lastOutcome.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 space-y-1">
                    <p>Job: {lastOutcome.job_id.slice(0, 20)}</p>
                    {lastOutcome.consensus_hash && (
                      <p>Consensus hash: {lastOutcome.consensus_hash.slice(0, 32)}</p>
                    )}
                    {lastOutcome.mismatched_workers && (
                      <p>Mismatched: {lastOutcome.mismatched_workers.join(', ').slice(0, 60)}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Workers Table */}
              {workers.length > 0 && (
                <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                  <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-cyan-400" /> Workers
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-500 border-b border-white/5">
                          <th className="text-left py-2 pr-4">ID</th>
                          <th className="text-left py-2 pr-4">Status</th>
                          <th className="text-right py-2 pr-4">Jobs</th>
                          <th className="text-right py-2 pr-4">Compute</th>
                          <th className="text-right py-2">Credits</th>
                        </tr>
                      </thead>
                      <tbody>
                        {workers.map(w => (
                          <tr key={w.id} className="border-b border-white/5 text-gray-300">
                            <td className="py-2 pr-4 font-mono text-xs">{w.id.slice(0, 20)}...</td>
                            <td className="py-2 pr-4">
                              <span className={`inline-flex items-center gap-1 text-xs ${w.is_active ? 'text-emerald-400' : 'text-gray-500'}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${w.is_active ? 'bg-emerald-400' : 'bg-gray-600'}`} />
                                {w.is_active ? 'active' : 'idle'}
                              </span>
                            </td>
                            <td className="py-2 pr-4 text-right">{w.total_jobs}</td>
                            <td className="py-2 pr-4 text-right">{w.total_compute_sec}s</td>
                            <td className="py-2 text-right text-emerald-400">{w.total_credits}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Logs */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <Receipt className="w-4 h-4 text-cyan-400" /> Event Log
                </h3>
                <div className="h-64 overflow-y-auto font-mono text-xs space-y-1 bg-black/20 rounded-lg p-3">
                  {logs.length === 0 && (
                    <p className="text-gray-600 italic">No events yet. Start a worker to begin.</p>
                  )}
                  {logs.map((log, i) => (
                    <div key={i} className="flex gap-2">
                      <span className="text-gray-600 flex-shrink-0">{log.timestamp}</span>
                      <span className={`flex-shrink-0 ${
                        log.type === 'success' ? 'text-emerald-400' :
                        log.type === 'error' ? 'text-red-400' :
                        log.type === 'warn' ? 'text-yellow-400' :
                        'text-cyan-400'
                      }`}>[{log.type}]</span>
                      <span className="text-gray-300 break-all">{log.message}</span>
                    </div>
                  ))}
                  <div ref={logEndRef} />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
