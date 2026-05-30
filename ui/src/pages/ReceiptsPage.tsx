import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Hash, FileCheck, Copy, Check, ExternalLink } from 'lucide-react';

interface Receipt {
  prediction_id: string;
  symbol: string;
  side: string;
  hash: string;
  type: 'prediction' | 'outcome';
  timestamp: string;
}

export default function ReceiptsPage() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/receipts?limit=100')
      .then(r => r.json())
      .then(d => setReceipts(d.receipts || []))
      .catch(() => setReceipts([]));
  }, []);

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopied(hash);
    setTimeout(() => setCopied(null), 1500);
  };

  const truncate = (s: string) => s.slice(0, 16) + '...' + s.slice(-8);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-300 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <FileCheck className="w-7 h-7 text-emerald-400" />
            Receipt Explorer
          </h1>
        </div>

        <div className="mb-6 p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
          <p className="text-sm text-emerald-400/80">
            Every prediction and outcome is hashed with SHA256 over canonical JSON.
            This creates an append-only, cryptographically verifiable audit trail.
          </p>
        </div>

        {receipts.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            No receipts yet. Make a prediction to generate the first receipt.
          </div>
        ) : (
          <div className="space-y-2">
            {receipts.map((r, i) => (
              <div key={i} className="flex items-center gap-4 p-4 rounded-lg bg-gray-900 border border-gray-800 hover:border-gray-700 transition">
                <Hash className="w-5 h-5 text-gray-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">{r.type}</span>
                    <span className="font-mono text-sm text-white">{r.symbol}</span>
                    <span className={`text-xs font-medium ${r.side.includes('LONG') ? 'text-emerald-400' : 'text-red-400'}`}>
                      {r.side}
                    </span>
                  </div>
                  <div className="font-mono text-xs text-gray-500 truncate">{truncate(r.hash)}</div>
                </div>
                <div className="text-xs text-gray-500 whitespace-nowrap">
                  {new Date(r.timestamp).toLocaleString()}
                </div>
                <button
                  onClick={() => copyHash(r.hash)}
                  className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                  title="Copy full hash"
                >
                  {copied === r.hash ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
