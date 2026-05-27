import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Activity, Brain, BarChart3, Zap, Globe, Dna } from 'lucide-react'
import ProofHome from './components/ProofHome'
import Dashboard from './components/Dashboard'
import TrainingDashboard from './components/TrainingDashboard'
import LiveTrainingDashboard from './components/LiveTrainingDashboard'
import CrawlerDashboard from './components/CrawlerDashboard'
import OverAgentDashboard from './components/OverAgentDashboard'

function Navigation() {
  const location = useLocation()
  const navItems = [
    { path: '/', label: 'OverLLM', icon: Brain },
    { path: '/dashboard', label: 'Monitor', icon: Activity },
    { path: '/training', label: 'Training', icon: BarChart3 },
    { path: '/live-training', label: 'Live', icon: Zap },
    { path: '/crawler', label: 'Crawler', icon: Globe },
    { path: '/overagent', label: 'OverAgent', icon: Dna },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#060612]/90 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 py-3">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 flex items-center justify-center">
              <Brain className="w-4 h-4 text-emerald-400" />
            </div>
            <span className="text-sm font-bold text-white">OverLLM</span>
          </Link>
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                    active
                      ? 'bg-white/10 text-white border border-white/10'
                      : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-[#060612]">
        <Navigation />
        <Routes>
          <Route path="/" element={<ProofHome />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/training" element={<TrainingDashboard />} />
          <Route path="/live-training" element={<LiveTrainingDashboard />} />
          <Route path="/crawler" element={<CrawlerDashboard />} />
          <Route path="/overagent" element={<OverAgentDashboard />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
