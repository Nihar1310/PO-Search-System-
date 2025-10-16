import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Filter, Clock, AlertCircle, CheckCircle2 } from 'lucide-react'
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
  const inputRef = useRef(null)

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
      onResults(res)
      
      if (!res.length) {
        setError('No POs matched your search. Try syncing your Gmail/Drive or using different keywords.')
      }
    } catch (e) {
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
          className="px-3 py-2 text-xs font-medium"
          aria-label="Filter"
        >
          Filters
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
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-800">0</div>
          <div className="text-xs text-gray-500">Total POs</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-800">0</div>
          <div className="text-xs text-gray-500">This Month</div>
        </div>
      </div>
    </div>
  )
}
