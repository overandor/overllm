import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { BarChart3, Book, Activity, Settings, FileText, Hash, Radio, Info, Home } from 'lucide-react'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import PredictionsPage from './pages/PredictionsPage'
import PerformancePage from './pages/PerformancePage'
import ReceiptsPage from './pages/ReceiptsPage'
import DocsPage from './pages/DocsPage'
import SettingsPage from './pages/SettingsPage'
import TelemetryPage from './pages/TelemetryPage'
import AboutPage from './pages/AboutPage'

function NavBar() {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  const links = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/dashboard', icon: BarChart3, label: 'Dashboard' },
    { path: '/predictions', icon: FileText, label: 'Predictions' },
    { path: '/performance', icon: Activity, label: 'Performance' },
    { path: '/receipts', icon: Hash, label: 'Receipts' },
    { path: '/telemetry', icon: Radio, label: 'Telemetry' },
    { path: '/docs', icon: Book, label: 'Docs' },
    { path: '/settings', icon: Settings, label: 'Settings' },
    { path: '/about', icon: Info, label: 'About' },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-gray-950/80 backdrop-blur border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center h-14 gap-1 overflow-x-auto">
          <Link to="/" className="flex items-center gap-2 mr-4 flex-shrink-0">
            <BarChart3 className="w-5 h-5 text-emerald-400" />
            <span className="font-bold text-white">OverLLM</span>
          </Link>
          {links.map(l => (
            <Link
              key={l.path}
              to={l.path}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition whitespace-nowrap ${
                isActive(l.path) ? 'bg-emerald-500/10 text-emerald-400' : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <l.icon className="w-4 h-4" />
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <NavBar />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/predictions" element={<PredictionsPage />} />
          <Route path="/performance" element={<PerformancePage />} />
          <Route path="/receipts" element={<ReceiptsPage />} />
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/telemetry" element={<TelemetryPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App
