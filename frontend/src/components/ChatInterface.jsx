import { useState, useRef, useEffect, useMemo, useCallback, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles, Search, FileText, Trash2 } from 'lucide-react'
import { searchPOs, sendChatMessage } from '../services/api'
import GlassButton from './GlassButton'

const MotionGlassButton = motion(GlassButton)

const STAGGER_STEP = 0.045
const MAX_STAGGER_DELAY = 0.35

const markdownComponents = {
  p: ({ node, ...props }) => (
    <p className="mb-2 last:mb-0" {...props} />
  ),
  ul: ({ node, ...props }) => (
    <ul className="mb-2 list-disc list-inside space-y-1" {...props} />
  ),
  ol: ({ node, ...props }) => (
    <ol className="mb-2 list-decimal list-inside space-y-1" {...props} />
  ),
  li: ({ node, ...props }) => (
    <li className="leading-relaxed" {...props} />
  ),
  a: ({ node, ...props }) => (
    <a className="text-blue-600 underline hover:text-blue-700" target="_blank" rel="noreferrer" {...props} />
  ),
  code: ({ node, inline, ...props }) =>
    inline ? (
      <code className="rounded bg-gray-100 px-1 py-0.5 text-xs" {...props} />
    ) : (
      <code className="block rounded-md bg-gray-900/90 px-3 py-2 text-xs text-white" {...props} />
    )
}

const generateMessageId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2, 9)}`
}

const buildMessage = (message, indexForDelay = 0) => ({
  ...message,
  id: message.id ?? generateMessageId(),
  animationDelay:
    message.animationDelay ?? Math.min(indexForDelay * STAGGER_STEP, MAX_STAGGER_DELAY)
})

const MessageBubble = memo(function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isSystem = message.isSystemMessage
  const delay = message.animationDelay ?? 0

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.28, ease: 'easeOut', delay }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div className={`flex items-start space-x-3 max-w-[80%] ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-blue-600'
              : isSystem
                ? 'bg-gradient-to-br from-purple-500 to-purple-600'
                : 'bg-gradient-to-br from-gray-500 to-gray-600'
          }`}
        >
          {isUser ? (
            <User className="w-4 h-4 text-white" />
          ) : isSystem ? (
            <Search className="w-4 h-4 text-white" />
          ) : (
            <Bot className="w-4 h-4 text-white" />
          )}
        </div>

        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
              : isSystem
                ? 'bg-gradient-to-br from-purple-50 to-purple-100 text-purple-800 border border-purple-200'
                : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
          }`}
        >
          <ReactMarkdown
            className={`chat-markdown text-sm leading-relaxed ${isUser ? 'chat-markdown--user text-white' : 'text-gray-800'}`}
            components={markdownComponents}
          >
            {message.content || ''}
          </ReactMarkdown>
          {message.structuredData && (
            <div className="mt-2 text-xs opacity-75">Intent: {message.structuredData.intent}</div>
          )}
        </div>
      </div>
    </motion.div>
  )
})

export default function ChatInterface({ onResults }) {
  const [messages, setMessages] = useState(() => [
    buildMessage({
      role: 'assistant',
      content:
        'Hello! I\'m your AI assistant for PO search. You can ask me things like "Find Metso firebrick orders from January" or "Show me all POs from last month".',
      timestamp: new Date(),
      animationDelay: 0
    })
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [conversationId, setConversationId] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const activeRequestRef = useRef(null)

  const adjustTextareaHeight = useCallback(() => {
    if (!inputRef.current) return
    const el = inputRef.current
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [])

  const appendMessage = useCallback((message) => {
    setMessages((prev) => [...prev, buildMessage(message, prev.length)])
  }, [])

  const resetConversation = useCallback(() => {
    setMessages([
      buildMessage({
        role: 'assistant',
        content:
          'Hello! I\'m your AI assistant for PO search. You can ask me things like "Find Metso firebrick orders from January" or "Show me all POs from last month".',
        timestamp: new Date(),
        animationDelay: 0
      }, 0)
    ])
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    adjustTextareaHeight()
  }, [input, adjustTextareaHeight])

  const handleSend = async (e) => {
    e.preventDefault()
    const messageText = input.trim()
    if (!messageText || loading) return

    const requestToken = Symbol('chatRequest')
    activeRequestRef.current = requestToken

    appendMessage({
      role: 'user',
      content: messageText,
      timestamp: new Date()
    })
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const res = await sendChatMessage(messageText, conversationId)
      if (activeRequestRef.current !== requestToken) {
        return
      }

      if (res.conversation_id) {
        setConversationId(res.conversation_id)
      }

      appendMessage({
        role: 'assistant',
        content: res.response,
        timestamp: new Date(),
        structuredData: res.structured_data
      })

      if (res.structured_data?.intent === 'search' && res.structured_data?.query) {
        try {
          const searchResults = await searchPOs(res.structured_data.query)
          if (activeRequestRef.current !== requestToken) {
            return
          }

          onResults(searchResults)
          
          if (!searchResults.length) {
            appendMessage({
              role: 'assistant',
              content:
                '🔍 No matching POs found yet. Try syncing your Gmail/Drive or refining your search query.',
              timestamp: new Date(),
              isSystemMessage: true
            })
          } else if (!res.response?.toLowerCase().includes('found')) {
            appendMessage({
              role: 'assistant',
              content: `✅ Found ${searchResults.length} matching PO${
                searchResults.length > 1 ? 's' : ''
              }! Check the results panel on the left.`,
              timestamp: new Date(),
              isSystemMessage: true
            })
          }
        } catch (searchErr) {
          if (activeRequestRef.current !== requestToken) {
            return
          }
          appendMessage({
            role: 'assistant',
            content: '⚠️ Failed to search. Please check your backend connectivity.',
            timestamp: new Date(),
            isSystemMessage: true
          })
        }
      }
    } catch (err) {
      if (activeRequestRef.current !== requestToken) {
        return
      }
      appendMessage({
        role: 'assistant',
        content: '❌ Error contacting backend. Please check your connection.',
        timestamp: new Date(),
        isSystemMessage: true
      })
      setError('Chat request failed. Check server logs or API key configuration.')
    } finally {
      if (activeRequestRef.current === requestToken) {
        setLoading(false)
        activeRequestRef.current = null
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e)
    }
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

  const renderedMessages = useMemo(
    () => messages.map((message) => <MessageBubble key={message.id} message={message} />),
    [messages]
  )

  const handleClearChat = () => {
    resetConversation()
    setConversationId(null)
    setError(null)
    setLoading(false)
    activeRequestRef.current = null
    setInput('')
    onResults?.([])
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(() => {
        inputRef.current?.focus()
        adjustTextareaHeight()
      })
    } else {
      inputRef.current?.focus()
      adjustTextareaHeight()
    }
  }

  return (
    <div className="glass rounded-2xl shadow-xl border border-white/20 flex flex-col h-[70vh] overflow-hidden">
      {/* Header */}
      <div className="gradient-primary p-4 rounded-t-2xl">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold">AI PO Assistant</h3>
              <p className="text-white/80 text-sm">Ask me anything about your purchase orders</p>
            </div>
          </div>
          <GlassButton
            type="button"
            variant="ghost"
            icon={Trash2}
            className="text-white/90 hover:text-white/100 hover:bg-white/10"
            onClick={handleClearChat}
            disabled={messages.length === 1 && !conversationId && !error && !loading}
          >
            Clear chat
          </GlassButton>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <AnimatePresence initial={false} mode="sync">
          {renderedMessages}
        </AnimatePresence>
        
        {loading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/20">
        <form onSubmit={handleSend} className="flex gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              rows={2}
              className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm input-focus placeholder-gray-500 text-sm resize-none"
              placeholder="Ask e.g. 'Metso firebrick order from Jan' or 'Show me all POs from last month'. Press Shift+Enter for a new line."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{ minHeight: '3rem', maxHeight: '10rem' }}
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
