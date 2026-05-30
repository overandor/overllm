import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Settings, Play, Square, AlertTriangle, CheckCircle } from 'lucide-react';

export default function SettingsPage() {
  const [status, setStatus] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/status').then(r => r.json()).then(setStatus).catch(() => {});
  }, []);

  const startEngine = async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/engine/start', { method: 'POST' });
      const d = await r.json();
      setMessage(d.message || 'Engine started');
      fetch('/api/status').then(r => r.json()).then(setStatus);
    } catch (e) {
      setMessage('Failed to start engine');
    } finally {
      setLoading(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const stopEngine = async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/engine/stop', { method: 'POST' });
      const d = await r.json();
      setMessage(d.message || 'Engine stopped');
      fetch('/api/status').then(r => r.json()).then(setStatus);
    } catch (e) {
      setMessage('Failed to stop engine');
    } finally {
      setLoading(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const judgePending = async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/judge/pending', { method: 'POST' });
      const d = await r.json();
      setMessage(`Judged ${d.outcomes?.length || 0} predictions`);
    } catch (e) {
      setMessage('Judge failed');
    } finally {
      setLoading(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-emerald-400" />
            Engine Settings
          </h1>
        </div>

        {message && (
          <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${message.includes('Failed') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'}`}>
            {message.includes('Failed') ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
            {message}
          </div>
        )}

        {/* Status */}
        <div className="p-6 rounded-xl bg-gray-900 border border-gray-800 mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">Runtime Status</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 rounded bg-gray-800/50">
              <span className="text-gray-400">Engine Running</span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${status.running ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                {status.running ? 'RUNNING' : 'STOPPED'}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded bg-gray-800/50">
              <span className="text-gray-400">Interval</span>
              <span className="font-mono text-white">{status.interval_seconds}s</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded bg-gray-800/50">
              <span className="text-gray-400">Live Trading</span>
              <span className="px-2 py-1 rounded text-xs font-medium bg-red-500/20 text-red-400">DISABLED</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded bg-gray-800/50">
              <span className="text-gray-400">Policy Epsilon</span>
              <span className="font-mono text-white">{status.policy_epsilon?.toFixed(3)}</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded bg-gray-800/50">
              <span className="text-gray-400">Session Net PnL</span>
              <span className={`font-mono ${status.session_net_bps >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {status.session_net_bps?.toFixed(1)} bps
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded bg-gray-800/50">
              <span className="text-gray-400">Symbols</span>
              <span className="font-mono text-white">{(status.symbols || []).length}</span>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="p-6 rounded-xl bg-gray-900 border border-gray-800 mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">Controls</h3>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={startEngine}
              disabled={loading || status.running}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold transition"
            >
              <Play className="w-4 h-4" />
              Start Engine
            </button>
            <button
              onClick={stopEngine}
              disabled={loading || !status.running}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-red-500 hover:bg-red-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold transition"
            >
              <Square className="w-4 h-4" />
              Stop Engine
            </button>
            <button
              onClick={judgePending}
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-gray-700 hover:border-cyan-500 text-gray-300 transition"
            >
              Judge Pending Now
            </button>
          </div>
        </div>

        {/* Truth Labels */}
        <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4">Truth Labels</h3>
          <div className="grid md:grid-cols-2 gap-3">
            {Object.entries(status.truth_labels || {}).map(([k, v]: [string, any]) => (
              <div key={k} className="flex items-center justify-between p-3 rounded bg-gray-800/50">
                <code className="text-sm text-gray-400">{k}</code>
                <span className="text-sm font-mono text-emerald-400">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
