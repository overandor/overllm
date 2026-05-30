import { Link } from 'react-router-dom';
import { ArrowLeft, Layers, GitBranch, Cpu, Lock, Globe, Zap, Shield, TrendingUp } from 'lucide-react';

export default function AboutPage() {
  const layers = [
    { icon: Layers, title: 'Layer A: BitNet Proof Kernel', desc: 'Deterministic compute kernel with cryptographic proof generation' },
    { icon: GitBranch, title: 'Layer B: Cognition DAG', desc: 'Directed acyclic graph for reasoning and inference chains' },
    { icon: Cpu, title: 'Layer C: WASM Worker Runtime', desc: 'Browser-based deterministic execution environment' },
    { icon: Zap, title: 'Layer D: Coordinator / Nervous System', desc: 'Central orchestration and agent coordination' },
    { icon: Globe, title: 'Layer E: Semantic Runtime', desc: 'Memory, lineage, and semantic SQL cognition' },
    { icon: Lock, title: 'Layer F: Settlement', desc: 'Escrow, adapters, telemetry, and proof submission' },
  ];

  const principles = [
    { icon: Shield, title: 'Transparency First', desc: 'Every prediction and outcome is public with a SHA256 receipt. No hidden losses.' },
    { icon: TrendingUp, title: 'Self-Judging', desc: 'The engine waits 3 minutes, fetches the exit price, and scores itself. Then it learns.' },
    { icon: Zap, title: 'Online Learning', desc: 'Q-learning weights update after every prediction. The policy adapts in real time.' },
    { icon: Lock, title: 'Paper Only', desc: 'Live trading is hard-disabled. All signals are paper trades visible to anyone.' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="flex items-center gap-4 mb-12">
          <Link to="/" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-4xl font-bold text-white">About OverLLM</h1>
        </div>

        {/* Mission */}
        <section className="mb-16">
          <p className="text-xl text-gray-400 leading-relaxed">
            OverLLM is a self-judging alpha engine for Gate.io futures. It predicts token direction,
            waits exactly 3 minutes, scores the outcome, and updates its Q-learning weights online.
            Every step is public. Every prediction has a cryptographic receipt.
          </p>
        </section>

        {/* Architecture Layers */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6">System Architecture</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {layers.map((l, i) => (
              <div key={i} className="p-5 rounded-xl bg-gray-900 border border-gray-800 hover:border-emerald-500/30 transition">
                <div className="flex items-center gap-3 mb-3">
                  <l.icon className="w-6 h-6 text-emerald-400" />
                  <h3 className="font-semibold text-white">{l.title}</h3>
                </div>
                <p className="text-sm text-gray-400">{l.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Principles */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6">Design Principles</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {principles.map((p, i) => (
              <div key={i} className="p-5 rounded-xl bg-gray-900 border border-gray-800">
                <p.icon className="w-6 h-6 text-cyan-400 mb-3" />
                <h3 className="font-semibold text-white mb-2">{p.title}</h3>
                <p className="text-sm text-gray-400">{p.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Tech Stack */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6">Technology Stack</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: 'Python', role: 'Backend + ML' },
              { name: 'FastAPI', role: 'API Server' },
              { name: 'React', role: 'Dashboard UI' },
              { name: 'TypeScript', role: 'Type-safe frontend' },
              { name: 'Tailwind CSS', role: 'Styling' },
              { name: 'SQLite', role: 'Append-only store' },
              { name: 'NumPy', role: 'Feature engineering' },
              { name: 'Gate.io API', role: 'Market data source' },
            ].map((t, i) => (
              <div key={i} className="p-4 rounded-lg bg-gray-900 border border-gray-800 text-center">
                <div className="font-semibold text-white">{t.name}</div>
                <div className="text-xs text-gray-500 mt-1">{t.role}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Roadmap */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6">Roadmap</h2>
          <div className="space-y-4">
            {[
              { done: true, title: '322 KPI feature engine', desc: 'Dynamic indicator generation from Gate.io tick data' },
              { done: true, title: '3-minute self-judging loop', desc: 'Prediction → wait → judge → learn' },
              { done: true, title: 'Online Q-learning policy', desc: 'Tabular RL with confidence calibration' },
              { done: true, title: 'Cryptographic receipts', desc: 'SHA256 canonical JSON for every prediction' },
              { done: true, title: 'Public dashboard', desc: '9-page React app with live telemetry' },
              { done: false, title: 'WASM worker runtime', desc: 'Browser-based deterministic execution' },
              { done: false, title: 'Semantic SQL cognition', desc: 'Natural language queries over prediction history' },
              { done: false, title: 'Solana settlement', desc: 'On-chain proof submission and verification' },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-4 p-4 rounded-lg bg-gray-900 border border-gray-800">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${item.done ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-800 text-gray-500'}`}>
                  {item.done ? '✓' : '○'}
                </div>
                <div>
                  <div className={`font-medium ${item.done ? 'text-white' : 'text-gray-500'}`}>{item.title}</div>
                  <div className="text-sm text-gray-500">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* License */}
        <section className="text-center py-12 border-t border-gray-800">
          <p className="text-gray-500">MIT / OverLLM Project</p>
          <p className="text-sm text-gray-600 mt-2">Paper trading only. No live trades. Ever.</p>
        </section>
      </div>
    </div>
  );
}
