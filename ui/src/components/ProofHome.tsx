import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Brain, Cpu, Activity, Database, BarChart3, ArrowRight, Zap, Globe, Terminal, Layers, GitBranch, Shield } from 'lucide-react'

interface SystemStatus {
  status: string
  queue_size: number
  telemetry: number
}

interface TrainingStatus {
  status: string
  current_epoch?: number
  total_epochs?: number
  dpo_loss?: number
  preference_pairs?: number
  vocab_size?: number
}

export default function ProofHome() {
  const [system, setSystem] = useState<SystemStatus | null>(null)
  const [training, setTraining] = useState<TrainingStatus | null>(null)
  const [uptime, setUptime] = useState(0)

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [sRes, tRes] = await Promise.allSettled([
          fetch('/api/status').then(r => r.json()),
          fetch('/api/metrics').then(r => r.json()),
        ])
        if (sRes.status === 'fulfilled') setSystem(sRes.value)
        if (tRes.status === 'fulfilled' && tRes.value.status !== 'no_data') setTraining(tRes.value)
      } catch {}
    }
    fetchAll()
    const i = setInterval(fetchAll, 5000)
    const u = setInterval(() => setUptime(p => p + 1), 1000)
    return () => { clearInterval(i); clearInterval(u) }
  }, [])

  const formatUptime = (s: number) => {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = s % 60
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen bg-[#060612]">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-6 pt-16 pb-20">
          <div className="flex items-center gap-3 mb-8">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <span className={`w-2 h-2 rounded-full ${system?.status === 'running' ? 'bg-emerald-400 animate-pulse' : 'bg-gray-500'}`} />
              <span className="text-xs text-emerald-400 font-mono">{system?.status === 'running' ? 'ONLINE' : 'CONNECTING'}</span>
            </div>
            <span className="text-xs text-gray-600 font-mono">uptime {formatUptime(uptime)}</span>
          </div>

          <h1 className="text-6xl md:text-8xl font-black tracking-tight mb-4">
            <span className="bg-gradient-to-r from-white via-emerald-200 to-cyan-200 bg-clip-text text-transparent">Over</span>
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">LLM</span>
          </h1>
          <p className="text-xl md:text-2xl text-gray-400 mb-2 max-w-2xl font-light">
            Personal-contextual language model built from scratch.
          </p>
          <p className="text-sm text-gray-600 mb-10 max-w-xl font-mono">
            C++ inference · Go orchestration · Rust telemetry · DPO training · Zero dependencies
          </p>

          <div className="flex flex-wrap gap-3 mb-16">
            <Link to="/training" className="group flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm font-medium hover:bg-emerald-500/20 transition-all">
              <BarChart3 className="w-4 h-4" />
              Training Dashboard
              <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link to="/dashboard" className="group flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white/5 border border-white/10 text-gray-300 text-sm font-medium hover:bg-white/10 transition-all">
              <Activity className="w-4 h-4" />
              System Monitor
              <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>

          {/* Live Metrics Strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-white/5 rounded-xl overflow-hidden">
            <MetricCell label="DPO Loss" value={training?.dpo_loss?.toFixed(4) || '—'} sub={training?.status === 'training' ? 'training' : training?.status || 'idle'} />
            <MetricCell label="Training Pairs" value={training?.preference_pairs?.toLocaleString() || '—'} sub={`${training?.vocab_size?.toLocaleString() || '0'} vocab`} />
            <MetricCell label="Telemetry Events" value={system?.telemetry?.toString() || '—'} sub="rolling window" />
            <MetricCell label="DPO Queue" value={system?.queue_size?.toString() || '—'} sub="preference pairs" />
          </div>
        </div>
      </div>

      {/* Architecture */}
      <div className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-xs font-mono text-gray-500 tracking-widest uppercase mb-8">Architecture</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <ArchCard icon={Cpu} title="C++ Engine" lang="C++" desc="Custom tensor ops, multi-head causal attention, transformer decoder. No PyTorch, no CUDA — pure CPU inference with binary weight format." color="emerald" />
          <ArchCard icon={Globe} title="Go Agent" lang="Go" desc="HTTP telemetry ingestion, Ollama client, automatic preference pair generation every 30s, DPO batch queue, REST API." color="cyan" />
          <ArchCard icon={Terminal} title="Rust Daemon" lang="Rust" desc="Active app detection, system stats, process monitoring, file access tracking, network summary. Async publisher to Go agent." color="violet" />
        </div>
      </div>

      {/* How It Works */}
      <div className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-xs font-mono text-gray-500 tracking-widest uppercase mb-8">Punishment-as-Reward DPO</h2>
        <div className="grid md:grid-cols-4 gap-4">
          <StepCard n="01" title="Harvest" desc="Rust daemon polls macOS every 5s — active app, file access, CPU, RAM, network, process tree." />
          <StepCard n="02" title="Generate" desc="Go agent queries Ollama twice: without context (rejected) and with full telemetry (chosen)." />
          <StepCard n="03" title="Train" desc="DPO trainer maximizes margin between chosen and rejected responses. Model learns to exploit system metadata." />
          <StepCard n="04" title="Infer" desc="C++ engine loads trained weights for fast local inference. No cloud, no latency, fully offline." />
        </div>
      </div>

      {/* Data Sources */}
      <div className="max-w-7xl mx-auto px-6 py-16">
        <h2 className="text-xs font-mono text-gray-500 tracking-widest uppercase mb-8">Data Sources</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <SourcePill icon={Layers} label="System Telemetry" live />
          <SourcePill icon={Database} label="HuggingFace" />
          <SourcePill icon={Globe} label="RSS News" />
          <SourcePill icon={GitBranch} label="Git Activity" />
          <SourcePill icon={Shield} label="Ollama Teacher" live />
        </div>
      </div>

      {/* Tech Stack */}
      <div className="max-w-7xl mx-auto px-6 py-16 pb-24">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-6">
            <h3 className="text-sm font-mono text-gray-400 mb-4">Stack</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Inference</span><span className="text-gray-300 font-mono">C++ / ARM64</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Orchestration</span><span className="text-gray-300 font-mono">Go 1.26</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Telemetry</span><span className="text-gray-300 font-mono">Rust / tokio</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Training</span><span className="text-gray-300 font-mono">Python / NumPy</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Dashboard</span><span className="text-gray-300 font-mono">React / Recharts</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Deploy</span><span className="text-gray-300 font-mono">Vercel / Docker</span></div>
            </div>
          </div>
          <div className="bg-white/[0.02] rounded-xl border border-white/5 p-6">
            <h3 className="text-sm font-mono text-gray-400 mb-4">Model</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Architecture</span><span className="text-gray-300 font-mono">Transformer Decoder</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Parameters</span><span className="text-gray-300 font-mono">~580K</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Embedding</span><span className="text-gray-300 font-mono">d=64, 2 heads</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Layers</span><span className="text-gray-300 font-mono">2 blocks, FFN=128</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Training</span><span className="text-gray-300 font-mono">DPO (β=0.1)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Binary Size</span><span className="text-gray-300 font-mono">~50MB total</span></div>
            </div>
          </div>
        </div>
        <p className="text-center text-xs text-gray-700 mt-12 font-mono">OverLLM — runs entirely offline on your Mac</p>
      </div>
    </div>
  )
}

function MetricCell({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-[#0a0a18] p-5">
      <div className="text-2xl font-bold text-white font-mono">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
      <div className="text-xs text-gray-600 font-mono">{sub}</div>
    </div>
  )
}

function ArchCard({ icon: Icon, title, lang, desc, color }: { icon: React.ElementType; title: string; lang: string; desc: string; color: string }) {
  const colors: Record<string, string> = {
    emerald: 'border-emerald-500/20 hover:border-emerald-500/40',
    cyan: 'border-cyan-500/20 hover:border-cyan-500/40',
    violet: 'border-violet-500/20 hover:border-violet-500/40',
  }
  const iconColors: Record<string, string> = {
    emerald: 'text-emerald-400',
    cyan: 'text-cyan-400',
    violet: 'text-violet-400',
  }
  return (
    <div className={`bg-white/[0.02] rounded-xl border ${colors[color]} p-6 transition-all`}>
      <div className="flex items-center gap-3 mb-3">
        <Icon className={`w-5 h-5 ${iconColors[color]}`} />
        <span className="text-sm font-semibold text-white">{title}</span>
        <span className={`text-xs font-mono ${iconColors[color]} ml-auto`}>{lang}</span>
      </div>
      <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
    </div>
  )
}

function StepCard({ n, title, desc }: { n: string; title: string; desc: string }) {
  return (
    <div className="bg-white/[0.02] rounded-xl border border-white/5 p-5">
      <span className="text-xs font-mono text-emerald-500">{n}</span>
      <h3 className="text-sm font-semibold text-white mt-1 mb-2">{title}</h3>
      <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
    </div>
  )
}

function SourcePill({ icon: Icon, label, live }: { icon: React.ElementType; label: string; live?: boolean }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/5 text-xs text-gray-400">
      <Icon className="w-3.5 h-3.5" />
      <span>{label}</span>
      {live && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse ml-auto" />}
    </div>
  )
}
