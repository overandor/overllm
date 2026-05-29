import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Brain, Shield, Zap, Globe, Lock, ChevronRight, Activity, TrendingUp, Cpu } from 'lucide-react';

export default function LandingPage() {
  const [stats, setStats] = useState({ predictions: 0, accuracy: 0, kpis: 322, symbols: 0 });

  useEffect(() => {
    fetch('/api/performance').then(r => r.json()).then(d => {
      const s = d.stats || {};
      setStats({
        predictions: s.total || 0,
        accuracy: Math.round((s.accuracy || 0) * 100),
        kpis: 322,
        symbols: Object.keys(d.accuracy_by_symbol || {}).length
      });
    }).catch(() => {});
  }, []);

  const features = [
    { icon: Brain, title: '322 Dynamic KPIs', desc: 'Real-time feature engineering from Gate.io futures tick data' },
    { icon: Zap, title: '3-Minute Judge Loop', desc: 'Self-judging predictions with online Q-learning weight updates' },
    { icon: Shield, title: 'Risk Governor', desc: 'Veto system with spread, volatility, and drawdown guards' },
    { icon: Lock, title: 'Cryptographic Receipts', desc: 'Every prediction and outcome hashed with SHA256' },
    { icon: Activity, title: 'Live Telemetry', desc: 'Real-time tick data ingestion and market state tracking' },
    { icon: TrendingUp, title: 'Paper-Only Mode', desc: 'Live trading hard-disabled. All predictions are public.' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-gray-950 text-white">
      {/* Hero */}
      <section className="relative overflow-hidden px-6 py-20 lg:py-32">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm mb-8">
            <Globe className="w-4 h-4" />
            <span>Live on Gate.io Futures</span>
          </div>
          <h1 className="text-5xl lg:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent">
            OverLLM Alpha Engine
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10">
            A self-judging 3-minute alpha engine that predicts token direction,
            waits, scores itself, and learns online — all visible on a public URL.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/dashboard" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold transition">
              <BarChart3 className="w-5 h-5" />
              Open Dashboard
              <ChevronRight className="w-4 h-4" />
            </Link>
            <Link to="/docs" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-gray-700 hover:border-gray-500 text-gray-300 transition">
              Read Docs
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-gray-800 bg-gray-900/50">
        <div className="max-w-5xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { label: 'Predictions', value: stats.predictions, suffix: '' },
            { label: 'Accuracy', value: stats.accuracy, suffix: '%' },
            { label: 'KPIs Engineered', value: stats.kpis, suffix: '+' },
            { label: 'Symbols', value: stats.symbols, suffix: '' },
          ].map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-3xl font-bold text-emerald-400">{s.value}{s.suffix}</div>
              <div className="text-sm text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">Engine Architecture</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="p-6 rounded-xl bg-gray-800/50 border border-gray-700/50 hover:border-emerald-500/30 transition group">
              <f.icon className="w-8 h-8 text-emerald-400 mb-4 group-hover:scale-110 transition" />
              <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture Diagram */}
      <section className="max-w-5xl mx-auto px-6 py-20 border-t border-gray-800">
        <h2 className="text-3xl font-bold text-center mb-12">Data Flow</h2>
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          {['Gate.io API', '322 KPI Factory', 'Q-Learning Policy', '3-Min Judge', 'Receipt Chain'].map((step, i) => (
            <div key={i} className="flex items-center gap-4">
              <div className="w-32 h-20 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center text-center px-2">
                <span className="text-gray-300">{step}</span>
              </div>
              {i < 4 && <ChevronRight className="w-5 h-5 text-gray-600 hidden md:block" />}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-5xl mx-auto px-6 py-20 text-center border-t border-gray-800">
        <Cpu className="w-12 h-12 text-cyan-400 mx-auto mb-6" />
        <h2 className="text-3xl font-bold mb-4">Transparent by Design</h2>
        <p className="text-gray-400 max-w-xl mx-auto mb-8">
          Every prediction, every outcome, every weight update is public.
          No hidden losses. No deleted trades. Cryptographic receipts for everything.
        </p>
        <Link to="/dashboard" className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-semibold transition">
          <Activity className="w-5 h-5" />
          View Live Engine
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
        OverLLM Project — Self-Judging Alpha Engine — Paper Trading Only
      </footer>
    </div>
  );
}
