import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Clock, TrendingUp, TrendingDown, Filter, Search } from 'lucide-react';

interface Prediction {
  prediction_id: string;
  symbol: string;
  side: string;
  confidence: number;
  reference_price: number;
  created_at: string;
  status: string;
  outcome?: string;
  net_return_bps?: number;
}

export default function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/predictions/history?limit=200')
      .then(r => r.json())
      .then(d => setPredictions(d.predictions || []))
      .catch(() => setPredictions([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = predictions.filter(p => {
    if (filter !== 'all' && p.side !== filter) return false;
    if (search && !p.symbol.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const sideColor = (side: string) => {
    if (side === 'LONG' || side === 'PREPARE_LONG') return 'text-emerald-400';
    if (side === 'SHORT' || side === 'PREPARE_SHORT') return 'text-red-400';
    return 'text-gray-400';
  };

  const outcomeBadge = (outcome?: string) => {
    if (!outcome) return <span className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-400">PENDING</span>;
    if (outcome === 'WIN' || outcome === 'PREPARE_WIN') return <span className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-400">{outcome}</span>;
    if (outcome === 'LOSS' || outcome === 'PREPARE_LOSS') return <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400">{outcome}</span>;
    return <span className="text-xs px-2 py-1 rounded bg-gray-600 text-gray-300">{outcome}</span>;
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <TrendingUp className="w-7 h-7 text-emerald-400" />
            Predictions History
          </h1>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search symbol..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-gray-900 border border-gray-800 text-white placeholder-gray-500 focus:border-emerald-500 outline-none"
            />
          </div>
          <div className="flex gap-2">
            {['all', 'LONG', 'SHORT', 'PREPARE_LONG', 'PREPARE_SHORT'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition ${filter === f ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-gray-900 border border-gray-800 text-gray-400 hover:border-gray-600'}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="text-center py-20 text-gray-500">Loading predictions...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-3 px-4">Time</th>
                  <th className="text-left py-3 px-4">Symbol</th>
                  <th className="text-left py-3 px-4">Side</th>
                  <th className="text-left py-3 px-4">Confidence</th>
                  <th className="text-left py-3 px-4">Entry Price</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Outcome</th>
                  <th className="text-right py-3 px-4">Net BPS</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.prediction_id} className="border-b border-gray-800/50 hover:bg-gray-900/50 transition">
                    <td className="py-3 px-4 text-gray-400 whitespace-nowrap">
                      {new Date(p.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-white">{p.symbol}</td>
                    <td className={`py-3 px-4 font-medium ${sideColor(p.side)}`}>{p.side}</td>
                    <td className="py-3 px-4">{(p.confidence * 100).toFixed(1)}%</td>
                    <td className="py-3 px-4 font-mono">{p.reference_price.toFixed(2)}</td>
                    <td className="py-3 px-4">
                      <span className={`text-xs px-2 py-1 rounded ${p.status === 'JUDGED' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">{outcomeBadge(p.outcome)}</td>
                    <td className="py-3 px-4 text-right font-mono">
                      {p.net_return_bps !== undefined ? (
                        <span className={p.net_return_bps > 0 ? 'text-emerald-400' : 'text-red-400'}>
                          {p.net_return_bps > 0 ? '+' : ''}{p.net_return_bps.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-gray-600">--</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="text-center py-20 text-gray-500">No predictions match your filters.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
