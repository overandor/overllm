import React, { useState, useRef, useEffect } from 'react'
import { Send, Plus, MessageSquare, Trash2, Settings, User, Bot, Sparkles, Terminal, FileCode, Zap } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface ChatSession {
  id: string
  title: string
  messages: Message[]
}

export default function Chat() {
  const [sessions, setSessions] = useState<ChatSession[]>([
    {
      id: '1',
      title: 'New Chat',
      messages: []
    }
  ])
  const [activeSessionId, setActiveSessionId] = useState('1')
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [activeSession?.messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now()
    }

    const updatedSessions = sessions.map(session => {
      if (session.id === activeSessionId) {
        const newMessages = [...session.messages, userMessage]
        const title = session.messages.length === 0 
          ? input.slice(0, 30) + (input.length > 30 ? '...' : '')
          : session.title
        return { ...session, messages: newMessages, title }
      }
      return session
    })

    setSessions(updatedSessions)
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input })
      })

      if (response.ok) {
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        let fullResponse = ''

        if (reader) {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            fullResponse += decoder.decode(value)
          }
        }

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: fullResponse || 'No response from AI',
          timestamp: Date.now()
        }
        setSessions(prev => prev.map(session => {
          if (session.id === activeSessionId) {
            return { ...session, messages: [...session.messages, assistantMessage] }
          }
          return session
        }))
      } else {
        throw new Error('API not available')
      }
    } catch (error) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I'm the Devin AI assistant. I can help you with:\n\n• **Terminal Commands**: Execute shell commands and automate tasks\n• **File Operations**: Explore, analyze, and manage your files\n• **Code Analysis**: Understand codebases and suggest improvements\n• **Task Automation**: Break down complex tasks into executable steps\n• **Programming**: Write, debug, and optimize code\n\nTry asking me to:\n- "List all files in the current directory"\n- "Analyze the project structure"\n- "Help me build a React component"\n- "Debug this error"`,
        timestamp: Date.now()
      }
      setSessions(prev => prev.map(session => {
        if (session.id === activeSessionId) {
          return { ...session, messages: [...session.messages, assistantMessage] }
        }
        return session
      }))
    }
    setIsLoading(false)
  }

  const handleNewChat = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: 'New Chat',
      messages: []
    }
    setSessions([...sessions, newSession])
    setActiveSessionId(newSession.id)
  }

  const handleDeleteSession = (sessionId: string) => {
    if (sessions.length === 1) return
    const filtered = sessions.filter(s => s.id !== sessionId)
    setSessions(filtered)
    if (activeSessionId === sessionId) {
      setActiveSessionId(filtered[0].id)
    }
  }

  const quickActions = [
    { icon: <Terminal className="w-4 h-4" />, label: 'Run Command', prompt: 'Help me run a terminal command to...' },
    { icon: <FileCode className="w-4 h-4" />, label: 'Analyze Code', prompt: 'Analyze the code in...' },
    { icon: <Zap className="w-4 h-4" />, label: 'Automate Task', prompt: 'Automate the task of...' },
  ]

  return (
    <div className="flex h-[calc(100vh-96px)] relative z-10">
      {/* Glassmorphic Sidebar */}
      <div className="w-72 bg-amber-950/30 backdrop-blur-xl border-r border-amber-700/30 flex flex-col">
        <div className="p-6">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 rounded-2xl text-amber-950 font-bold transition-all duration-300 shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40"
          >
            <Plus className="w-5 h-5" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 space-y-2">
          {sessions.map(session => (
            <div
              key={session.id}
              className={`group flex items-center gap-3 px-4 py-3 rounded-2xl cursor-pointer transition-all duration-300 ${
                activeSessionId === session.id
                  ? 'bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-500/30'
                  : 'text-amber-300/70 hover:bg-amber-900/30 hover:text-amber-200'
              }`}
              onClick={() => setActiveSessionId(session.id)}
            >
              <MessageSquare className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1 truncate text-sm font-medium">{session.title}</span>
              {sessions.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteSession(session.id)
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-amber-800/50 rounded-xl transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-amber-700/30">
          <button className="w-full flex items-center justify-center gap-2 px-4 py-3 text-amber-300/70 hover:text-amber-200 hover:bg-amber-900/30 rounded-2xl transition-all duration-300">
            <Settings className="w-5 h-5" />
            <span className="text-sm font-medium">Settings</span>
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {activeSession.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center mx-auto mb-6 shadow-2xl shadow-amber-500/25">
                  <Sparkles className="w-10 h-10 text-amber-950" />
                </div>
                <h2 className="text-2xl font-bold text-amber-200 mb-2">Devin AI Assistant</h2>
                <p className="text-amber-400/70 mb-6">Your AI-powered development companion</p>
                
                <div className="flex flex-wrap justify-center gap-3">
                  {quickActions.map((action, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(action.prompt)}
                      className="flex items-center gap-2 px-4 py-3 bg-amber-900/30 border border-amber-700/50 rounded-xl text-amber-300/80 hover:bg-amber-900/50 hover:text-amber-200 transition-all"
                    >
                      {action.icon}
                      <span className="text-sm">{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto py-8 px-6">
              {activeSession.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 mb-8 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-500/25">
                      <Bot className="w-6 h-6 text-amber-950" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] rounded-3xl px-6 py-4 shadow-xl ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-amber-950'
                        : 'bg-amber-900/30 backdrop-blur-xl border border-amber-700/30 text-amber-100'
                    }`}
                  >
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content}
                    </div>
                  </div>
                  {message.role === 'user' && (
                    <div className="w-10 h-10 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/10 flex items-center justify-center flex-shrink-0">
                      <User className="w-6 h-6 text-gray-300" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-4 mb-8">
                  <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-500/25">
                    <Bot className="w-6 h-6 text-amber-950" />
                  </div>
                  <div className="bg-amber-900/30 backdrop-blur-xl border border-amber-700/30 rounded-3xl px-6 py-4">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-6 bg-amber-950/30 backdrop-blur-xl border-t border-amber-700/30">
          <div className="max-w-4xl mx-auto">
            <div className="relative flex items-center bg-amber-900/30 backdrop-blur-xl rounded-3xl border border-amber-700/50 focus-within:border-amber-500/50 transition-all duration-300">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="Message Devin AI..."
                className="flex-1 bg-transparent text-amber-100 placeholder-amber-400/50 px-6 py-4 resize-none outline-none text-sm"
                rows={1}
                style={{ minHeight: '56px', maxHeight: '200px' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="m-2 p-3 bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-600 hover:to-yellow-600 disabled:from-amber-800 disabled:to-amber-800 disabled:opacity-50 rounded-2xl transition-all duration-300 shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40"
              >
                <Send className="w-5 h-5 text-amber-950" />
              </button>
            </div>
            <p className="text-xs text-amber-400/50 mt-3 text-center">
              Devin AI can make mistakes. Consider checking important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
