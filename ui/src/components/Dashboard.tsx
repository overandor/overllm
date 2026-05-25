import React, { useState, useEffect } from 'react'
import { Activity, Cpu, MemoryStick, Zap, TrendingUp } from 'lucide-react'

interface SystemStats {
  cpu_usage: number
  memory_usage: number
  active_connections: number
  inference_count: number
  training_loss: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<SystemStats>({
    cpu_usage: 0,
    memory_usage: 0,
    active_connections: 0,
    inference_count: 0,
    training_loss: 0,
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('http://localhost:7749/api/status')
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

  const StatCard = ({ icon: Icon, label, value, unit }: any) => (
    <div className="neu-card flex-1">
      <div className="flex items-center gap-3 mb-2">
        <Icon className="w-6 h-6 text-neu-accent" />
        <span className="text-sm text-gray-600">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-800">
        {value} <span className="text-sm font-normal text-gray-600">{unit}</span>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">System Dashboard</h2>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard icon={Cpu} label="CPU Usage" value={stats.cpu_usage.toFixed(1)} unit="%" />
        <StatCard icon={MemoryStick} label="Memory" value={stats.memory_usage.toFixed(1)} unit="%" />
        <StatCard icon={Activity} label="Connections" value={stats.active_connections} unit="" />
        <StatCard icon={Zap} label="Inferences" value={stats.inference_count} unit="" />
        <StatCard icon={TrendingUp} label="Training Loss" value={stats.training_loss.toFixed(4)} unit="" />
      </div>

      {/* Activity Log */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Recent Activity</h3>
        <div className="space-y-2">
          <div className="flex items-center gap-3 p-3 bg-neu-bg rounded-neu-sm">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-sm text-gray-700">Model training completed - Epoch 10</span>
            <span className="text-xs text-gray-500 ml-auto">2 min ago</span>
          </div>
          <div className="flex items-center gap-3 p-3 bg-neu-bg rounded-neu-sm">
            <div className="w-2 h-2 bg-blue-500 rounded-full" />
            <span className="text-sm text-gray-700">New trading data received - 1s candles</span>
            <span className="text-xs text-gray-500 ml-auto">5 min ago</span>
          </div>
          <div className="flex items-center gap-3 p-3 bg-neu-bg rounded-neu-sm">
            <div className="w-2 h-2 bg-purple-500 rounded-full" />
            <span className="text-sm text-gray-700">Vector index updated - 1,234 vectors</span>
            <span className="text-xs text-gray-500 ml-auto">10 min ago</span>
          </div>
          <div className="flex items-center gap-3 p-3 bg-neu-bg rounded-neu-sm">
            <div className="w-2 h-2 bg-orange-500 rounded-full" />
            <span className="text-sm text-gray-700">Genetic algorithm evolved - Generation 50</span>
            <span className="text-xs text-gray-500 ml-auto">15 min ago</span>
          </div>
        </div>
      </div>

      {/* Model Performance */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Model Performance</h3>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Token Selection Accuracy</span>
              <span>87.5%</span>
            </div>
            <div className="h-3 bg-neu-bg rounded-neu-sm overflow-hidden">
              <div className="h-full bg-neu-accent rounded-neu-sm" style={{ width: '87.5%' }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>RL Reward Rate</span>
              <span>+0.023/step</span>
            </div>
            <div className="h-3 bg-neu-bg rounded-neu-sm overflow-hidden">
              <div className="h-full bg-green-500 rounded-neu-sm" style={{ width: '65%' }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>GA Fitness Score</span>
              <span>0.912</span>
            </div>
            <div className="h-3 bg-neu-bg rounded-neu-sm overflow-hidden">
              <div className="h-full bg-blue-500 rounded-neu-sm" style={{ width: '91.2%' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
