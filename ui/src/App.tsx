import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Landing from './components/Landing'
import Chat from './components/Chat'
import Terminal from './components/Terminal'
import FileExplorer from './components/FileExplorer'
import Dashboard from './components/Dashboard'

function Navigation() {
  const location = useLocation()
  const navItems = [
    { path: '/', label: 'Home', icon: '🏠' },
    { path: '/chat', label: 'AI Chat', icon: '💬' },
    { path: '/terminal', label: 'Terminal', icon: '⚡' },
    { path: '/files', label: 'Files', icon: '📁' },
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-b from-amber-950/90 to-amber-900/80 backdrop-blur-xl border-b border-amber-700/30">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 via-yellow-500 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/30">
              <span className="text-xl">✨</span>
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-amber-200 via-yellow-300 to-amber-400 bg-clip-text text-transparent">
              Devin Terminal
            </h1>
          </div>
          
          <div className="flex items-center gap-2">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ${
                  location.pathname === item.path
                    ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-amber-950 shadow-lg shadow-amber-500/30'
                    : 'text-amber-200/70 hover:text-amber-100 hover:bg-amber-800/30'
                }`}
              >
                <span className="mr-2">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-amber-950 via-amber-900 to-yellow-950">
        <Navigation />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/terminal" element={<Terminal />} />
          <Route path="/files" element={<FileExplorer />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
