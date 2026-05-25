import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Activity, Clock } from 'lucide-react'

interface Candle {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export default function TradingView() {
  const [candles1s, setCandles1s] = useState<Candle[]>([])
  const [candles1m, setCandles1m] = useState<Candle[]>([])
  const [isSimulating, setIsSimulating] = useState(false)

  const startSimulation = () => setIsSimulating(true)
  const stopSimulation = () => setIsSimulating(false)

  useEffect(() => {
    if (!isSimulating) return

    const interval = setInterval(() => {
      const now = Date.now()
      const basePrice = 50000 + Math.random() * 1000
      const newCandle: Candle = {
        timestamp: now,
        open: basePrice,
        high: basePrice + Math.random() * 100,
        low: basePrice - Math.random() * 100,
        close: basePrice + (Math.random() - 0.5) * 50,
        volume: Math.random() * 10,
      }

      setCandles1s(prev => [...prev.slice(-99), newCandle])
      if (now % 60000 < 1000) {
        setCandles1m(prev => [...prev.slice(-59), newCandle])
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [isSimulating])

  const CandleRow = ({ candle, isUp }: { candle: Candle, isUp: boolean }) => (
    <div className="flex items-center gap-4 p-2 bg-neu-bg rounded-neu-sm">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isUp ? 'bg-green-500' : 'bg-red-500'}`}>
        {isUp ? <TrendingUp className="w-4 h-4 text-white" /> : <TrendingDown className="w-4 h-4 text-white" />}
      </div>
      <div className="flex-1 grid grid-cols-5 gap-2 text-sm">
        <div className="text-gray-600">{new Date(candle.timestamp).toLocaleTimeString()}</div>
        <div className="text-gray-800">{candle.open.toFixed(2)}</div>
        <div className="text-gray-800">{candle.high.toFixed(2)}</div>
        <div className="text-gray-800">{candle.low.toFixed(2)}</div>
        <div className="text-gray-800">{candle.close.toFixed(2)}</div>
      </div>
      <div className="text-sm text-gray-600">{candle.volume.toFixed(2)}</div>
    </div>
  )

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Trading Data</h2>
      
      {/* Controls */}
      <div className="neu-card">
        <div className="flex items-center gap-4">
          <button
            onClick={isSimulating ? stopSimulation : startSimulation}
            className="neu-button flex items-center gap-2"
          >
            <Activity className="w-5 h-5" />
            {isSimulating ? 'Stop Simulation' : 'Start Simulation'}
          </button>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Clock className="w-4 h-4" />
            <span>Real-time 1s & 1m candles</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">1s Candles</h3>
          <div className="text-2xl font-bold text-neu-accent">{candles1s.length}</div>
        </div>
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">1m Candles</h3>
          <div className="text-2xl font-bold text-blue-500">{candles1m.length}</div>
        </div>
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">Latest Price</h3>
          <div className="text-2xl font-bold text-green-500">
            {candles1s.length > 0 ? candles1s[candles1s.length - 1].close.toFixed(2) : '0.00'}
          </div>
        </div>
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">Volume (24h)</h3>
          <div className="text-2xl font-bold text-orange-500">
            {candles1s.reduce((sum, c) => sum + c.volume, 0).toFixed(2)}
          </div>
        </div>
      </div>

      {/* 1-Second Candles */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">1-Second Candles (Last 100)</h3>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {candles1s.length === 0 ? (
            <div className="text-center text-gray-500 py-8">Start simulation to see data</div>
          ) : (
            candles1s.map((candle, i) => (
              <CandleRow key={i} candle={candle} isUp={candle.close >= candle.open} />
            ))
          )}
        </div>
      </div>

      {/* 1-Minute Candles */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">1-Minute Candles (Last 60)</h3>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {candles1m.length === 0 ? (
            <div className="text-center text-gray-500 py-8">Start simulation to see data</div>
          ) : (
            candles1m.map((candle, i) => (
              <CandleRow key={i} candle={candle} isUp={candle.close >= candle.open} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
