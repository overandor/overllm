import React, { useState, useRef, useEffect } from 'react'
import { Terminal as TerminalIcon, Send, Command, Play, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'

interface TerminalCommand {
  id: string
  command: string
  output: string
  status: 'pending' | 'running' | 'success' | 'error'
  timestamp: number
  duration?: number
}

export default function Terminal() {
  const [commands, setCommands] = useState<TerminalCommand[]>([])
  const [input, setInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const terminalRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [commands])

  const executeCommand = async (cmd: string) => {
    const newCommand: TerminalCommand = {
      id: Date.now().toString(),
      command: cmd,
      output: '',
      status: 'pending',
      timestamp: Date.now()
    }

    setCommands(prev => [...prev, newCommand])
    setIsProcessing(true)

    // Update to running
    setTimeout(() => {
      setCommands(prev => prev.map(c => 
        c.id === newCommand.id ? { ...c, status: 'running' } : c
      ))
    }, 100)

    try {
      const startTime = Date.now()
      const response = await fetch('/api/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      })

      const duration = Date.now() - startTime
      const data = await response.json()

      setCommands(prev => prev.map(c => 
        c.id === newCommand.id ? { 
          ...c, 
          output: data.output || data.error || 'Command executed',
          status: data.success ? 'success' : 'error',
          duration 
        } : c
      ))
    } catch (error) {
      setCommands(prev => prev.map(c => 
        c.id === newCommand.id ? { 
          ...c, 
          output: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          status: 'error' 
        } : c
      ))
    } finally {
      setIsProcessing(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isProcessing) return
    executeCommand(input)
    setInput('')
  }

  const suggestedCommands = [
    'ls -la',
    'pwd',
    'npm install',
    'git status',
    'cargo build',
    'python script.py',
    'docker ps',
    'kubectl get pods'
  ]

  return (
    <div className="pt-24 min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center shadow-lg shadow-amber-500/30">
              <TerminalIcon className="w-6 h-6 text-amber-950" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-amber-200">AI Terminal</h1>
              <p className="text-amber-400/70 text-sm">Execute commands with natural language processing</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCommands([])}
              className="px-4 py-2 rounded-xl bg-amber-800/30 border border-amber-600/50 text-amber-200 text-sm hover:bg-amber-800/50 transition-all"
            >
              Clear History
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Terminal Window */}
          <div className="lg:col-span-3 bg-amber-950/50 backdrop-blur-xl rounded-2xl border border-amber-700/30 overflow-hidden">
            {/* Terminal Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-amber-900/30 border-b border-amber-700/30">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <div className="text-amber-400/70 text-sm font-mono">devin-terminal</div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400/70" />
                <span className="text-amber-400/70 text-sm">{new Date().toLocaleTimeString()}</span>
              </div>
            </div>

            {/* Terminal Output */}
            <div 
              ref={terminalRef}
              className="h-[500px] overflow-y-auto p-4 font-mono text-sm space-y-2"
            >
              {commands.length === 0 && (
                <div className="text-amber-400/50 text-center py-20">
                  <TerminalIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No commands executed yet</p>
                  <p className="text-sm mt-2">Type a command below or use AI assistance</p>
                </div>
              )}

              {commands.map((cmd) => (
                <div key={cmd.id} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-amber-400">$</span>
                    <span className="text-amber-200">{cmd.command}</span>
                    {cmd.status === 'running' && (
                      <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                    )}
                    {cmd.status === 'success' && (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    )}
                    {cmd.status === 'error' && (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    {cmd.duration && (
                      <span className="text-amber-400/50 text-xs ml-auto">
                        {cmd.duration}ms
                      </span>
                    )}
                  </div>
                  {cmd.output && (
                    <div className={`ml-4 whitespace-pre-wrap ${
                      cmd.status === 'error' ? 'text-red-400' : 'text-amber-300/80'
                    }`}>
                      {cmd.output}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Terminal Input */}
            <div className="p-4 border-t border-amber-700/30">
              <form onSubmit={handleSubmit} className="flex items-center gap-3">
                <span className="text-amber-400 font-mono">$</span>
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Enter command or describe task in natural language..."
                  className="flex-1 bg-amber-900/30 border border-amber-700/50 rounded-xl px-4 py-3 text-amber-200 placeholder-amber-400/50 focus:outline-none focus:border-amber-500/50 font-mono"
                  disabled={isProcessing}
                />
                <button
                  type="submit"
                  disabled={isProcessing || !input.trim()}
                  className="px-4 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 text-amber-950 font-bold hover:shadow-lg hover:shadow-amber-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isProcessing ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* AI Assistant */}
            <div className="bg-amber-900/20 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Command className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-bold text-amber-200">AI Assistant</h3>
              </div>
              <p className="text-amber-300/70 text-sm mb-4">
                Describe what you want to do in natural language, and AI will convert it to terminal commands.
              </p>
              <div className="space-y-2">
                <div className="text-amber-400/50 text-xs font-semibold mb-2">EXAMPLES:</div>
                {[
                  'List all files in current directory',
                  'Install all dependencies',
                  'Check git status',
                  'Build the project'
                ].map((example, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(example)}
                    className="w-full text-left px-3 py-2 rounded-lg bg-amber-800/30 border border-amber-700/30 text-amber-300/80 text-sm hover:bg-amber-800/50 transition-all"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Commands */}
            <div className="bg-amber-900/20 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Play className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-bold text-amber-200">Quick Commands</h3>
              </div>
              <div className="space-y-2">
                {suggestedCommands.map((cmd, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(cmd)}
                    className="w-full text-left px-3 py-2 rounded-lg bg-amber-800/30 border border-amber-700/30 text-amber-300/80 text-sm font-mono hover:bg-amber-800/50 transition-all"
                  >
                    {cmd}
                  </button>
                ))}
              </div>
            </div>

            {/* Stats */}
            <div className="bg-amber-900/20 backdrop-blur-xl rounded-2xl border border-amber-700/30 p-6">
              <h3 className="text-lg font-bold text-amber-200 mb-4">Session Stats</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-amber-400/70">Commands Executed</span>
                  <span className="text-amber-200 font-bold">{commands.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-amber-400/70">Successful</span>
                  <span className="text-green-400 font-bold">
                    {commands.filter(c => c.status === 'success').length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-amber-400/70">Failed</span>
                  <span className="text-red-400 font-bold">
                    {commands.filter(c => c.status === 'error').length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-amber-400/70">Avg Duration</span>
                  <span className="text-amber-200 font-bold">
                    {commands.length > 0 
                      ? `${Math.round(commands.reduce((acc, c) => acc + (c.duration || 0), 0) / commands.length)}ms`
                      : 'N/A'
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}