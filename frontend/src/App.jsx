import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  MessageCircle,
  Database,
  TrendingUp,
  FileText,
  Users,
  Calendar,
  DollarSign,
  LogOut
} from 'lucide-react'
import ChatInterface from './components/ChatInterface'
import SearchBar from './components/SearchBar'
import POResultCard from './components/POResultCard'
import ConnectionPanel from './components/ConnectionPanel'
import GlassButton from './components/GlassButton'
import LogoIcon from './components/LogoIcon'
import { API_BASE_URL, getAuthStatus, getAnalytics, triggerSync, getSession, logout } from './services/api'
import LoginPage from './components/LoginPage'

function App() {
  const [results, setResults] = useState([])
  const [authState, setAuthState] = useState({ connected: false, loading: true, error: null })
  const [activeTab, setActiveTab] = useState('search')
  const [analytics, setAnalytics] = useState(null)
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [analyticsError, setAnalyticsError] = useState(null)
  const [session, setSession] = useState({ loading: false, user: null, error: null })

  const autoSyncAttemptedRef = useRef(false)

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

  const fetchAnalytics = useCallback(async () => {
    setAnalyticsLoading(true)
    setAnalyticsError(null)
    try {
      const data = await getAnalytics()
      setAnalytics(data)
    } catch (error) {
      setAnalyticsError('Failed to load analytics data. Please check backend connectivity.')
    } finally {
      setAnalyticsLoading(false)
    }
  }, [])

  const fetchSession = useCallback(async () => {
    setSession((prev) => ({ ...prev, loading: true }))
    try {
      const data = await getSession()
      setSession({ loading: false, user: data, error: null })
    } catch (error) {
      setSession({ loading: false, user: null, error: null })
    }
  }, [])

  const handleLoginSuccess = useCallback((data) => {
    setSession({ loading: false, user: data, error: null })
    refreshAuthStatus()
    fetchAnalytics()
    fetchSession()
  }, [refreshAuthStatus, fetchAnalytics, fetchSession])

  const handleLogout = useCallback(async () => {
    try {
      await logout()
      setSession({ loading: false, user: null, error: null })
      setAuthState({ connected: false, loading: false, error: null })
      setAnalytics(null)
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }, [])

  const formatCurrency = (value, options = {}) => {
    if (value == null || Number.isNaN(Number(value))) return '—'
    try {
      return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: options.maximumFractionDigits ?? 0
      }).format(Number(value))
    } catch (err) {
      return `₹${Number(value).toLocaleString('en-IN')}`
    }
  }

  const formatDateLabel = (value) => {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '—'
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const formatDateTimeLabel = (value) => {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '—'
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  const formatMonthKey = (key) => {
    if (!key) return '—'
    const [year, month] = key.split('-')
    if (!year || !month) return key
    const parsed = new Date(Number(year), Number(month) - 1)
    if (Number.isNaN(parsed.getTime())) return key
    return parsed.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  }

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


  useEffect(() => {
    if (session.user) {
      refreshAuthStatus()
    }
  }, [refreshAuthStatus, session.user])

  useEffect(() => {
    if (!session.user) return
    if (activeTab === 'analytics' && !analytics && !analyticsLoading) {
      fetchAnalytics()
    }
  }, [activeTab, analytics, analyticsLoading, fetchAnalytics, session.user])

  useEffect(() => {
    if (!session.user) return
    if (!authState.loading && authState.connected && !autoSyncAttemptedRef.current) {
      autoSyncAttemptedRef.current = true
      ;(async () => {
        try {
          await triggerSync({ enable_gmail: false, enable_drive: true })
          fetchAnalytics()
        } catch (err) {
          console.error('Automatic Drive sync failed', err)
        }
      })()
    }
  }, [authState.loading, authState.connected, fetchAnalytics, session.user])

  const MotionGlassButton = motion(GlassButton)

  useEffect(() => {
    fetchSession()
  }, [fetchSession])

  const tabs = [
    { id: 'search', label: 'Search', icon: Search },
    { id: 'chat', label: 'AI Chat', icon: MessageCircle },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp }
  ]

  const analyticsSummary = analytics?.summary

  const stats = analyticsSummary
    ? [
        {
          label: 'Total POs',
          value: analyticsSummary.total_pos.toLocaleString(),
          icon: FileText,
          color: 'text-blue-600'
        },
        {
          label: 'Total Value',
          value: formatCurrency(analyticsSummary.total_value),
          icon: TrendingUp,
          color: 'text-purple-600'
        },
        {
          label: 'Average Value',
          value: formatCurrency(analyticsSummary.average_value, { maximumFractionDigits: 2 }),
          icon: DollarSign,
          color: 'text-emerald-600'
        },
        {
          label: 'Synced',
          value: authState.connected ? 'Yes' : 'No',
          icon: Database,
          color: authState.connected ? 'text-green-600' : 'text-red-600'
        },
        {
          label: 'Last Ingested',
          value: formatDateLabel(analyticsSummary.last_ingested),
          icon: Calendar,
          color: 'text-indigo-600'
        }
      ]
    : [
        {
          label: 'Total POs',
          value: results.length.toString(),
          icon: FileText,
          color: 'text-blue-600'
        },
        {
          label: 'This Month',
          value: results
            .filter((po) => {
              const poDate = new Date(po.date)
              const now = new Date()
              return poDate.getMonth() === now.getMonth() && poDate.getFullYear() === now.getFullYear()
            })
            .length.toString(),
          icon: Calendar,
          color: 'text-green-600'
        },
        {
          label: 'Total Value',
          value: formatCurrency(results.reduce((sum, po) => sum + (po.total_value || 0), 0)),
          icon: TrendingUp,
          color: 'text-purple-600'
        },
        {
          label: 'Clients',
          value: [...new Set(results.map((po) => po.client_name).filter(Boolean))].length.toString(),
          icon: Users,
          color: 'text-orange-600'
        },
        {
          label: 'Synced',
          value: authState.connected ? 'Yes' : 'No',
          icon: Database,
          color: authState.connected ? 'text-green-600' : 'text-red-600'
        }
      ]

  const monthlyData = analytics?.monthly_value ?? []
  const topClients = analytics?.top_clients ?? []
  const sourceBreakdown = analytics?.source_breakdown ?? []
  const recentActivity = analytics?.recent_activity ?? []

  if (session.loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 to-blue-100">
        <div className="text-sm text-slate-500">Preparing your workspace…</div>
      </div>
    )
  }

  if (!session.user) {
    return <LoginPage onSuccess={handleLoginSuccess} errorMessage={session.error} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slatey-50 via-slatey-100 to-electric-50 text-slate-900 dark:text-slate-100">
      {/* Hero Header with breathing room */}
      <motion.header 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="backdrop-blur-md"
      >
        <div className="max-w-7xl mx-auto px-6 pt-10 pb-6">
          <div className="flex items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-[20px] bg-white/70 backdrop-blur-md flex items-center justify-center shadow-lg border border-white/60">
                <LogoIcon size={36} />
              </div>
              <div>
                <h1 className="text-[28px] leading-8 font-semibold text-gray-900 tracking-[-0.01em]">PO Search & Parsing</h1>
                <p className="mt-1 text-[13px] leading-5 text-gray-600">Intelligent PO management with AI-powered search</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Quick stats dock */}
              <div className="hidden md:flex items-stretch rounded-[20px] border border-white/40 bg-white/60 backdrop-blur-lg shadow-inner px-3 py-2">
                {stats.map((stat, index) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.06 }}
                    className="flex items-center px-3"
                  >
                    <div className="w-8 h-8 rounded-[12px] bg-white/70 flex items-center justify-center mr-2 border border-white/60">
                      <stat.icon className={`w-4 h-4 ${stat.color}`} />
                    </div>
                    <div className="leading-tight">
                      <div className="text-sm font-semibold text-gray-800">{stat.value}</div>
                      <div className="text-[11px] text-gray-500">{stat.label}</div>
                    </div>
                    {index < stats.length - 1 && <div className="mx-3 h-6 w-px bg-white/50" />}
                  </motion.div>
                ))}
              </div>

              {/* Logout button */}
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 rounded-[16px] bg-white/60 backdrop-blur-lg border border-white/40 shadow-inner hover:bg-white/70 transition-all duration-120 ease-out-120"
                title="Logout"
              >
                <LogOut className="w-4 h-4 text-gray-700" />
                <span className="text-sm font-medium text-gray-700 hidden lg:inline">Logout</span>
              </motion.button>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Navigation Pills */}
      <div className="max-w-7xl mx-auto px-6 pb-4">
        <div className="flex items-center gap-2 bg-white/50 dark:bg-white/10 rounded-[20px] p-2 backdrop-blur-md border border-white/40 dark:border-white/10 shadow-inner">
          {tabs.map((tab) => (
            <MotionGlassButton
              key={tab.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab(tab.id)}
              variant={activeTab === tab.id ? 'primary' : 'ghost'}
              icon={tab.icon}
              className={`px-5 py-2 text-sm font-medium ${activeTab === tab.id ? 'text-gray-900' : 'text-gray-600'}`}
            >
              <span>{tab.label}</span>
            </MotionGlassButton>
          ))}
        </div>
      </div>

      {/* Main Content aligned on baseline grid */}
      <main className="max-w-7xl mx-auto px-6 pb-10">
        <AnimatePresence mode="wait">
          {activeTab === 'search' && (
            <motion.div
              key="search"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="grid lg:grid-cols-12 gap-6"
            >
              {/* Left rail: filters + results */}
              <section className="lg:col-span-4 space-y-6">
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
                        <p className="text-sm text-gray-400 mb-4">No Gmail sync yet—connect in Google Connection.</p>
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

              {/* Right: conversational workspace */}
              <section className="lg:col-span-8 space-y-6">
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
              className="space-y-6"
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-200 to-blue-200 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-purple-700" />
                </div>
                <div className="text-left">
                  <h3 className="text-xl font-semibold text-gray-800">Analytics Dashboard</h3>
                  <p className="text-sm text-gray-500">
                    Track ingestion trends, top clients, and source coverage for your purchase orders.
                  </p>
                </div>
              </div>

              {analyticsLoading && (
                <div className="glass rounded-2xl border border-white/30 p-6 text-left">
                  <p className="text-sm text-gray-600 animate-pulse">Loading analytics…</p>
                </div>
              )}

              {analyticsError && (
                <div className="glass rounded-2xl border border-red-200 bg-red-50/70 p-6 text-left">
                  <p className="text-sm text-red-600">{analyticsError}</p>
                </div>
              )}

              {!analyticsLoading && !analyticsError && analytics && (
                <div className="space-y-6 text-left">
                  <section className="grid md:grid-cols-3 gap-4">
                    <div className="glass rounded-2xl border border-white/20 p-5 shadow-sm">
                      <p className="text-xs tracking-wide text-gray-500 uppercase mb-1">Total POs</p>
                      <p className="text-2xl font-semibold text-gray-900">{analytics.summary.total_pos.toLocaleString()}</p>
                      <p className="text-sm text-gray-500">Indexed across Gmail & Drive</p>
                    </div>
                    <div className="glass rounded-2xl border border-white/20 p-5 shadow-sm">
                      <p className="text-xs tracking-wide text-gray-500 uppercase mb-1">Total Value</p>
                      <p className="text-2xl font-semibold text-gray-900">{formatCurrency(analytics.summary.total_value)}</p>
                      <p className="text-sm text-gray-500">Sum of parsed PO totals</p>
                    </div>
                    <div className="glass rounded-2xl border border-white/20 p-5 shadow-sm">
                      <p className="text-xs tracking-wide text-gray-500 uppercase mb-1">Last Ingested</p>
                      <p className="text-2xl font-semibold text-gray-900">{formatDateLabel(analytics.summary.last_ingested)}</p>
                      <p className="text-sm text-gray-500">Most recent PO ingestion timestamp</p>
                    </div>
                  </section>

                  <div className="grid lg:grid-cols-2 gap-6">
                    <div className="glass rounded-2xl border border-white/20 p-6 shadow-sm">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-semibold text-gray-800">Monthly Totals</h4>
                        <span className="text-xs text-gray-500">Last {monthlyData.length} months</span>
                      </div>
                      <div className="space-y-3">
                        {monthlyData.length ? (
                          monthlyData.map((entry) => (
                            <div
                              key={entry.month}
                              className="flex items-center justify-between rounded-xl bg-white/80 px-4 py-3 border border-gray-100"
                            >
                              <div>
                                <p className="text-sm font-semibold text-gray-800">{formatMonthKey(entry.month)}</p>
                                <p className="text-xs text-gray-500">{entry.po_count} POs</p>
                              </div>
                              <div className="text-sm font-semibold text-gray-800">{formatCurrency(entry.total_value)}</div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-gray-500">No monthly data yet.</p>
                        )}
                      </div>
                    </div>

                    <div className="glass rounded-2xl border border-white/20 p-6 shadow-sm">
                      <h4 className="text-lg font-semibold text-gray-800 mb-4">Top Clients</h4>
                      <div className="space-y-3">
                        {topClients.length ? (
                          topClients.map((client, index) => (
                            <div
                              key={`${client.client_name}-${index}`}
                              className="flex items-center justify-between rounded-xl bg-white/80 px-4 py-3 border border-gray-100"
                            >
                              <div>
                                <p className="text-sm font-semibold text-gray-800">{client.client_name}</p>
                                <p className="text-xs text-gray-500">{client.po_count} POs</p>
                              </div>
                              <div className="text-sm font-semibold text-gray-800">{formatCurrency(client.total_value)}</div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-gray-500">No client breakdown yet.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid lg:grid-cols-2 gap-6">
                    <div className="glass rounded-2xl border border-white/20 p-6 shadow-sm">
                      <h4 className="text-lg font-semibold text-gray-800 mb-4">Source Breakdown</h4>
                      <div className="space-y-3">
                        {sourceBreakdown.length ? (
                          sourceBreakdown.map((source) => (
                            <div
                              key={source.source}
                              className="flex items-center justify-between rounded-xl bg-white/80 px-4 py-3 border border-gray-100"
                            >
                              <div>
                                <p className="text-sm font-semibold text-gray-800 capitalize">{source.source}</p>
                                <p className="text-xs text-gray-500">{source.po_count} POs</p>
                              </div>
                              <div className="text-sm font-semibold text-gray-800">{formatCurrency(source.total_value)}</div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-gray-500">No source data yet.</p>
                        )}
                      </div>
                    </div>

                    <div className="glass rounded-2xl border border-white/20 p-6 shadow-sm">
                      <h4 className="text-lg font-semibold text-gray-800 mb-4">Recent Activity</h4>
                      <div className="space-y-3">
                        {recentActivity.length ? (
                          recentActivity.map((item) => (
                            <div
                              key={item.id}
                              className="flex items-center justify-between rounded-xl bg-white/80 px-4 py-3 border border-gray-100"
                            >
                              <div>
                                <p className="text-sm font-semibold text-gray-800">{item.po_number || `PO-${item.id}`}</p>
                                <p className="text-xs text-gray-500">{formatDateTimeLabel(item.created_at)}</p>
                              </div>
                              <div className="text-sm font-semibold text-gray-800">{formatCurrency(item.total_value)}</div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-gray-500">No recent activity captured.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {!analyticsLoading && !analyticsError && !analytics && (
                <div className="glass rounded-2xl border border-white/20 p-6 text-left">
                  <p className="text-sm text-gray-500">Analytics will appear after your first sync completes.</p>
                </div>
              )}
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
