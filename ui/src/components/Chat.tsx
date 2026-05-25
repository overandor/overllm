import React, { useState, useRef, useEffect } from 'react'
import { Send, Plus, MessageSquare, Trash2, Settings, User, Bot } from 'lucide-react'

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

    // Try to call backend API
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:7749'
      const response = await fetch(`${apiUrl}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input })
      })

      if (response.ok) {
        const data = await response.json()
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response || 'No response from backend',
          timestamp: Date.now()
        }
        setSessions(prev => prev.map(session => {
          if (session.id === activeSessionId) {
            return { ...session, messages: [...session.messages, assistantMessage] }
          }
          return session
        }))
      } else {
        throw new Error('Backend not available')
      }
    } catch (error) {
      // Fallback to simulated response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I'm the OverLLM AI assistant. Backend not connected. Configure VITE_API_URL to connect to deployed backend.\n\nI can help you with:\n\n• Vector search and retrieval\n• Model training and optimization\n• Trading data analysis\n• System telemetry\n\nHow can I assist you today?`,
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

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <div className="w-64 bg-gray-950 flex flex-col border-r border-gray-800">
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-white transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          {sessions.map(session => (
            <div
              key={session.id}
              className={`group flex items-center gap-2 px-3 py-3 rounded-lg cursor-pointer transition-colors ${
                activeSessionId === session.id
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
              }`}
              onClick={() => setActiveSessionId(session.id)}
            >
              <MessageSquare className="w-4 h-4 flex-shrink-0" />
              <span className="flex-1 truncate text-sm">{session.title}</span>
              {sessions.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteSession(session.id)
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-700 rounded transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-800">
          <button className="flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-white transition-colors">
            <Settings className="w-5 h-5" />
            <span className="text-sm">Settings</span>
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-14 border-b border-gray-800 flex items-center px-6 bg-gray-900">
          <h1 className="text-white font-semibold">OverLLM</h1>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {activeSession.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Bot className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h2 className="text-xl text-white font-semibold mb-2">OverLLM AI Assistant</h2>
                <p className="text-gray-400">Start a conversation to begin</p>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto py-8 px-4">
              {activeSession.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 mb-6 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-100'
                    }`}
                  >
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content}
                    </div>
                  </div>
                  {message.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5 text-gray-300" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-4 mb-6">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-gray-800 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800 p-4 bg-gray-900">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-center bg-gray-800 rounded-xl border border-gray-700 focus-within:border-gray-600">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="Message OverLLM..."
                className="flex-1 bg-transparent text-white placeholder-gray-500 px-4 py-3 resize-none outline-none text-sm"
                rows={1}
                style={{ minHeight: '48px', maxHeight: '200px' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="m-2 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg transition-colors"
              >
                <Send className="w-5 h-5 text-white" />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              OverLLM can make mistakes. Consider checking important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
