import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles, Search, FileText } from 'lucide-react'
import { searchPOs, sendChatMessage } from '../services/api'
import GlassButton from './GlassButton'

const MotionGlassButton = motion(GlassButton)

export default function ChatInterface({ onResults }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant for PO search. You can ask me things like "Find Metso firebrick orders from January" or "Show me all POs from last month".',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [conversationId, setConversationId] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    
    const userMsg = { 
      role: 'user', 
      content: input.trim(),
      timestamp: new Date()
    }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const res = await sendChatMessage(input, conversationId)
      if (res.conversation_id) {
        setConversationId(res.conversation_id)
      }
      const assistantMsg = { 
        role: 'assistant', 
        content: res.response,
        timestamp: new Date(),
        structuredData: res.structured_data
      }
      setMessages((m) => [...m, assistantMsg])

      if (res.structured_data?.intent === 'search' && res.structured_data?.query) {
        try {
          const searchResults = await searchPOs(res.structured_data.query)
          onResults(searchResults)
          
          if (!searchResults.length) {
            const noResultsMsg = {
              role: 'assistant',
              content: '🔍 No matching POs found yet. Try syncing your Gmail/Drive or refining your search query.',
              timestamp: new Date(),
              isSystemMessage: true
            }
            setMessages((m) => [...m, noResultsMsg])
          } else if (!res.response?.toLowerCase().includes('found')) {
            const resultsMsg = {
              role: 'assistant',
              content: `✅ Found ${searchResults.length} matching PO${searchResults.length > 1 ? 's' : ''}! Check the results panel on the left.`,
              timestamp: new Date(),
              isSystemMessage: true
            }
            setMessages((m) => [...m, resultsMsg])
          }
        } catch (searchErr) {
          const errorMsg = {
            role: 'assistant',
            content: '⚠️ Failed to search. Please check your backend connectivity.',
            timestamp: new Date(),
            isSystemMessage: true
          }
          setMessages((m) => [...m, errorMsg])
        }
      }
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: '❌ Error contacting backend. Please check your connection.',
        timestamp: new Date(),
        isSystemMessage: true
      }
      setMessages((m) => [...m, errorMsg])
      setError('Chat request failed. Check server logs or API key configuration.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e)
    }
  }

  const MessageBubble = ({ message, index }) => {
    const isUser = message.role === 'user'
    const isSystem = message.isSystemMessage

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.1 }}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div className={`flex items-start space-x-3 max-w-[80%] ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
          {/* Avatar */}
          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser 
              ? 'bg-gradient-to-br from-blue-500 to-blue-600' 
              : isSystem 
                ? 'bg-gradient-to-br from-purple-500 to-purple-600'
                : 'bg-gradient-to-br from-gray-500 to-gray-600'
          }`}>
            {isUser ? (
              <User className="w-4 h-4 text-white" />
            ) : isSystem ? (
              <Search className="w-4 h-4 text-white" />
            ) : (
              <Bot className="w-4 h-4 text-white" />
            )}
          </div>

          {/* Message Content */}
          <div className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
              : isSystem
                ? 'bg-gradient-to-br from-purple-50 to-purple-100 text-purple-800 border border-purple-200'
                : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
          }`}>
            <div className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </div>
            {message.structuredData && (
              <div className="mt-2 text-xs opacity-75">
                Intent: {message.structuredData.intent}
              </div>
            )}
          </div>
        </div>
      </motion.div>
    )
  }

  const TypingIndicator = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-start mb-4"
    >
      <div className="flex items-start space-x-3 max-w-[80%]">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-gray-500 to-gray-600 flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
        <div className="px-4 py-3 rounded-2xl bg-white border border-gray-200 shadow-sm">
          <div className="typing-indicator">
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        </div>
      </div>
    </motion.div>
  )

  return (
    <div className="glass rounded-2xl shadow-xl border border-white/20 flex flex-col h-[70vh] overflow-hidden">
      {/* Header */}
      <div className="gradient-primary p-4 rounded-t-2xl">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-white font-semibold">AI PO Assistant</h3>
            <p className="text-white/80 text-sm">Ask me anything about your purchase orders</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <AnimatePresence>
          {messages.map((message, index) => (
            <MessageBubble key={index} message={message} index={index} />
          ))}
        </AnimatePresence>
        
        {loading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/20">
        <form onSubmit={handleSend} className="flex gap-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm input-focus placeholder-gray-500 text-sm"
              placeholder="Ask e.g. 'Metso firebrick order from Jan' or 'Show me all POs from last month'"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
            />
            <FileText className="absolute right-4 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          </div>
          <MotionGlassButton
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={loading || !input.trim()}
            loading={loading}
            icon={Send}
            className="px-6 py-2.5 text-sm font-semibold"
          >
            {loading ? 'Sending…' : 'Send'}
          </MotionGlassButton>
        </form>
        
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg"
          >
            <p className="text-red-600 text-sm">{error}</p>
          </motion.div>
        )}
      </div>
    </div>
  )
}
