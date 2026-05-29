import { useState } from 'react';
import { Book, Code, Server, Database, Shield, FileText, ChevronRight, Copy, Check } from 'lucide-react';

const endpoints = [
  { method: 'GET', path: '/api/status', desc: 'Engine status, truth labels, runtime config' },
  { method: 'GET', path: '/api/model', desc: 'Policy hash, epsilon, calibration state' },
  { method: 'GET', path: '/api/gate/markets', desc: 'Available Gate.io futures markets' },
  { method: 'GET', path: '/api/predictions/live', desc: 'Recent predictions with outcomes' },
  { method: 'GET', path: '/api/predictions/pending', desc: 'Predictions waiting for 3-min judgment' },
  { method: 'GET', path: '/api/predictions/history', desc: 'Full prediction history' },
  { method: 'GET', path: '/api/performance', desc: 'Stats, accuracy by symbol, calibration' },
  { method: 'GET', path: '/api/receipts', desc: 'Cryptographic receipt explorer' },
  { method: 'POST', path: '/api/predict/once', desc: 'Trigger a single prediction (body: {symbol})' },
  { method: 'POST', path: '/api/engine/start', desc: 'Start the auto-prediction loop' },
  { method: 'POST', path: '/api/engine/stop', desc: 'Stop the auto-prediction loop' },
  { method: 'POST', path: '/api/judge/pending', desc: 'Force judgment of elapsed predictions' },
];

const modules = [
  { name: 'gate/client.py', desc: 'Gate.io futures REST API client. Fetches tickers, candlesticks, order books, trades, funding rates.' },
  { name: 'features/engine.py', desc: '322 dynamic KPI indicators generated on-the-fly from market data. Returns, volatility, SMA/EMA, RSI, MACD, BB, ATR, OBV, VWAP, ADX, CCI, Williams %R, MFI, Keltner, Donchian, Fibonacci, Pivots, ROC, CMF, PPO, autocorrelation, variance ratios, trade flow, order book depth, funding, basis, skew, kurtosis, market structure.' },
  { name: 'predictions/store.py', desc: 'Thread-safe SQLite append-only store. No deletion of losses. Every row is permanent.' },
  { name: 'predictions/judge.py', desc: 'ThreeMinuteOutcomeJudge. Fetches exit price after exactly 180s. Scores net return after fees, spread, slippage penalties.' },
  { name: 'learning/q_learning.py', desc: 'Online tabular Q-learning with epsilon-greedy exploration. Confidence calibration with sliding-window accuracy tracking. Regime and symbol memory.' },
  { name: 'risk/governor.py', desc: 'Veto system: stale data, high spread, volatility shock, drawdown, cooldown, API degradation. Live trading hard-disabled.' },
  { name: 'receipts/hasher.py', desc: 'Canonical JSON + SHA256 receipts for every prediction and outcome. Deterministic, auditable.' },
  { name: 'engine.py', desc: 'Main orchestrator. Fetches data, builds features, runs policy, applies risk veto, stores prediction, schedules judge.' },
];

export default function DocsPage() {
  const [copied, setCopied] = useState<string | null>(null);

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 1500);
  };

  const curlExample = `curl -X POST https://overllm-alpha.onrender.com/api/predict/once \\
  -H "Content-Type: application/json" \\
  -d '{"symbol": "BTC_USDT"}'`;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
          <Book className="w-8 h-8 text-emerald-400" />
          Documentation
        </h1>
        <p className="text-gray-500 mb-12">API reference, architecture, and deployment guide.</p>

        {/* Quick Start */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6 flex items-center gap-2">
            <Code className="w-5 h-5 text-cyan-400" />
            Quick Start
          </h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4 relative">
            <pre className="text-sm overflow-x-auto"><code className="text-emerald-400">{curlExample}</code></pre>
            <button onClick={() => copy(curlExample)} className="absolute top-3 right-3 p-1.5 rounded bg-gray-800 hover:bg-gray-700 transition">
              {copied === curlExample ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </section>

        {/* Endpoints */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6 flex items-center gap-2">
            <Server className="w-5 h-5 text-cyan-400" />
            API Endpoints
          </h2>
          <div className="space-y-2">
            {endpoints.map((ep, i) => (
              <div key={i} className="flex items-center gap-4 p-3 rounded-lg bg-gray-900/50 border border-gray-800 hover:border-gray-700 transition">
                <span className={`text-xs font-mono font-bold px-2 py-1 rounded ${ep.method === 'GET' ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'}`}>
                  {ep.method}
                </span>
                <code className="text-sm text-gray-300 font-mono">{ep.path}</code>
                <span className="text-sm text-gray-500 ml-auto">{ep.desc}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Modules */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6 flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Module Reference
          </h2>
          <div className="grid gap-4">
            {modules.map((m, i) => (
              <div key={i} className="p-4 rounded-lg bg-gray-900/50 border border-gray-800">
                <code className="text-sm font-mono text-emerald-400">{m.name}</code>
                <p className="text-sm text-gray-400 mt-2">{m.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Truth Labels */}
        <section className="mb-16">
          <h2 className="text-2xl font-semibold text-white mb-6 flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-400" />
            Truth Labels
          </h2>
          <p className="text-gray-400 mb-4">
            Every <code>/api/status</code> response includes these truth labels for full transparency:
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {[
              { key: 'runtime', val: 'real' },
              { key: 'telemetry', val: 'real' },
              { key: 'gateio_data', val: 'real if fetched live' },
              { key: 'prediction_mode', val: 'paper' },
              { key: 'live_trading', val: 'disabled' },
              { key: 'model_quality', val: 'experimental' },
              { key: 'receipts', val: 'real' },
              { key: 'tunnel', val: 'production' },
            ].map((t, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded bg-gray-900 border border-gray-800">
                <code className="text-sm text-gray-400">{t.key}</code>
                <span className="text-sm font-mono text-emerald-400">{t.val}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Architecture */}
        <section>
          <h2 className="text-2xl font-semibold text-white mb-6 flex items-center gap-2">
            <FileText className="w-5 h-5 text-cyan-400" />
            Architecture
          </h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 font-mono text-sm text-gray-400 leading-relaxed">
            {`Gate.io API
    -> gate/client.py (REST polling, 1m/5m/15m candles, order book, trades, funding)
    -> features/engine.py (322 KPIs: returns, vol, SMA, EMA, RSI, MACD, BB, ATR, OBV,
                          VWAP, ADX, CCI, WilliamsR, MFI, Keltner, Donchian, Fibonacci,
                          Pivots, ROC, CMF, PPO, autocorr, variance ratios, trade flow,
                          order book depth, funding, basis, skew, kurtosis, market structure)
    -> engine.py (orchestrator)
        -> risk/governor.py (veto: stale data, spread, volatility, drawdown, cooldown)
        -> learning/q_learning.py (action selection: LONG / SHORT / PREPARE_LONG / PREPARE_SHORT)
        -> predictions/store.py (append-only SQLite)
        -> receipts/hasher.py (SHA256 canonical JSON)
    -> 3-minute wait
    -> predictions/judge.py (exit price, net return, outcome classification)
    -> learning/q_learning.py (weight update, confidence calibration)
    -> predictions/store.py (outcome record + receipt)`}
          </div>
        </section>
      </div>
    </div>
  );
}
