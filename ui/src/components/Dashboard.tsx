import React, { useEffect, useMemo, useState } from 'react'
import { Activity, Bot, Box, CheckCircle, Database, FileCode2, Flame, Globe, HardDrive, Link2, Network, Server, ShieldCheck, Workflow, Zap } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface SystemStatus {
  status: string
  queue_size: number
  telemetry: number
  model: string
  model_path?: string
  vocab_path?: string
  runtime?: string
  ollama?: string
}

interface TrainingMetrics {
  status: string
  current_epoch: number
  total_epochs: number
  dpo_loss: number
  preference_pairs: number
  vocab_size: number
  elapsed_s: number
  epoch_history: { epoch: number; loss: number; time_s: number }[]
}

interface NodeInfo {
  node_id: string
  host: string
  os: string
  arch: string
  cpus: number
  workspace: string
  role: string
  chain: string
  work_contract: string
}

interface FileInfo {
  rel_path: string
  path: string
  size: number
  modified: string
  in_use: boolean
  role?: string
}

interface CrawlerStatus {
  status: string
  is_crawling: boolean
  total_pages_crawled: number
  unique_urls: number
  domains_crawled: number
  seed_urls?: string[]
}

interface PipelineStage {
  name: string
  status: string
  active?: boolean
  detail: string
}

export default function Dashboard() {
  const [system, setSystem] = useState<SystemStatus | null>(null)
  const [training, setTraining] = useState<TrainingMetrics | null>(null)
  const [node, setNode] = useState<NodeInfo | null>(null)
  const [files, setFiles] = useState<FileInfo[]>([])
  const [crawler, setCrawler] = useState<CrawlerStatus | null>(null)
  const [pipeline, setPipeline] = useState<{ stages: PipelineStage[]; token_policy: string; chain: string } | null>(null)
  const [telemetry, setTelemetry] = useState<any[]>([])
  const [refreshCount, setRefreshCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchJSON = async (url: string) => {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`${url} ${res.status}`)
      return res.json()
    }
    const fetchAll = async () => {
      try {
        const [status, metrics, nodeInfo, fileInfo, crawlerInfo, pipelineInfo, telemetryInfo] = await Promise.all([
          fetchJSON('/api/status'),
          fetchJSON('/api/metrics'),
          fetchJSON('/api/node'),
          fetchJSON('/api/files'),
          fetchJSON('/api/crawler/status'),
          fetchJSON('/api/pipeline'),
          fetchJSON('/api/telemetry'),
        ])
        setSystem(status)
        if (metrics.status !== 'no_data') setTraining(metrics)
        setNode(nodeInfo)
        setFiles(fileInfo.files || [])
        setCrawler(crawlerInfo)
        setPipeline(pipelineInfo)
        setTelemetry(telemetryInfo || [])
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Backend unavailable')
      }
      setRefreshCount(c => c + 1)
    }
    fetchAll()
    const interval = setInterval(fetchAll, 3000)
    return () => clearInterval(interval)
  }, [])

  const inUseFiles = useMemo(() => files.filter(f => f.in_use), [files])
  const recentFiles = useMemo(() => files.slice(0, 18), [files])
  const live = system?.status === 'running'

  return (
    <div className="min-h-screen bg-[#0b0704] text-orange-50 pt-24 px-6 pb-8">
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_15%_10%,rgba(251,146,60,0.22),transparent_34%),radial-gradient(circle_at_82%_0%,rgba(245,158,11,0.16),transparent_30%),linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,0.34))]" />
      <div className="relative max-w-7xl mx-auto space-y-5">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="h-11 w-11 rounded-lg border border-orange-300/20 bg-orange-400/10 flex items-center justify-center shadow-[0_0_24px_rgba(251,146,60,0.2)]">
                <Flame className="h-5 w-5 text-orange-300" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">OverLLM Node Console</h1>
                <p className="text-xs text-orange-200/55 font-mono">{node?.node_id || 'discovering node'} · {pipeline?.chain || 'blockchain/overllm'}</p>
              </div>
            </div>
            <p className="max-w-3xl text-sm text-orange-100/64">
              Every prompt is treated as work: collect sources, run local inference, emit a receipt, and prepare confirmation. This dashboard shows the machine, files, crawler, ETL, training, and token-origin surfaces without hiding the machinery.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Pill live={live} label={live ? 'NODE ONLINE' : 'NODE OFFLINE'} />
            <span className="text-xs font-mono text-orange-200/45">poll #{refreshCount}</span>
          </div>
        </header>

        {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}

        <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
          <Metric icon={Server} label="Runtime" value={system?.model || '-'} sub={system?.ollama === 'disabled' ? 'Ollama disabled' : 'external'} />
          <Metric icon={Activity} label="Telemetry" value={`${system?.telemetry || 0}`} sub="events" />
          <Metric icon={Globe} label="Crawler" value={crawler?.status || 'idle'} sub={`${crawler?.total_pages_crawled || 0} pages`} active={crawler?.is_crawling} />
          <Metric icon={Database} label="Training" value={training?.status || 'idle'} sub={training ? `${training.preference_pairs.toLocaleString()} pairs` : 'no data'} />
          <Metric icon={FileCode2} label="Files" value={`${files.length}`} sub={`${inUseFiles.length} in use`} />
          <Metric icon={Box} label="Queue" value={`${system?.queue_size || 0}`} sub="DPO work" />
          <Metric icon={ShieldCheck} label="Confirm" value="receipt" sub="local proof" />
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <Panel className="xl:col-span-2" title="ETL, Training, Build, Confirmation" icon={Workflow}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {(pipeline?.stages || []).map(stage => (
                <div key={stage.name} className="rounded-lg border border-orange-200/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs uppercase tracking-[0.22em] text-orange-200/45">{stage.name}</span>
                    <span className={`h-2 w-2 rounded-full ${stage.active ? 'bg-orange-300 animate-pulse' : stage.status === 'ready' || stage.status === 'complete' ? 'bg-emerald-300' : 'bg-orange-500/50'}`} />
                  </div>
                  <div className="text-lg font-semibold text-orange-50">{stage.status}</div>
                  <p className="mt-2 text-xs leading-5 text-orange-100/50">{stage.detail}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-lg border border-orange-300/10 bg-orange-400/5 p-3 text-xs text-orange-100/60 font-mono">
              token policy: {pipeline?.token_policy || 'loading dynamic origin policy'}
            </div>
          </Panel>

          <Panel title="Machine As Node" icon={Network}>
            <Info label="host" value={node?.host} />
            <Info label="platform" value={node ? `${node.os}/${node.arch} · ${node.cpus} cpu` : undefined} />
            <Info label="role" value={node?.role} />
            <Info label="workspace" value={node?.workspace} />
            <Info label="contract" value={node?.work_contract} />
          </Panel>
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-5 gap-4">
          <Panel className="xl:col-span-3" title="Training Loss And Work Receipts" icon={Bot}>
            {training?.epoch_history?.length ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={training.epoch_history}>
                  <defs>
                    <linearGradient id="orangeLoss" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#fb923c" stopOpacity={0.42} />
                      <stop offset="100%" stopColor="#fb923c" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(251,146,60,0.12)" />
                  <XAxis dataKey="epoch" stroke="rgba(254,215,170,0.45)" fontSize={10} />
                  <YAxis stroke="rgba(254,215,170,0.45)" fontSize={10} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ background: '#120b06', border: '1px solid rgba(251,146,60,.22)', borderRadius: 8, color: '#fed7aa' }} />
                  <Area type="monotone" dataKey="loss" stroke="#fb923c" strokeWidth={2} fill="url(#orangeLoss)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : <Empty text="No training metrics found." />}
          </Panel>

          <Panel className="xl:col-span-2" title="Crawler Truth Intake" icon={Link2}>
            <div className="grid grid-cols-3 gap-2 mb-4">
              <Mini label="pages" value={crawler?.total_pages_crawled || 0} />
              <Mini label="urls" value={crawler?.unique_urls || 0} />
              <Mini label="domains" value={crawler?.domains_crawled || 0} />
            </div>
            <p className="text-xs text-orange-100/50 mb-3">Seed URLs</p>
            <div className="space-y-2">
              {(crawler?.seed_urls || []).length ? crawler?.seed_urls?.map(seed => (
                <div key={seed} className="truncate rounded-md bg-black/25 border border-orange-200/10 px-3 py-2 text-xs font-mono text-orange-100/65">{seed}</div>
              )) : <Empty text="No crawler seeds yet. Open Crawler and start collection." />}
            </div>
          </Panel>
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Panel title="Files Used By This Node" icon={HardDrive}>
            <FileList files={inUseFiles.length ? inUseFiles : recentFiles.slice(0, 6)} />
          </Panel>
          <Panel title="All Visible Project Files" icon={Box}>
            <FileList files={recentFiles} compact />
          </Panel>
        </section>

        <Panel title="Recent Telemetry And Prompt Work" icon={Zap}>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2">
            {telemetry.slice(-12).reverse().map((event, index) => (
              <div key={index} className="rounded-md border border-orange-200/10 bg-black/25 px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.18em] text-orange-200/35">{event.type || 'event'}</div>
                <div className="mt-1 text-xs font-mono text-orange-100/60 truncate">{event.data || JSON.stringify(event)}</div>
              </div>
            ))}
            {!telemetry.length && <Empty text="No telemetry events yet." />}
          </div>
        </Panel>
      </div>
    </div>
  )
}

function Panel({ title, icon: Icon, children, className = '' }: { title: string; icon: React.ElementType; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-orange-200/10 bg-[#100a06]/86 shadow-[0_20px_70px_rgba(0,0,0,0.32)] p-5 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="h-4 w-4 text-orange-300" />
        <h2 className="text-sm font-medium tracking-wide text-orange-50">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function Metric({ icon: Icon, label, value, sub, active }: { icon: React.ElementType; label: string; value: string; sub: string; active?: boolean }) {
  return (
    <div className="rounded-lg border border-orange-200/10 bg-[#100a06]/80 p-4">
      <div className="flex items-center justify-between mb-3">
        <Icon className="h-4 w-4 text-orange-300/80" />
        <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-orange-300 animate-pulse' : 'bg-orange-300/35'}`} />
      </div>
      <div className="text-lg font-semibold font-mono truncate">{value}</div>
      <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-orange-200/38">{label}</div>
      <div className="mt-1 text-xs text-orange-100/42 truncate">{sub}</div>
    </div>
  )
}

function Pill({ live, label }: { live: boolean; label: string }) {
  return <div className={`rounded-full border px-3 py-1.5 text-xs font-mono ${live ? 'border-orange-300/30 bg-orange-400/10 text-orange-200' : 'border-red-400/30 bg-red-500/10 text-red-200'}`}>{label}</div>
}

function Info({ label, value }: { label: string; value?: string }) {
  return (
    <div className="mb-3">
      <div className="text-[10px] uppercase tracking-[0.2em] text-orange-200/34">{label}</div>
      <div className="mt-1 break-all text-xs font-mono text-orange-100/65">{value || '-'}</div>
    </div>
  )
}

function Mini({ label, value }: { label: string; value: number }) {
  return <div className="rounded-md bg-black/25 border border-orange-200/10 p-3"><div className="text-lg font-mono">{value}</div><div className="text-[10px] uppercase tracking-widest text-orange-200/35">{label}</div></div>
}

function FileList({ files, compact = false }: { files: FileInfo[]; compact?: boolean }) {
  return (
    <div className={`space-y-2 overflow-y-auto ${compact ? 'max-h-72' : 'max-h-80'}`}>
      {files.map(file => (
        <div key={file.path} className="rounded-md border border-orange-200/10 bg-black/25 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-xs font-mono text-orange-50/80">{file.rel_path}</div>
              {file.role && <div className="mt-1 text-[10px] text-orange-300/70">{file.role}</div>}
            </div>
            {file.in_use && <CheckCircle className="h-3.5 w-3.5 flex-none text-orange-300" />}
          </div>
        </div>
      ))}
      {!files.length && <Empty text="No files returned." />}
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-md border border-orange-200/10 bg-black/20 px-3 py-4 text-xs text-orange-100/42">{text}</div>
}
