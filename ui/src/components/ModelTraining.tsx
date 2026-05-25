import React, { useState } from 'react'
import { Play, Pause, RotateCcw, TrendingUp } from 'lucide-react'

export default function ModelTraining() {
  const [isTraining, setIsTraining] = useState(false)
  const [epoch, setEpoch] = useState(0)
  const [loss, setLoss] = useState(0.5)
  const [reward, setReward] = useState(0.1)

  const startTraining = () => setIsTraining(true)
  const stopTraining = () => setIsTraining(false)
  const resetTraining = () => {
    setIsTraining(false)
    setEpoch(0)
    setLoss(0.5)
    setReward(0.1)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Model Training</h2>
      
      {/* Training Controls */}
      <div className="neu-card">
        <div className="flex items-center gap-4">
          <button
            onClick={isTraining ? stopTraining : startTraining}
            className="neu-button flex items-center gap-2"
          >
            {isTraining ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            {isTraining ? 'Pause Training' : 'Start Training'}
          </button>
          <button onClick={resetTraining} className="neu-button flex items-center gap-2">
            <RotateCcw className="w-5 h-5" />
            Reset
          </button>
        </div>
      </div>

      {/* Training Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">Current Epoch</h3>
          <div className="text-3xl font-bold text-neu-accent">{epoch}</div>
        </div>
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">Training Loss</h3>
          <div className="text-3xl font-bold text-orange-500">{loss.toFixed(4)}</div>
        </div>
        <div className="neu-card">
          <h3 className="text-sm text-gray-600 mb-2">RL Reward</h3>
          <div className="text-3xl font-bold text-green-500">{reward.toFixed(3)}</div>
        </div>
      </div>

      {/* Training Progress */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Training Progress</h3>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>DPO Training</span>
              <span>{epoch}/100 epochs</span>
            </div>
            <div className="h-3 bg-neu-bg rounded-neu-sm overflow-hidden">
              <div className="h-full bg-neu-accent rounded-neu-sm transition-all" style={{ width: `${epoch}%` }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>RL Mistake Learning</span>
              <span>Active</span>
            </div>
            <div className="h-3 bg-neu-bg rounded-neu-sm overflow-hidden">
              <div className="h-full bg-green-500 rounded-neu-sm" style={{ width: '75%' }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Genetic Algorithm</span>
              <span>Generation 50</span>
            </div>
            <div className="h-3 bg-neu-bg rounded-neu-sm overflow-hidden">
              <div className="h-full bg-blue-500 rounded-neu-sm" style={{ width: '50%' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Token Selection Optimization */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Token Selection Optimization</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-600 mb-1">Exploration Rate</div>
            <div className="text-xl font-bold text-gray-800">0.05</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 mb-1">Learning Rate</div>
            <div className="text-xl font-bold text-gray-800">0.001</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 mb-1">Best Token Confidence</div>
            <div className="text-xl font-bold text-green-500">0.92</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 mb-1">Avg Token Confidence</div>
            <div className="text-xl font-bold text-blue-500">0.78</div>
          </div>
        </div>
      </div>
    </div>
  )
}
