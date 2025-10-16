import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  MessageCircle, 
  Database, 
  TrendingUp,
  FileText,
  Users,
  Calendar
} from 'lucide-react'
import ChatInterface from './components/ChatInterface'
import SearchBar from './components/SearchBar'
import POResultCard from './components/POResultCard'
import ConnectionPanel from './components/ConnectionPanel'
import GlassButton from './components/GlassButton'
import LogoIcon from './components/LogoIcon'
import { getAuthStatus } from './services/api'

function App() {
  const [results, setResults] = useState([])
  const [authState, setAuthState] = useState({ connected: false, loading: true, error: null })
  const [activeTab, setActiveTab] = useState('search')

  // Demo data for frontend testing
  const demoResults = [
    {
      id: 1,
      po_number: 'PO-2024-001',
      date: '2024-01-15',
      client_name: 'Metso Corporation',
      total_value: 125000.00,
      source: 'gmail',
      filename: 'Metso_Firebrick_Order.pdf',
      parsed_data: {
        line_items: [
          { description: 'Firebrick Type A', quantity: 100, unit_price: 250.00, total: 25000.00 },
          { description: 'Firebrick Type B', quantity: 200, unit_price: 300.00, total: 60000.00 },
          { description: 'Insulation Material', quantity: 50, unit_price: 800.00, total: 40000.00 }
        ],
        payment_terms: 'Net 30 days',
        raw_text: 'Purchase Order for Firebrick materials...'
      },
      created_at: '2024-01-15T10:30:00Z'
    },
    {
      id: 2,
      po_number: 'PO-2024-002',
      date: '2024-01-20',
      client_name: 'Refractory Solutions Inc',
      total_value: 85000.00,
      source: 'drive',
      filename: 'Refractory_Order_Jan2024.docx',
      parsed_data: {
        line_items: [
          { description: 'Castable Refractory', quantity: 75, unit_price: 600.00, total: 45000.00 },
          { description: 'Ceramic Fiber', quantity: 100, unit_price: 400.00, total: 40000.00 }
        ],
        payment_terms: 'Net 45 days',
        raw_text: 'Refractory materials order for Q1 2024...'
      },
      created_at: '2024-01-20T14:15:00Z'
    }
  ]

  const refreshAuthStatus = useCallback(async () => {
    setAuthState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const status = await getAuthStatus()
      setAuthState({ connected: Boolean(status.connected), loading: false, error: null })
    } catch (error) {
      console.log('Backend not available, running in demo mode')
      setAuthState({ connected: false, loading: false, error: null })
    }
  }, [])

  useEffect(() => {
    refreshAuthStatus()
  }, [refreshAuthStatus])

  const MotionGlassButton = motion(GlassButton)

  const tabs = [
    { id: 'search', label: 'Search', icon: Search },
    { id: 'chat', label: 'AI Chat', icon: MessageCircle },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp }
  ]

  const stats = [
    { label: 'Total POs', value: results.length.toString(), icon: FileText, color: 'text-blue-600' },
    { label: 'This Month', value: results.filter(po => {
      const poDate = new Date(po.date)
      const now = new Date()
      return poDate.getMonth() === now.getMonth() && poDate.getFullYear() === now.getFullYear()
    }).length.toString(), icon: Calendar, color: 'text-green-600' },
    { label: 'Total Value', value: `$${results.reduce((sum, po) => sum + (po.total_value || 0), 0).toLocaleString()}`, icon: TrendingUp, color: 'text-purple-600' },
    { label: 'Clients', value: [...new Set(results.map(po => po.client_name).filter(Boolean))].length.toString(), icon: Users, color: 'text-orange-600' },
    { label: 'Synced', value: authState.connected ? 'Yes' : 'No', icon: Database, color: authState.connected ? 'text-green-600' : 'text-red-600' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <motion.header 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="glass border-b border-white/20 backdrop-blur-md"
      >
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-2xl bg-white/70 backdrop-blur-md flex items-center justify-center shadow-lg border border-white/60">
                <LogoIcon size={36} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-800">PO Search & Parsing</h1>
                <p className="text-sm text-gray-600">Intelligent PO management with AI-powered search</p>
              </div>
            </div>
            
            {/* Stats */}
            <div className="hidden md:flex items-center space-x-6">
              {stats.map((stat, index) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="text-center"
                >
                  <div className={`w-8 h-8 rounded-lg bg-white/50 flex items-center justify-center mx-auto mb-1`}>
                    <stat.icon className={`w-4 h-4 ${stat.color}`} />
                  </div>
                  <div className="text-lg font-semibold text-gray-800">{stat.value}</div>
                  <div className="text-xs text-gray-500">{stat.label}</div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </motion.header>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center space-x-2 bg-white/40 rounded-2xl p-2 backdrop-blur-md border border-white/30 shadow-inner">
          {tabs.map((tab) => (
            <MotionGlassButton
              key={tab.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab(tab.id)}
              variant={activeTab === tab.id ? 'primary' : 'ghost'}
              icon={tab.icon}
              className={`px-5 py-2 text-sm font-medium ${activeTab === tab.id ? 'text-blue-900' : 'text-gray-600'}`}
            >
              <span>{tab.label}</span>
            </MotionGlassButton>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 pb-8">
        <AnimatePresence mode="wait">
          {activeTab === 'search' && (
            <motion.div
              key="search"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="grid lg:grid-cols-3 gap-6"
            >
              {/* Search Section */}
              <section className="lg:col-span-1 space-y-6">
                <SearchBar onResults={setResults} />
                
                {/* Results */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-800">Search Results</h3>
                    <span className="text-sm text-gray-500">{results.length} found</span>
                  </div>
                  
                  <AnimatePresence>
                    {results.length === 0 ? (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-center py-12"
                      >
                        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                          <Search className="w-8 h-8 text-gray-400" />
                        </div>
                        <p className="text-gray-500 mb-2">No search results yet</p>
                        <p className="text-sm text-gray-400 mb-4">Try searching for POs or use the AI chat</p>
                        <MotionGlassButton
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => setResults(demoResults)}
                          className="px-6 py-2.5 text-sm font-semibold"
                        >
                          Load Demo Data
                        </MotionGlassButton>
                      </motion.div>
                    ) : (
                      <div className="space-y-4">
                        {results.map((po, index) => (
                          <POResultCard key={po.id} po={po} index={index} />
                        ))}
                      </div>
                    )}
                  </AnimatePresence>
                </div>
              </section>

              {/* Chat Section */}
              <section className="lg:col-span-2 space-y-6">
                <ConnectionPanel
                  authState={authState}
                  onRefresh={refreshAuthStatus}
                />
                <ChatInterface onResults={setResults} />
              </section>
            </motion.div>
          )}

          {activeTab === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="max-w-4xl mx-auto"
            >
              <ChatInterface onResults={setResults} />
            </motion.div>
          )}

          {activeTab === 'analytics' && (
            <motion.div
              key="analytics"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="text-center py-12"
            >
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">Analytics Dashboard</h3>
              <p className="text-gray-500">Coming soon! Track PO trends, client insights, and more.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <motion.footer 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="glass border-t border-white/20 backdrop-blur-md mt-12"
      >
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="text-center text-sm text-gray-500">
            <p>PO Search & Parsing System • Powered by AI • Built with React & FastAPI</p>
          </div>
        </div>
      </motion.footer>
    </div>
  )
}

export default App
