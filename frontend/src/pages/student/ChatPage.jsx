import { useState, useRef, useEffect } from 'react'
import { chatAPI } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { PageHeader, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

const QUICK_REPLIES = [
  'What is dyslexia?',
  'How do I scan text?',
  'Show my progress tips',
  'Does this work offline?',
  'Tell me about my plan',
]

export default function ChatPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hi ${user?.name?.split(' ')[0] || 'there'}! 👋 I'm your DyslexAid assistant. I can help you understand dyslexia, use this app, and learn better. What would you like to know?`,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')
    const history = messages.map((m) => ({ role: m.role, content: m.content }))
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setLoading(true)
    try {
      const res = await chatAPI.send(msg, history)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }])
    } catch {
      toast.error('Could not get a response. Try again.')
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I had trouble connecting. Please try again! 😊' },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <PageHeader icon="💬" title="AI Assistant" subtitle="Ask me anything about reading and learning." />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-4 pb-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.role === 'assistant' && (
              <div className="w-9 h-9 rounded-full bg-[#1A6B6B] flex items-center justify-center text-lg shrink-0">
                🤖
              </div>
            )}
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl dyslexia-text text-sm leading-relaxed
                ${m.role === 'user'
                  ? 'bg-[#1A6B6B] text-white rounded-br-sm'
                  : 'bg-white border border-[#E5E0D8] text-[var(--text-color)] rounded-bl-sm shadow-sm'
                }`}
              style={{ lineHeight: 'var(--line-spacing)' }}
            >
              {m.content}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-9 h-9 rounded-full bg-[#1A6B6B] flex items-center justify-center text-lg shrink-0">
              🤖
            </div>
            <div className="bg-white border border-[#E5E0D8] rounded-2xl rounded-bl-sm px-5 py-4 shadow-sm">
              <div className="flex gap-1.5 items-center">
                <div className="w-2 h-2 rounded-full bg-[#1A6B6B] typing-dot" />
                <div className="w-2 h-2 rounded-full bg-[#1A6B6B] typing-dot" />
                <div className="w-2 h-2 rounded-full bg-[#1A6B6B] typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick replies */}
      {messages.length <= 2 && (
        <div className="flex gap-2 flex-wrap mb-3">
          {QUICK_REPLIES.map((qr) => (
            <button
              key={qr}
              onClick={() => sendMessage(qr)}
              disabled={loading}
              className="px-3 py-1.5 rounded-full border border-[#1A6B6B] text-[#1A6B6B] dyslexia-text text-xs
                hover:bg-[#E0F2F2] transition-colors disabled:opacity-50"
            >
              {qr}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 items-end bg-white rounded-2xl border border-[#E5E0D8] p-2 shadow-sm">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendMessage()
            }
          }}
          placeholder="Type your question here…"
          rows={1}
          className="flex-1 px-3 py-2 dyslexia-text resize-none focus:outline-none bg-transparent"
          style={{ lineHeight: 1.5, maxHeight: '120px', overflow: 'auto' }}
        />
        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          className="w-10 h-10 rounded-xl bg-[#1A6B6B] text-white flex items-center justify-center
            hover:bg-[#155858] transition-colors disabled:opacity-50 shrink-0"
        >
          {loading ? <Spinner size="sm" /> : '↑'}
        </button>
      </div>
    </div>
  )
}
