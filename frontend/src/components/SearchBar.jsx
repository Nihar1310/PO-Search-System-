import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Filter,
  Clock,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Calendar,
  DollarSign
} from 'lucide-react'
import { searchPOs } from '../services/api'
import GlassButton from './GlassButton'

const MotionGlassButton = motion(GlassButton)

export default function SearchBar({ onResults }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastSearch, setLastSearch] = useState(null)
  const [recentSearches, setRecentSearches] = useState([
    'Metso firebrick',
    'PO-2024-001',
    'January orders',
    'High value POs'
  ])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [rawResults, setRawResults] = useState([])
  const [filters, setFilters] = useState({
    sources: new Set(),
    startDate: '',
    endDate: '',
    minValue: ''
  })
  const [filterTouched, setFilterTouched] = useState(false)
  const inputRef = useRef(null)

  const filteredResults = useMemo(() => {
    if (!rawResults.length) return []

    return rawResults.filter((po) => {
      const source = (po.source || 'unknown').toLowerCase()
      const sourceMatch = filters.sources.size === 0 || filters.sources.has(source)

      const hasDate = Boolean(po.date)
      let date = null
      if (hasDate) {
        const parsed = new Date(po.date)
        date = Number.isNaN(parsed.getTime()) ? null : parsed
      }

      const startMatch = filters.startDate
        ? date
          ? date >= new Date(filters.startDate)
          : false
        : true
      const endMatch = filters.endDate
        ? date
          ? date <= new Date(filters.endDate)
          : false
        : true

      const minValueMatch = filters.minValue
        ? Number(po.total_value || 0) >= Number(filters.minValue)
        : true

      return sourceMatch && startMatch && endMatch && minValueMatch
    })
  }, [rawResults, filters])

  useEffect(() => {
    if (rawResults.length) {
      onResults(filteredResults)
    }
  }, [filteredResults, rawResults.length, onResults])

  const updateFilters = (updater) => {
    setFilterTouched(true)
    setFilters((prev) => {
      const next = updater(prev)
      return { ...next }
    })
  }

  const toggleSource = (source) => {
    updateFilters((prev) => {
      const nextSources = new Set(prev.sources)
      if (nextSources.has(source)) {
        nextSources.delete(source)
      } else {
        nextSources.add(source)
      }
      return { ...prev, sources: nextSources }
    })
  }

  const clearFilters = () => {
    setFilterTouched(false)
    setFilters({ sources: new Set(), startDate: '', endDate: '', minValue: '' })
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) {
      setError('Please enter a PO number, client name, or keyword to search.')
      onResults([])
      return
    }
    
    setLoading(true)
    setError(null)
    setLastSearch(query)
    
    // Add to recent searches if not already there
    if (!recentSearches.includes(query)) {
      setRecentSearches(prev => [query, ...prev.slice(0, 3)])
    }
    
    try {
      const res = await searchPOs(query)
      setRawResults(res)
      if (!filterTouched) {
        onResults(res)
      }
      
      if (!res.length) {
        setError('No POs matched your search. Try syncing your Gmail/Drive or using different keywords.')
      }
    } catch (e) {
      setRawResults([])
      onResults([])
      setError('Search failed. Please check your backend connection and try again.')
    } finally {
      setLoading(false)
      setShowSuggestions(false)
    }
  }

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion)
    setShowSuggestions(false)
    // Trigger search automatically
    setTimeout(() => {
      onSubmit({ preventDefault: () => {} })
    }, 100)
  }

  const clearSearch = () => {
    setQuery('')
    setError(null)
    setRawResults([])
    setFilterTouched(false)
    setFilters({ sources: new Set(), startDate: '', endDate: '', minValue: '' })
    onResults([])
    inputRef.current?.focus()
  }

  const SearchSuggestions = () => (
    <AnimatePresence>
      {showSuggestions && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-lg border border-gray-200 z-10 overflow-hidden"
        >
          {recentSearches.length > 0 && (
            <div className="p-3 border-b border-gray-100">
              <div className="flex items-center space-x-2 text-xs text-gray-500 mb-2">
                <Clock className="w-3 h-3" />
                <span>Recent searches</span>
              </div>
              <div className="space-y-1">
                {recentSearches.map((search, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(search)}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
                  >
                    {search}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <div className="p-3">
            <div className="text-xs text-gray-500 mb-2">Quick searches</div>
            <div className="space-y-1">
              {['All POs', 'This month', 'High value', 'Pending'].map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )

  const sourceOptions = [
    { label: 'Gmail', value: 'gmail' },
    { label: 'Drive', value: 'drive' },
    { label: 'Cache', value: 'cache' }
  ]

  const summaryStats = useMemo(() => {
    if (!filteredResults.length) {
      return { total: 0, gmail: 0, drive: 0, maxValue: null }
    }

    let gmail = 0
    let drive = 0
    let maxValue = 0

    filteredResults.forEach((po) => {
      const value = Number(po.total_value || 0)
      if (value > maxValue) {
        maxValue = value
      }
      const source = (po.source || '').toLowerCase()
      if (source === 'gmail') gmail += 1
      if (source === 'drive') drive += 1
    })

    return {
      total: filteredResults.length,
      gmail,
      drive,
      maxValue: maxValue || null
    }
  }, [filteredResults])

  const renderFilters = () => (
    <AnimatePresence>
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="mt-4 space-y-5 rounded-2xl border border-white/40 bg-white/95 p-5 shadow-sm"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Filters</p>
              <p className="text-sm text-gray-500">Refine results by source, date range, or minimum PO value.</p>
            </div>
            <GlassButton
              type="button"
              variant="ghost"
              icon={XCircle}
              className="text-sm"
              onClick={clearFilters}
            >
              Reset filters
            </GlassButton>
          </div>

          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Sources</p>
            <div className="flex flex-wrap gap-2">
              {sourceOptions.map(({ label, value }) => {
                const active = filters.sources.has(value)
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => toggleSource(value)}
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      active
                        ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-blue-300'
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="flex flex-col gap-2 text-xs font-medium text-gray-600">
              <span className="inline-flex items-center gap-2 text-gray-600">
                <Calendar className="h-4 w-4 text-blue-500" /> Start date
              </span>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => updateFilters((prev) => ({ ...prev, startDate: e.target.value }))}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label className="flex flex-col gap-2 text-xs font-medium text-gray-600">
              <span className="inline-flex items-center gap-2 text-gray-600">
                <Calendar className="h-4 w-4 text-blue-500" /> End date
              </span>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => updateFilters((prev) => ({ ...prev, endDate: e.target.value }))}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </label>

            <label className="flex flex-col gap-2 text-xs font-medium text-gray-600 sm:col-span-2">
              <span className="inline-flex items-center gap-2 text-gray-600">
                <DollarSign className="h-4 w-4 text-blue-500" /> Minimum total value (USD)
              </span>
              <input
                type="number"
                min="0"
                value={filters.minValue}
                placeholder="e.g. 5000"
                onChange={(e) => updateFilters((prev) => ({ ...prev, minValue: e.target.value }))}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </label>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )

  const renderSummary = () => (
    <div className="grid grid-cols-2 gap-3 pt-4 border-t border-gray-200">
      <div className="text-center">
        <div className="text-2xl font-bold text-gray-800">{summaryStats.total}</div>
        <div className="text-xs text-gray-500">Filtered Results</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-gray-800">
          {summaryStats.maxValue != null ? `$${summaryStats.maxValue.toLocaleString()}` : '—'}
        </div>
        <div className="text-xs text-gray-500">Highest PO Value</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-semibold text-blue-600">{summaryStats.gmail}</div>
        <div className="text-xs text-gray-500">Gmail Matches</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-semibold text-indigo-600">{summaryStats.drive}</div>
        <div className="text-xs text-gray-500">Drive Matches</div>
      </div>
    </div>
  )

  return (
    <div className="glass rounded-2xl shadow-xl border border-white/20 p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Search Purchase Orders</h2>
          <p className="text-sm text-gray-600">Find POs by number, client, or keywords</p>
        </div>
        <MotionGlassButton
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="button"
          variant="ghost"
          icon={Filter}
          className={`px-3 py-2 text-xs font-medium ${showFilters ? 'text-blue-600' : ''}`}
          aria-label="Filters"
          onClick={() => setShowFilters((prev) => !prev)}
        >
          {showFilters ? 'Hide Filters' : 'Filters'}
        </MotionGlassButton>
      </div>

      {/* Search Form */}
      <form onSubmit={onSubmit} className="relative">
        <div className="relative">
          <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
            <Search className="w-5 h-5 text-gray-400" />
          </div>
          <input
            ref={inputRef}
            className="w-full pl-12 pr-40 py-4 rounded-full border border-gray-200 bg-white/90 backdrop-blur-sm shadow-inner placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 transition"
            placeholder="Search by PO number, client name, keywords..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setShowSuggestions(e.target.value.length > 0)
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            disabled={loading}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center space-x-2">
            {query && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={clearSearch}
                className="p-1 rounded-full hover:bg-gray-100 transition-colors"
              >
                <span className="text-gray-400 text-lg">&times;</span>
              </motion.button>
            )}
            <MotionGlassButton
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={loading || !query.trim()}
              loading={loading}
              icon={Search}
              className="px-6 py-2.5 text-sm font-semibold"
            >
              {loading ? 'Searching...' : 'Search'}
            </MotionGlassButton>
          </div>
        </div>
        
        <SearchSuggestions />
      </form>

      {renderFilters()}

      {filterTouched && rawResults.length > 0 && filteredResults.length === 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-700">
          Filters are currently hiding all results. Adjust or reset them to see your matches.
        </div>
      )}

      {/* Status Messages */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-start space-x-3 p-4 bg-red-50 border border-red-200 rounded-xl"
          >
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-700 text-sm font-medium">Search Error</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </motion.div>
        )}

        {lastSearch && !loading && !error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center space-x-3 p-4 bg-green-50 border border-green-200 rounded-xl"
          >
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <div>
              <p className="text-green-700 text-sm font-medium">Search completed</p>
              <p className="text-green-600 text-sm">Found results for "{lastSearch}"</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quick Stats */}
      {renderSummary()}
    </div>
  )
}
