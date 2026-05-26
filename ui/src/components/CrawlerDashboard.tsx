import React, { useState, useEffect } from 'react'
import { Globe, Play, Pause, RefreshCw, Database, Eye, Layout, Image, Link2, BarChart3, CheckCircle, AlertCircle, Zap, Target } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'

interface CrawlerStats {
  total_pages_crawled: number
  unique_urls: number
  domains_crawled: number
  domain_breakdown: Record<string, number>
  is_crawling: boolean
  avg_page_size: number
}

interface CrawledPage {
  url: string
  title: string
  domain: string
  timestamp: number
  content_hash: string
  text_length: number
  visual_features: {
    layout_structure: {
      total_elements: number
      header_count: number
      nav_count: number
      main_count: number
      section_count: number
      article_count: number
      aside_count: number
      footer_count: number
    }
    content_density: {
      text_to_html_ratio: number
      text_length: number
      word_count: number
    }
    media_elements: {
      image_count: number
      video_count: number
      audio_count: number
    }
    interactive_elements: {
      button_count: number
      form_count: number
      link_count: number
    }
  }
}

const API_URL = 'http://localhost:8001'

export default function CrawlerDashboard() {
  const [stats, setStats] = useState<CrawlerStats | null>(null)
  const [pages, setPages] = useState<CrawledPage[]>([])
  const [isCrawling, setIsCrawling] = useState(false)
  const [seedUrls, setSeedUrls] = useState('https://github.com,https://stackoverflow.com,https://docs.python.org')
  const [maxPages, setMaxPages] = useState(100)
  const [maxDepth, setMaxDepth] = useState(3)
  const [followExternal, setFollowExternal] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedPage, setSelectedPage] = useState<CrawledPage | null>(null)

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 2000)
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/crawler/status`)
      const data = await res.json()
      setStats(data)
      setIsCrawling(data.is_crawling)
      setError(null)
    } catch (e) {
      setError('Failed to fetch crawler status')
    }
  }

  const fetchPages = async () => {
    try {
      const res = await fetch(`${API_URL}/api/crawler/pages`)
      const data = await res.json()
      setPages(data.pages || [])
    } catch (e) {
      console.error('Failed to fetch pages:', e)
    }
  }

  const startCrawler = async () => {
    try {
      const urls = seedUrls.split(',').map(u => u.trim()).filter(u => u)
      const res = await fetch(`${API_URL}/api/crawler/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seed_urls: urls,
          max_pages: maxPages,
          max_depth: maxDepth,
          follow_external: followExternal
        })
      })
      
      if (res.ok) {
        setIsCrawling(true)
        setError(null)
        // Start fetching pages
        fetchPages()
        const pageInterval = setInterval(fetchPages, 3000)
        return () => clearInterval(pageInterval)
      }
    } catch (e) {
      setError('Failed to start crawler')
    }
  }

  const stopCrawler = async () => {
    try {
      await fetch(`${API_URL}/api/crawler/stop`, { method: 'POST' })
      setIsCrawling(false)
    } catch (e) {
      setError('Failed to stop crawler')
    }
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toFixed(0)
  }

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${bytes}B`
  }

  const domainData = stats?.domain_breakdown 
    ? Object.entries(stats.domain_breakdown).map(([domain, count]) => ({
        name: domain,
        value: count
      }))
    : []

  const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4']

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Globe className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-300 to-purple-300 bg-clip-text text-transparent">
                OverLLM Web Crawler
              </h1>
              <p className="text-sm text-blue-400/60">Iframe Vision • Real-time Extraction • Training Data</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isCrawling && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/20 border border-blue-500/40 text-blue-300 text-sm">
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                CRAWLING
              </div>
            )}
            {!isCrawling && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-500/20 border border-gray-500/40 text-gray-400 text-sm">
                <CheckCircle className="w-4 h-4" />
                IDLE
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-300 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Crawler Controls */}
        <div className="bg-[#111128] rounded-2xl border border-blue-500/20 p-6">
          <h2 className="text-lg font-semibold text-blue-200 mb-4">Crawler Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400 mb-1 block">Seed URLs (comma-separated)</label>
              <input
                type="text"
                value={seedUrls}
                onChange={(e) => setSeedUrls(e.target.value)}
                className="w-full bg-[#0a0a1a] border border-white/10 rounded-lg px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
                placeholder="https://example.com,https://another.com"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Max Pages</label>
                <input
                  type="number"
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  className="w-full bg-[#0a0a1a] border border-white/10 rounded-lg px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Max Depth</label>
                <input
                  type="number"
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Number(e.target.value))}
                  className="w-full bg-[#0a0a1a] border border-white/10 rounded-lg px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={startCrawler}
                  disabled={isCrawling}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-all"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
              </div>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={followExternal}
                onChange={(e) => setFollowExternal(e.target.checked)}
                className="rounded bg-[#0a0a1a] border-white/10"
              />
              Follow external links
            </label>
            <button
              onClick={stopCrawler}
              disabled={!isCrawling}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-all"
            >
              <Pause className="w-4 h-4" />
              Stop
            </button>
            <button
              onClick={fetchStats}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard
            icon={Database}
            label="Pages Crawled"
            value={stats ? formatNumber(stats.total_pages_crawled) : '--'}
            sub={stats ? `${stats.unique_urls} unique URLs` : ''}
            gradient="from-blue-500 to-cyan-500"
          />
          <KPICard
            icon={Globe}
            label="Domains"
            value={stats ? stats.domains_crawled.toString() : '--'}
            sub={stats ? `${Object.keys(stats.domain_breakdown || {}).length} active` : ''}
            gradient="from-purple-500 to-pink-500"
          />
          <KPICard
            icon={Layout}
            label="Avg Page Size"
            value={stats ? formatBytes(stats.avg_page_size) : '--'}
            sub="HTML content"
            gradient="from-emerald-500 to-green-500"
          />
          <KPICard
            icon={Zap}
            label="Status"
            value={isCrawling ? 'Active' : 'Idle'}
            sub={isCrawling ? 'Crawling in progress' : 'Ready to start'}
            gradient={isCrawling ? 'from-orange-500 to-amber-500' : 'from-gray-500 to-gray-600'}
          />
        </div>

        {/* Domain Breakdown Chart */}
        {domainData.length > 0 && (
          <div className="bg-[#111128] rounded-2xl border border-purple-500/20 p-6">
            <h2 className="text-lg font-semibold text-purple-200 mb-4">Domain Distribution</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={domainData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {domainData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111128', border: '1px solid #8b5cf640', borderRadius: '12px' }}
                    labelStyle={{ color: '#a78bfa' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {domainData.map((item, index) => (
                  <div key={item.name} className="flex items-center justify-between p-2 bg-[#0a0a1a] rounded-lg">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                      <span className="text-sm text-gray-300">{item.name}</span>
                    </div>
                    <span className="text-sm font-semibold text-white">{item.value} pages</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Crawled Pages List */}
        {pages.length > 0 && (
          <div className="bg-[#111128] rounded-2xl border border-blue-500/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-blue-200">Crawled Pages</h2>
              <span className="text-sm text-gray-400">{pages.length} pages</span>
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {pages.slice(0, 20).map((page, index) => (
                <div
                  key={index}
                  onClick={() => setSelectedPage(page)}
                  className="p-3 bg-[#0a0a1a] rounded-lg hover:bg-white/5 cursor-pointer transition-all border border-transparent hover:border-white/10"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-white truncate">{page.title || 'Untitled'}</div>
                      <div className="text-xs text-gray-400 truncate">{page.url}</div>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500 ml-4">
                      <span>{formatBytes(page.text_length)}</span>
                      <span>{page.visual_features?.layout_structure?.total_elements || 0} elements</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Page Detail Modal */}
        {selectedPage && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-[#111128] rounded-2xl border border-blue-500/20 p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">{selectedPage.title || 'Untitled'}</h2>
                <button
                  onClick={() => setSelectedPage(null)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-gray-400 mb-1">URL</div>
                  <div className="text-sm text-blue-300 break-all">{selectedPage.url}</div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-400 mb-1">Domain</div>
                  <div className="text-sm text-white">{selectedPage.domain}</div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatItem label="Text Length" value={formatBytes(selectedPage.text_length)} />
                  <StatItem label="Total Elements" value={selectedPage.visual_features?.layout_structure?.total_elements || 0} />
                  <StatItem label="Images" value={selectedPage.visual_features?.media_elements?.image_count || 0} />
                  <StatItem label="Links" value={selectedPage.visual_features?.interactive_elements?.link_count || 0} />
                </div>
                
                <div>
                  <div className="text-sm text-gray-400 mb-2">Layout Structure</div>
                  <div className="grid grid-cols-4 gap-2">
                    <MiniStat label="Headers" value={selectedPage.visual_features?.layout_structure?.header_count || 0} />
                    <MiniStat label="Nav" value={selectedPage.visual_features?.layout_structure?.nav_count || 0} />
                    <MiniStat label="Main" value={selectedPage.visual_features?.layout_structure?.main_count || 0} />
                    <MiniStat label="Sections" value={selectedPage.visual_features?.layout_structure?.section_count || 0} />
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-400 mb-2">Content Density</div>
                  <div className="bg-[#0a0a1a] rounded-lg p-3">
                    <div className="text-sm text-white">
                      Text/HTML Ratio: {(selectedPage.visual_features?.content_density?.text_to_html_ratio || 0).toFixed(3)}
                    </div>
                    <div className="text-sm text-gray-400 mt-1">
                      Words: {selectedPage.visual_features?.content_density?.word_count || 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="text-center text-xs text-gray-600 mt-8">
          OverLLM Web Crawler • Iframe Vision • Real-time Training Data Collection
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

function StatItem({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-[#0a0a1a] rounded-lg p-3">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-lg font-semibold text-white">{value}</div>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-[#0a0a1a] rounded p-2 text-center">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  )
}