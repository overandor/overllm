import React, { useState } from 'react'
import { Search, Database, Network, GitBranch } from 'lucide-react'

interface SearchResult {
  id: string
  similarity: number
  type: string
  metadata: Record<string, string>
}

export default function VectorSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [nodeCount, setNodeCount] = useState(1234)
  const [edgeCount, setEdgeCount] = useState(5678)

  const handleSearch = () => {
    // Simulate search results
    const mockResults: SearchResult[] = [
      {
        id: 'node_001',
        similarity: 0.95,
        type: 'trading',
        metadata: { timestamp: '2024-01-15', price: '50000.00' },
      },
      {
        id: 'node_002',
        similarity: 0.87,
        type: 'telemetry',
        metadata: { app: 'VS Code', cpu: '45%' },
      },
      {
        id: 'node_003',
        similarity: 0.82,
        type: 'concept',
        metadata: { category: 'machine learning' },
      },
    ]
    setResults(mockResults)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800">DAG Vector Search</h2>
      
      {/* Search Input */}
      <div className="neu-card">
        <div className="flex gap-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search vectors..."
            className="neu-input flex-1"
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch} className="neu-button flex items-center gap-2">
            <Search className="w-5 h-5" />
            Search
          </button>
        </div>
      </div>

      {/* DAG Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="neu-card">
          <div className="flex items-center gap-3 mb-2">
            <Database className="w-6 h-6 text-neu-accent" />
            <span className="text-sm text-gray-600">Total Nodes</span>
          </div>
          <div className="text-3xl font-bold text-gray-800">{nodeCount}</div>
        </div>
        <div className="neu-card">
          <div className="flex items-center gap-3 mb-2">
            <Network className="w-6 h-6 text-blue-500" />
            <span className="text-sm text-gray-600">Total Edges</span>
          </div>
          <div className="text-3xl font-bold text-gray-800">{edgeCount}</div>
        </div>
      </div>

      {/* Search Results */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Search Results</h3>
        {results.length === 0 ? (
          <div className="text-center text-gray-500 py-8">Enter a query to search</div>
        ) : (
          <div className="space-y-3">
            {results.map((result, i) => (
              <div key={i} className="p-4 bg-neu-bg rounded-neu-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-neu-accent" />
                    <span className="font-semibold text-gray-800">{result.id}</span>
                  </div>
                  <span className="text-sm text-neu-accent font-bold">
                    {(result.similarity * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-sm text-gray-600 mb-2">Type: {result.type}</div>
                <div className="text-xs text-gray-500">
                  {Object.entries(result.metadata).map(([k, v]) => (
                    <span key={k} className="mr-3">
                      <span className="font-medium">{k}:</span> {v}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DAG Visualization Placeholder */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">DAG Structure</h3>
        <div className="h-64 bg-neu-bg rounded-neu-sm flex items-center justify-center">
          <div className="text-center text-gray-500">
            <Network className="w-12 h-12 mx-auto mb-2" />
            <p>Interactive DAG visualization</p>
            <p className="text-sm">Shows node relationships and edge weights</p>
          </div>
        </div>
      </div>

      {/* Vector Types */}
      <div className="neu-card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Vector Types</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-neu-bg rounded-neu-sm text-center">
            <div className="text-2xl font-bold text-green-500">456</div>
            <div className="text-sm text-gray-600">Trading</div>
          </div>
          <div className="p-4 bg-neu-bg rounded-neu-sm text-center">
            <div className="text-2xl font-bold text-blue-500">321</div>
            <div className="text-sm text-gray-600">Telemetry</div>
          </div>
          <div className="p-4 bg-neu-bg rounded-neu-sm text-center">
            <div className="text-2xl font-bold text-purple-500">234</div>
            <div className="text-sm text-gray-600">Concept</div>
          </div>
          <div className="p-4 bg-neu-bg rounded-neu-sm text-center">
            <div className="text-2xl font-bold text-orange-500">223</div>
            <div className="text-sm text-gray-600">Meta LLM</div>
          </div>
        </div>
      </div>
    </div>
  )
}
