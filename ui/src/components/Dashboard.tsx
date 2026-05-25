import React, { useState, useEffect } from 'react'
import { Activity, Cpu, MemoryStick, Zap, TrendingUp, Terminal, FileCode, Clock, CheckCircle, AlertTriangle } from 'lucide-react'

interface SystemStats {
  cpu_usage: number
  memory_usage: number
  active_connections: number
  inference_count: number
  training_loss: number
}

interface ActivityItem {
  id: string
  type: 'success' | 'info' | 'warning' | 'error'
  message: string
  timestamp: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<SystemStats>({
    cpu_usage: 45.2,
    memory_usage: 62.8,
    active_connections: 12,
    inference_count: 1234,
    training_loss: 0.0234,
  })

  const [activities, setActivities] = useState<ActivityItem[]>([
    { id: '1', type: 'success', message: 'Model training completed - Epoch 10', timestamp: Date.now() - 120000 },
    { id: '2', type: 'info', message: 'New trading data received - 1s candles', timestamp: Date.now() - 300000 },
    { id: '3', type: 'success', message: 'Vector index updated - 1,234 vectors', timestamp: Date.now() - 600000 },
    { id: '4', type: 'warning', message: 'Genetic algorithm evolved - Generation 50', timestamp: Date.now() - 900000 },
  ])

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/status')
        const data = await response.json()
        setStats(data)
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 2000)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (timestamp: number) => {
    const diff = Math.floor((Date.now() - timestamp) / 1000)
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return `${Math.floor(diff / 3600)}h ago`
  }

  const StatCard = ({ icon: Icon, label, value, unit, gradient }: { 
    icon: React.ElementType, 
    label: string, 
    value: string | number, 
    unit: string,
    gradient: string 
  }) => (
    <div className="bg-amber-900/20 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6 hover:border-amber-500/50 transition-all duration-300 hover:scale-105">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg`}>
          <Icon className="w-6 h-6 text-amber-950" />
        </div>
        <TrendingUp className="w-5 h-5 text-amber-400/50" />
      </div>
      <div className="text-3xl font-bold text-amber-200 mb-1">{value}<span className="text-lg text-amber-400/70 ml-1">{unit}</span></div>
      <div className="text-sm text-amber-400/70">{label}</div>
    </div>
  )

  const ActivityIcon = ({ type }: { type: ActivityItem['type'] }) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-red-400" />
      default:
        return <Activity className="w-4 h-4 text-blue-400" />
    }
  }

  return (
    <div className="pt-24 min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center shadow-lg shadow-amber-500/30">
            <Activity className="w-6 h-6 text-amber-950" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-amber-200">System Dashboard</h1>
            <p className="text-amber-400/70 text-sm">Real-time monitoring and performance metrics</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <StatCard icon={Cpu} label="CPU Usage" value={stats.cpu_usage.toFixed(1)} unit="%" gradient="from-amber-500 to-yellow-500" />
          <StatCard icon={MemoryStick} label="Memory" value={stats.memory_usage.toFixed(1)} unit="%" gradient="from-amber-400 to-orange-500" />
          <StatCard icon={Activity} label="Connections" value={stats.active_connections} unit="" gradient="from-yellow-500 to-amber-600" />
          <StatCard icon={Zap} label="Inferences" value={stats.inference_count} unit="" gradient="from-amber-600 to-yellow-500" />
          <StatCard icon={TrendingUp} label="Training Loss" value={stats.training_loss.toFixed(4)} unit="" gradient="from-orange-500 to-amber-500" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Activity Log */}
          <div className="bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
            <h3 className="text-xl font-bold text-amber-200 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Recent Activity
            </h3>
            <div className="space-y-3">
              {activities.map((activity) => (
                <div key={activity.id} className="flex items-center gap-3 p-3 bg-amber-900/30 rounded-xl border border-amber-700/30">
                  <ActivityIcon type={activity.type} />
                  <span className="flex-1 text-amber-200 text-sm">{activity.message}</span>
                  <span className="text-amber-400/50 text-xs">{formatTime(activity.timestamp)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Model Performance */}
          <div className="bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
            <h3 className="text-xl font-bold text-amber-200 mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Model Performance
            </h3>
            <div className="space-y-4">
              <PerformanceBar label="Token Selection Accuracy" value={87.5} gradient="from-amber-500 to-yellow-500" />
              <PerformanceBar label="RL Reward Rate" value={65} gradient="from-green-500 to-emerald-500" />
              <PerformanceBar label="GA Fitness Score" value={91.2} gradient="from-blue-500 to-cyan-500" />
              <PerformanceBar label="Memory Efficiency" value={78.3} gradient="from-purple-500 to-pink-500" />
            </div>
          </div>
        </div>

        {/* Terminal Stats */}
        <div className="mt-6 bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
          <h3 className="text-xl font-bold text-amber-200 mb-4 flex items-center gap-2">
            <Terminal className="w-5 h-5" />
            Terminal Statistics
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Commands Today</div>
              <div className="text-2xl font-bold text-amber-200">247</div>
            </div>
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Success Rate</div>
              <div className="text-2xl font-bold text-green-400">94.2%</div>
            </div>
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Avg Execution Time</div>
              <div className="text-2xl font-bold text-amber-200">1.2s</div>
            </div>
          </div>
        </div>

        {/* File Operations */}
        <div className="mt-6 bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
          <h3 className="text-xl font-bold text-amber-200 mb-4 flex items-center gap-2">
            <FileCode className="w-5 h-5" />
            File Operations
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Files Analyzed</div>
              <div className="text-2xl font-bold text-amber-200">1,847</div>
            </div>
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Total Appraisal</div>
              <div className="text-2xl font-bold text-amber-200">$12.4K</div>
            </div>
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Avg Score</div>
              <div className="text-2xl font-bold text-amber-200">82.5</div>
            </div>
            <div className="bg-amber-900/30 rounded-xl p-4 border border-amber-700/30">
              <div className="text-amber-400/70 text-sm mb-1">Hourly Changes</div>
              <div className="text-2xl font-bold text-amber-200">156</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function PerformanceBar({ label, value, gradient }: { label: string, value: number, gradient: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-2">
        <span className="text-amber-300/80">{label}</span>
        <span className="text-amber-200 font-bold">{value}%</span>
      </div>
      <div className="h-3 bg-amber-900/50 rounded-full overflow-hidden">
        <div 
          className={`h-full bg-gradient-to-r ${gradient} rounded-full transition-all duration-500`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}
