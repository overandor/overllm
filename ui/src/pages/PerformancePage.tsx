import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, BarChart3, TrendingUp, Target, PieChart } from 'lucide-react';

interface PerfData {
  stats: { total: number; wins: number; losses: number; accuracy: number; total_net_bps: number; avg_net_bps: number };
  accuracy_by_symbol: Record<string, { total: number; wins: number; accuracy: number; avg_net_bps: number }>;
  calibration: { bins: { low: number; high: number; predicted: number; actual: number; count: number }[] };
}

export default function PerformancePage() {
  const [data, setData] = useState<PerfData | null>(null);

  useEffect(() => {
    fetch('/api/performance')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => setData(null));
  }, []);

  const stats = data?.stats || { total: 0, wins: 0, losses: 0, accuracy: 0, total_net_bps: 0, avg_net_bps: 0 };
  const bySymbol = data?.accuracy_by_symbol || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <BarChart3 className="w-7 h-7 text-emerald-400" />
            Performance Analytics
          </h1>
        </div>

        {/* Summary Cards */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total Predictions', value: stats.total, icon: Target },
            { label: 'Win Rate', value: `${(stats.accuracy * 100).toFixed(1)}%`, icon: TrendingUp },
            { label: 'Wins', value: stats.wins, icon: TrendingUp, color: 'text-emerald-400' },
            { label: 'Losses', value: stats.losses, icon: TrendingUp, color: 'text-red-400' },
          ].map((card, i) => (
            <div key={i} className="p-6 rounded-xl bg-gray-900 border border-gray-800">
              <card.icon className={`w-5 h-5 mb-3 ${card.color || 'text-gray-400'}`} />
              <div className="text-2xl font-bold text-white">{card.value}</div>
              <div className="text-sm text-gray-500 mt-1">{card.label}</div>
            </div>
          ))}
        </div>

        {/* PnL */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <h3 className="text-lg font-semibold text-white mb-4">Total Net PnL (bps)</h3>
            <div className={`text-4xl font-bold ${stats.total_net_bps >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {stats.total_net_bps >= 0 ? '+' : ''}{stats.total_net_bps.toFixed(1)}
            </div>
            <p className="text-sm text-gray-500 mt-2">After fees, spread, slippage</p>
          </div>
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <h3 className="text-lg font-semibold text-white mb-4">Average Net Return (bps)</h3>
            <div className={`text-4xl font-bold ${stats.avg_net_bps >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {stats.avg_net_bps >= 0 ? '+' : ''}{stats.avg_net_bps.toFixed(2)}
            </div>
            <p className="text-sm text-gray-500 mt-2">Per prediction average</p>
          </div>
        </div>

        {/* By Symbol */}
        <div className="p-6 rounded-xl bg-gray-900 border border-gray-800 mb-8">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-cyan-400" />
            Accuracy by Symbol
          </h3>
          {Object.keys(bySymbol).length === 0 ? (
            <div className="text-center py-12 text-gray-500">No judged predictions yet.</div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(bySymbol).map(([sym, s]: [string, any]) => (
                <div key={sym} className="p-4 rounded-lg bg-gray-800/50 border border-gray-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono font-semibold text-white">{sym}</span>
                    <span className="text-xs text-gray-500">{s.total} trades</span>
                  </div>
                  <div className="text-2xl font-bold text-emerald-400">{(s.accuracy * 100).toFixed(1)}%</div>
                  <div className="text-sm text-gray-500">avg: {s.avg_net_bps.toFixed(1)} bps</div>
                  <div className="mt-2 h-2 bg-gray-700 rounded overflow-hidden">
                    <div className="h-full bg-emerald-500 transition-all" style={{ width: `${s.accuracy * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Calibration */}
        <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4">Confidence Calibration</h3>
          {(data?.calibration?.bins || []).length === 0 ? (
            <div className="text-center py-12 text-gray-500">Not enough data for calibration.</div>
          ) : (
            <div className="space-y-3">
              {(data?.calibration?.bins || []).map((b: any, i: number) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-24 text-sm text-gray-400">
                    {(b.low * 100).toFixed(0)}% - {(b.high * 100).toFixed(0)}%
                  </div>
                  <div className="flex-1 h-6 bg-gray-800 rounded overflow-hidden relative">
                    <div className="absolute top-0 left-0 h-full bg-blue-500/30 transition-all" style={{ width: `${b.predicted * 100}%` }} />
                    <div className="absolute top-0 left-0 h-full bg-emerald-500/50 transition-all" style={{ width: `${b.actual * 100}%` }} />
                  </div>
                  <div className="w-16 text-right text-sm text-gray-400">n={b.count}</div>
                </div>
              ))}
              <div className="flex items-center gap-4 text-xs text-gray-500 mt-4">
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500/30 rounded" /> Predicted</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-emerald-500/50 rounded" /> Actual</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
