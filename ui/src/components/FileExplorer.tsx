import React, { useState, useEffect } from 'react'
import { FileText, Folder, Search, DollarSign, Clock, TrendingUp, ArrowUp, ArrowDown, ChevronRight, ChevronDown, RefreshCw, Filter, SortAsc } from 'lucide-react'

interface FileItem {
  name: string
  path: string
  type: 'file' | 'folder'
  size: number
  modified: number
  appraisal: number
  kpis: {
    hourlyViews: number
    hourlyEdits: number
    hourlyCommits: number
    score: number
  }
}

export default function FileExplorer() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [currentPath, setCurrentPath] = useState('/')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'name' | 'size' | 'modified' | 'appraisal'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    loadFiles(currentPath)
  }, [currentPath])

  const loadFiles = async (path: string) => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/files?path=${encodeURIComponent(path)}`)
      const data = await response.json()
      setFiles(data.files || [])
    } catch (error) {
      console.error('Failed to load files:', error)
      // Mock data for demo
      setFiles(generateMockFiles())
    } finally {
      setIsLoading(false)
    }
  }

  const generateMockFiles = (): FileItem[] => [
    {
      name: 'src',
      path: '/src',
      type: 'folder',
      size: 0,
      modified: Date.now(),
      appraisal: 0,
      kpis: { hourlyViews: 45, hourlyEdits: 12, hourlyCommits: 3, score: 85 }
    },
    {
      name: 'components',
      path: '/components',
      type: 'folder',
      size: 0,
      modified: Date.now() - 3600000,
      appraisal: 0,
      kpis: { hourlyViews: 32, hourlyEdits: 8, hourlyCommits: 2, score: 78 }
    },
    {
      name: 'App.tsx',
      path: '/App.tsx',
      type: 'file',
      size: 2456,
      modified: Date.now() - 7200000,
      appraisal: 1250.00,
      kpis: { hourlyViews: 67, hourlyEdits: 15, hourlyCommits: 5, score: 92 }
    },
    {
      name: 'index.html',
      path: '/index.html',
      type: 'file',
      size: 1024,
      modified: Date.now() - 10800000,
      appraisal: 450.00,
      kpis: { hourlyViews: 23, hourlyEdits: 3, hourlyCommits: 1, score: 65 }
    },
    {
      name: 'package.json',
      path: '/package.json',
      type: 'file',
      size: 512,
      modified: Date.now() - 14400000,
      appraisal: 890.00,
      kpis: { hourlyViews: 45, hourlyEdits: 7, hourlyCommits: 2, score: 88 }
    },
    {
      name: 'README.md',
      path: '/README.md',
      type: 'file',
      size: 3072,
      modified: Date.now() - 18000000,
      appraisal: 2100.00,
      kpis: { hourlyViews: 89, hourlyEdits: 4, hourlyCommits: 1, score: 95 }
    },
    {
      name: 'tsconfig.json',
      path: '/tsconfig.json',
      type: 'file',
      size: 768,
      modified: Date.now() - 21600000,
      appraisal: 675.00,
      kpis: { hourlyViews: 34, hourlyEdits: 2, hourlyCommits: 0, score: 72 }
    }
  ]

  const filteredFiles = files
    .filter(file => 
      file.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'size':
          comparison = a.size - b.size
          break
        case 'modified':
          comparison = a.modified - b.modified
          break
        case 'appraisal':
          comparison = a.appraisal - b.appraisal
          break
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '-'
    const units = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
  }

  const formatTime = (timestamp: number) => {
    const diff = Date.now() - timestamp
    const hours = Math.floor(diff / 3600000)
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value)
  }

  const handleFileClick = (file: FileItem) => {
    if (file.type === 'folder') {
      setCurrentPath(file.path)
    } else {
      setSelectedFile(file)
    }
  }

  const totalAppraisal = files.reduce((sum, file) => sum + file.appraisal, 0)
  const avgScore = files.length > 0 
    ? Math.round(files.reduce((sum, file) => sum + file.kpis.score, 0) / files.length)
    : 0

  return (
    <div className="pt-24 min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center shadow-lg shadow-amber-500/30">
              <Folder className="w-6 h-6 text-amber-950" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-amber-200">File Explorer</h1>
              <p className="text-amber-400/70 text-sm">Intelligent file management with real-time KPIs</p>
            </div>
          </div>
          
          <button
            onClick={() => loadFiles(currentPath)}
            className="px-4 py-2 rounded-xl bg-amber-800/30 border border-amber-600/50 text-amber-200 text-sm hover:bg-amber-800/50 transition-all flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            icon={<DollarSign className="w-5 h-5" />}
            label="Total Appraisal"
            value={formatCurrency(totalAppraisal)}
            gradient="from-amber-500 to-yellow-500"
          />
          <StatCard
            icon={<TrendingUp className="w-5 h-5" />}
            label="Avg Score"
            value={`${avgScore}/100`}
            gradient="from-amber-400 to-orange-500"
          />
          <StatCard
            icon={<FileText className="w-5 h-5" />}
            label="Total Files"
            value={files.length.toString()}
            gradient="from-yellow-500 to-amber-600"
          />
          <StatCard
            icon={<Clock className="w-5 h-5" />}
            label="Last Updated"
            value={formatTime(Math.max(...files.map(f => f.modified)))}
            gradient="from-amber-600 to-yellow-500"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* File List */}
          <div className="lg:col-span-2 bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 border-b border-amber-700/30">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-amber-400/50" />
                  <input
                    type="text"
                    placeholder="Search files..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 pr-4 py-2 bg-amber-900/30 border border-amber-700/50 rounded-xl text-amber-200 placeholder-amber-400/50 focus:outline-none focus:border-amber-500/50 text-sm w-64"
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="px-3 py-2 bg-amber-900/30 border border-amber-700/50 rounded-xl text-amber-200 text-sm focus:outline-none focus:border-amber-500/50"
                >
                  <option value="name">Name</option>
                  <option value="size">Size</option>
                  <option value="modified">Modified</option>
                  <option value="appraisal">Appraisal</option>
                </select>
                <button
                  onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                  className="p-2 rounded-xl bg-amber-900/30 border border-amber-700/50 text-amber-400 hover:bg-amber-800/50 transition-all"
                >
                  {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Breadcrumb */}
            <div className="px-4 py-2 border-b border-amber-700/30 bg-amber-900/20">
              <div className="flex items-center gap-2 text-sm">
                <button
                  onClick={() => setCurrentPath('/')}
                  className="text-amber-400 hover:text-amber-200 transition-colors"
                >
                  Root
                </button>
                {currentPath.split('/').filter(Boolean).map((part, i, arr) => (
                  <React.Fragment key={i}>
                    <ChevronRight className="w-4 h-4 text-amber-400/50" />
                    <button
                      onClick={() => setCurrentPath('/' + arr.slice(0, i + 1).join('/'))}
                      className="text-amber-400 hover:text-amber-200 transition-colors"
                    >
                      {part}
                    </button>
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* File List */}
            <div className="divide-y divide-amber-700/30 max-h-[600px] overflow-y-auto">
              {isLoading ? (
                <div className="p-8 text-center text-amber-400/50">
                  Loading files...
                </div>
              ) : filteredFiles.length === 0 ? (
                <div className="p-8 text-center text-amber-400/50">
                  No files found
                </div>
              ) : (
                filteredFiles.map((file) => (
                  <div
                    key={file.path}
                    onClick={() => handleFileClick(file)}
                    className="flex items-center gap-4 px-4 py-3 hover:bg-amber-900/30 transition-colors cursor-pointer"
                  >
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      file.type === 'folder' 
                        ? 'bg-amber-500/20 text-amber-400' 
                        : 'bg-amber-800/30 text-amber-300'
                    }`}>
                      {file.type === 'folder' ? (
                        <Folder className="w-5 h-5" />
                      ) : (
                        <FileText className="w-5 h-5" />
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-amber-200 font-medium truncate">{file.name}</div>
                      <div className="text-amber-400/50 text-xs">{formatSize(file.size)}</div>
                    </div>

                    <div className="text-right">
                      <div className="text-amber-200 font-bold">{formatCurrency(file.appraisal)}</div>
                      <div className="text-amber-400/50 text-xs">{formatTime(file.modified)}</div>
                    </div>

                    <div className="text-right">
                      <div className={`font-bold ${
                        file.kpis.score >= 80 ? 'text-green-400' :
                        file.kpis.score >= 60 ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {file.kpis.score}
                      </div>
                      <div className="text-amber-400/50 text-xs">Score</div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <div className="text-amber-300 text-sm">{file.kpis.hourlyViews}</div>
                        <div className="text-amber-400/50 text-xs">views</div>
                      </div>
                      <div className="text-right">
                        <div className="text-amber-300 text-sm">{file.kpis.hourlyEdits}</div>
                        <div className="text-amber-400/50 text-xs">edits</div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* File Details */}
          <div className="bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
            {selectedFile ? (
              <>
                <div className="flex items-center gap-3 mb-6">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    selectedFile.type === 'folder' 
                      ? 'bg-amber-500/20 text-amber-400' 
                      : 'bg-amber-800/30 text-amber-300'
                  }`}>
                    {selectedFile.type === 'folder' ? (
                      <Folder className="w-6 h-6" />
                    ) : (
                      <FileText className="w-6 h-6" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-amber-200">{selectedFile.name}</h3>
                    <p className="text-amber-400/70 text-sm">{selectedFile.path}</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <DetailItem
                    label="Appraisal Value"
                    value={formatCurrency(selectedFile.appraisal)}
                    icon={<DollarSign className="w-4 h-4" />}
                  />
                  <DetailItem
                    label="File Size"
                    value={formatSize(selectedFile.size)}
                    icon={<FileText className="w-4 h-4" />}
                  />
                  <DetailItem
                    label="Last Modified"
                    value={formatTime(selectedFile.modified)}
                    icon={<Clock className="w-4 h-4" />}
                  />
                  
                  <div className="pt-4 border-t border-amber-700/30">
                    <h4 className="text-amber-200 font-semibold mb-3">Hourly KPIs</h4>
                    <div className="space-y-3">
                      <KPICard
                        label="Views"
                        value={selectedFile.kpis.hourlyViews}
                        trend="up"
                        percentage={12}
                      />
                      <KPICard
                        label="Edits"
                        value={selectedFile.kpis.hourlyEdits}
                        trend="up"
                        percentage={8}
                      />
                      <KPICard
                        label="Commits"
                        value={selectedFile.kpis.hourlyCommits}
                        trend="down"
                        percentage={-3}
                      />
                    </div>
                  </div>

                  <div className="pt-4 border-t border-amber-700/30">
                    <h4 className="text-amber-200 font-semibold mb-3">Quality Score</h4>
                    <div className="relative h-3 bg-amber-900/50 rounded-full overflow-hidden">
                      <div
                        className={`absolute inset-y-0 left-0 rounded-full transition-all ${
                          selectedFile.kpis.score >= 80 ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
                          selectedFile.kpis.score >= 60 ? 'bg-gradient-to-r from-yellow-500 to-orange-500' :
                          'bg-gradient-to-r from-red-500 to-rose-500'
                        }`}
                        style={{ width: `${selectedFile.kpis.score}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-2">
                      <span className="text-amber-400/70 text-sm">0</span>
                      <span className="text-amber-200 font-bold">{selectedFile.kpis.score}/100</span>
                      <span className="text-amber-400/70 text-sm">100</span>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-amber-400/50 py-12">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Select a file to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, gradient }: { icon: React.ReactNode, label: string, value: string, gradient: string }) {
  return (
    <div className="bg-amber-900/20 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center`}>
          <div className="text-amber-950">{icon}</div>
        </div>
        <div>
          <div className="text-amber-400/70 text-xs">{label}</div>
          <div className="text-amber-200 font-bold text-lg">{value}</div>
        </div>
      </div>
    </div>
  )
}

function DetailItem({ label, value, icon }: { label: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="text-amber-400/70">{icon}</div>
        <span className="text-amber-400/70 text-sm">{label}</span>
      </div>
      <span className="text-amber-200 font-medium">{value}</span>
    </div>
  )
}

function KPICard({ label, value, trend, percentage }: { label: string, value: number, trend: 'up' | 'down', percentage: number }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="text-amber-400/70 text-xs">{label}</div>
        <div className="text-amber-200 font-bold">{value}</div>
      </div>
      <div className={`flex items-center gap-1 text-sm ${
        trend === 'up' ? 'text-green-400' : 'text-red-400'
      }`}>
        {trend === 'up' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
        <span>{Math.abs(percentage)}%</span>
      </div>
    </div>
  )
}