import React, { useState } from 'react'
import { Save, RotateCcw, Zap, Cpu, Database } from 'lucide-react'

export default function SettingsPanel() {
  const [settings, setSettings] = useState({
    learningRate: 0.001,
    explorationRate: 0.1,
    batchSize: 32,
    gamma: 0.99,
    mutationRate: 0.01,
    crossoverRate: 0.7,
    populationSize: 50,
    vectorDimension: 128,
    maxCandles: 10000,
  })

  const handleSave = () => {
    console.log('Settings saved:', settings)
    alert('Settings saved successfully!')
  }

  const handleReset = () => {
    setSettings({
      learningRate: 0.001,
      explorationRate: 0.1,
      batchSize: 32,
      gamma: 0.99,
      mutationRate: 0.01,
      crossoverRate: 0.7,
      populationSize: 50,
      vectorDimension: 128,
      maxCandles: 10000,
    })
  }

  const SettingRow = ({ label, value, onChange, min, max, step, icon: Icon }: any) => (
    <div className="flex items-center gap-4 p-3 bg-neu-bg rounded-neu-sm">
      <Icon className="w-5 h-5 text-neu-accent" />
      <span className="flex-1 text-sm text-gray-700">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="neu-input w-24 text-right"
      />
    </div>
  )

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">Settings</h2>
      
      {/* RL Settings */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5" />
          Reinforcement Learning
        </h3>
        <div className="space-y-3">
          <SettingRow
            label="Learning Rate"
            value={settings.learningRate}
            onChange={(v) => setSettings({...settings, learningRate: v})}
            min={0.0001}
            max={0.1}
            step={0.0001}
            icon={Zap}
          />
          <SettingRow
            label="Exploration Rate (Epsilon)"
            value={settings.explorationRate}
            onChange={(v) => setSettings({...settings, explorationRate: v})}
            min={0}
            max={1}
            step={0.01}
            icon={Zap}
          />
          <SettingRow
            label="Batch Size"
            value={settings.batchSize}
            onChange={(v) => setSettings({...settings, batchSize: v})}
            min={1}
            max={256}
            step={1}
            icon={Database}
          />
          <SettingRow
            label="Gamma (Discount Factor)"
            value={settings.gamma}
            onChange={(v) => setSettings({...settings, gamma: v})}
            min={0}
            max={1}
            step={0.01}
            icon={Zap}
          />
        </div>
      </div>

      {/* GA Settings */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5" />
          Genetic Algorithm
        </h3>
        <div className="space-y-3">
          <SettingRow
            label="Mutation Rate"
            value={settings.mutationRate}
            onChange={(v) => setSettings({...settings, mutationRate: v})}
            min={0}
            max={1}
            step={0.001}
            icon={Cpu}
          />
          <SettingRow
            label="Crossover Rate"
            value={settings.crossoverRate}
            onChange={(v) => setSettings({...settings, crossoverRate: v})}
            min={0}
            max={1}
            step={0.01}
            icon={Cpu}
          />
          <SettingRow
            label="Population Size"
            value={settings.populationSize}
            onChange={(v) => setSettings({...settings, populationSize: v})}
            min={10}
            max={200}
            step={1}
            icon={Database}
          />
        </div>
      </div>

      {/* Vector Search Settings */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Database className="w-5 h-5" />
          Vector Search
        </h3>
        <div className="space-y-3">
          <SettingRow
            label="Vector Dimension"
            value={settings.vectorDimension}
            onChange={(v) => setSettings({...settings, vectorDimension: v})}
            min={32}
            max={1024}
            step={32}
            icon={Database}
          />
          <SettingRow
            label="Max Candles Stored"
            value={settings.maxCandles}
            onChange={(v) => setSettings({...settings, maxCandles: v})}
            min={1000}
            max={100000}
            step={1000}
            icon={Database}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="neu-card">
        <div className="flex gap-4">
          <button onClick={handleSave} className="neu-button flex items-center gap-2">
            <Save className="w-5 h-5" />
            Save Settings
          </button>
          <button onClick={handleReset} className="neu-button flex items-center gap-2">
            <RotateCcw className="w-5 h-5" />
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  )
}
