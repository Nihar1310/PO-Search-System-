import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FileText, 
  Calendar, 
  Building2, 
  DollarSign, 
  ChevronDown, 
  ChevronUp, 
  Download, 
  Eye, 
  Clock,
  Mail,
  HardDrive,
  Tag,
  Package
} from 'lucide-react'
import GlassButton from './GlassButton'
import { getPODetails } from '../services/api'

const MotionGlassButton = motion(GlassButton)

export default function POResultCard({ po, index = 0 }) {
  const [expanded, setExpanded] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const [details, setDetails] = useState(po)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState(null)

  useEffect(() => {
    setDetails(po)
    setDetailsError(null)
  }, [po])

  useEffect(() => {
    const needsFetch = !details?.parsed_data || Object.keys(details.parsed_data || {}).length === 0
    if (!expanded || !po?.id || !needsFetch) {
      return
    }

    let cancelled = false
    const fetchDetails = async () => {
      setDetailsLoading(true)
      setDetailsError(null)
      try {
        const fullDetails = await getPODetails(po.id)
        if (!cancelled && fullDetails) {
          setDetails((prev) => ({ ...prev, ...fullDetails }))
        }
      } catch (err) {
        if (!cancelled) {
          setDetailsError('Failed to load full PO details.')
        }
      } finally {
        if (!cancelled) {
          setDetailsLoading(false)
        }
      }
    }

    fetchDetails()

    return () => {
      cancelled = true
    }
  }, [expanded, po?.id, details?.parsed_data])

  const resolved = details || po
  const parsed = resolved?.parsed_data || {}
  const items = parsed.line_items || parsed.items || []

  const getSourceIcon = (source) => {
    switch (source?.toLowerCase()) {
      case 'gmail':
        return <Mail className="w-4 h-4" />
      case 'drive':
        return <HardDrive className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  const getSourceColor = (source) => {
    switch (source?.toLowerCase()) {
      case 'gmail':
        return 'text-red-500 bg-red-50'
      case 'drive':
        return 'text-blue-500 bg-blue-50'
      default:
        return 'text-gray-500 bg-gray-50'
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '—'
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-IN', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
      })
    } catch {
      return dateString
    }
  }

  const handleExport = () => {
      const dataStr = JSON.stringify(resolved, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${po.po_number || 'po'}-${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      whileHover={{ y: -2 }}
      className="glass rounded-[20px] shadow-lg border border-white/20 overflow-hidden card-hover"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header */}
      <div className="p-6 border-b border-white/20">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-[12px] bg-gradient-to-br from-electric-500 to-sky-400 flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div className="min-w-0">
                <h3 className="text-[17px] font-semibold text-gray-900 leading-6 truncate">
                  {resolved.client_name || parsed.client_name || 'Unknown Supplier'}
                </h3>
                <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[12px] text-gray-600">
                  <span className="font-medium text-gray-700">{resolved.po_number || 'Unknown PO'}</span>
                  <span className="text-gray-300">•</span>
                  <span>{formatDate(resolved.date)}</span>
                  <span className="text-gray-300">•</span>
                  <span>{formatCurrency(resolved.total_value ?? parsed.total_value)}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium flex items-center gap-1 ${getSourceColor(resolved.source)}`}>
              {getSourceIcon(resolved.source)}
              <span className="capitalize">{resolved.source || 'Unknown'}</span>
            </span>
            {resolved.created_at && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700">New</span>
            )}
          </div>
        </div>

        {/* Key Info Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center">
              <Calendar className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="text-[11px] text-gray-500">Date</p>
              <p className="text-sm font-medium text-gray-800">{formatDate(resolved.date)}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center">
              <Building2 className="w-4 h-4 text-purple-600" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] text-gray-500">Client</p>
              <p className="text-sm font-medium text-gray-800 truncate">
                {resolved.client_name || parsed.client_name || 'Unknown'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <p className="text-[11px] text-gray-500">Total Value</p>
              <p className="text-sm font-medium text-gray-800">
                {formatCurrency(resolved.total_value ?? parsed.total_value)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center">
              <Tag className="w-4 h-4 text-orange-600" />
            </div>
            <div>
              <p className="text-[11px] text-gray-500">Items</p>
              <p className="text-sm font-medium text-gray-800">
                {items.length || 0} line items
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 bg-gray-50/50 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <MotionGlassButton
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="button"
            variant="ghost"
            icon={Eye}
            onClick={() => setExpanded(!expanded)}
            className="px-5 py-2 text-sm font-semibold"
          >
            <span className="flex items-center gap-1">
              {expanded ? 'Hide Details' : 'View Details'}
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </span>
          </MotionGlassButton>
          
          <MotionGlassButton
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="button"
            variant="primary"
            icon={Download}
            onClick={handleExport}
            className="px-5 py-2 text-sm font-semibold"
          >
            Export JSON
          </MotionGlassButton>
        </div>

        <div className="text-xs text-gray-500 flex items-center space-x-1">
          <Clock className="w-3 h-3" />
          <span>Created {formatDate(resolved.created_at)}</span>
        </div>
      </div>

      {/* Expanded Details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="p-6 bg-white/50 border-t border-white/20 space-y-6">
              {detailsLoading && (
                <div className="rounded-lg border border-blue-100 bg-blue-50/80 px-3 py-2 text-xs text-blue-700">
                  Loading PO details…
                </div>
              )}

              {detailsError && (
                <div className="rounded-lg border border-red-200 bg-red-50/80 px-3 py-2 text-xs text-red-600">
                  {detailsError}
                </div>
              )}

              {/* Line Items */}
              {items.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center space-x-2">
                    <Package className="w-4 h-4" />
                    <span>Line Items ({items.length})</span>
                  </h4>
                  <div className="space-y-3">
                    {items.map((item, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="p-3 bg-white rounded-lg border border-gray-200"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-800">
                              {item.description || item.name || `Item ${idx + 1}`}
                            </p>
                            <div className="flex items-center space-x-4 mt-1 text-xs text-gray-600">
                              <span>Qty: {item.quantity || 'N/A'}</span>
                              <span>Unit: {formatCurrency(item.unit_price)}</span>
                              <span>Total: {formatCurrency(item.total)}</span>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Payment Terms */}
              {parsed.payment_terms && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-800 mb-2">Payment Terms</h4>
                  <p className="text-sm text-gray-600 bg-white p-3 rounded-lg border border-gray-200">
                    {parsed.payment_terms}
                  </p>
                </div>
              )}

              {/* Raw Text Excerpt */}
              {parsed.raw_text && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-800 mb-2">Document Excerpt</h4>
                  <div className="bg-white p-4 rounded-lg border border-gray-200 max-h-40 overflow-y-auto">
                    <p className="text-xs text-gray-600 whitespace-pre-wrap leading-relaxed">
                      {parsed.raw_text.slice(0, 800)}
                      {parsed.raw_text.length > 800 && '...'}
                    </p>
                  </div>
                </div>
              )}

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                <div>
                  <p className="text-xs text-gray-500 mb-1">PO ID</p>
                  <p className="text-sm font-mono text-gray-700">{resolved.id}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">File ID</p>
                  <p className="text-sm font-mono text-gray-700 truncate">{resolved.file_id || 'N/A'}</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(Number(value))
  } catch (err) {
    return `₹${value}`
  }
}
