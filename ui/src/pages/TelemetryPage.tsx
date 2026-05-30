import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, Radio, Server, Database, Clock } from 'lucide-react';

interface TickData {
  symbol: string;
  last: number;
  change: number;
  volume: number;
  timestamp: number;
}

export default function TelemetryPage() {
  const [ticks, setTicks] = useState<TickData[]>([]);
  const [status, setStatus] = useState<any>({});
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    const fetchData = () => {
      fetch('/api/status').then(r => r.json()).then(d => {
        setStatus(d);
        setLastUpdate(new Date());
      }).catch(() => {});

      fetch('/api/gate/markets').then(r => r.json()).then(d => {
        const markets = d.markets || [];
        setTicks(markets.slice(0, 10).map((m: any) => ({
          symbol: m.contract,
          last: parseFloat(m.last || 0),
          change: parseFloat(m.change_percentage || 0),
          volume: parseFloat(m.volume_24h || 0),
          timestamp: Date.now()
        })));
      }).catch(() => {});
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Radio className="w-7 h-7 text-emerald-400" />
            Live Telemetry
          </h1>
          <div className="ml-auto flex items-center gap-2 text-xs text-gray-500">
            <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
            Last update: {lastUpdate.toLocaleTimeString()}
          </div>
        </div>

        {/* System Status */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <Server className="w-5 h-5 text-cyan-400 mb-3" />
            <div className="text-2xl font-bold text-white">{status.running ? 'ONLINE' : 'OFFLINE'}</div>
            <div className="text-sm text-gray-500 mt-1">Alpha Engine</div>
          </div>
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <Clock className="w-5 h-5 text-cyan-400 mb-3" />
            <div className="text-2xl font-bold text-white">{status.interval_seconds || '--'}s</div>
            <div className="text-sm text-gray-500 mt-1">Prediction Interval</div>
          </div>
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <Database className="w-5 h-5 text-cyan-400 mb-3" />
            <div className="text-2xl font-bold text-white">{(status.symbols || []).length}</div>
            <div className="text-sm text-gray-500 mt-1">Active Symbols</div>
          </div>
        </div>

        {/* Live Tick Table */}
        <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            Gate.io Live Tick Data
          </h3>
          {ticks.length === 0 ? (
            <div className="text-center py-12 text-gray-500">Fetching tick data...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left py-3 px-4">Symbol</th>
                    <th className="text-right py-3 px-4">Last Price</th>
                    <th className="text-right py-3 px-4">Change %</th>
                    <th className="text-right py-3 px-4">Volume 24h</th>
                  </tr>
                </thead>
                <tbody>
                  {ticks.map((t, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition">
                      <td className="py-3 px-4 font-mono text-white">{t.symbol}</td>
                      <td className="py-3 px-4 text-right font-mono">{t.last.toFixed(4)}</td>
                      <td className={`py-3 px-4 text-right font-mono ${t.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {t.change >= 0 ? '+' : ''}{t.change.toFixed(2)}%
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-gray-400">{(t.volume / 1e6).toFixed(2)}M</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
