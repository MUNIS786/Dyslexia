/**
 * frontend/src/features/tutor/TutorChat.jsx
 *
 * Primary interactive container for the V2 Personal AI Tutor.
 * Features:
 * - Dynamic context awareness (active story excerpt, target word, learning level)
 * - Child-friendly conversational stream with progressive hints
 * - Quick prompt chips to eliminate blank-page paralysis
 * - One-click execution of suggested pedagogical next actions
 * - Resilient offline fallback support
 */
import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTutor } from '../../hooks/v2/useTutor'
import TutorMessageBubble from './TutorMessageBubble'
import TutorPromptChips from './TutorPromptChips'
import TutorContextBadge from './TutorContextBadge'

export default function TutorChat({
  initialPassageId = null,
  initialWord = null,
  studentName = 'Learner',
}) {
  const navigate = useNavigate()
  const [inputText, setInputText] = useState('')
  const messagesEndRef = useRef(null)

  const {
    messages,
    context,
    activePassageId,
    activeWord,
    setActivePassageId,
    setActiveWord,
    loading,
    error,
    sendMessage,
    clearHistory,
  } = useTutor(initialPassageId, initialWord)

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (e) => {
    e?.preventDefault()
    const text = inputText.trim()
    if (!text || loading) return

    setInputText('')
    await sendMessage(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSelectPrompt = (promptText) => {
    if (loading) return
    sendMessage(promptText)
  }

  const handleExecuteAction = (action) => {
    if (!action) return
    const { type, payload } = action

    if (type === 'open_reading_coach' || type === 'read_again' || type === 'try_question') {
      navigate('/student/reading-coach')
    } else if (type === 'start_adaptive_practice') {
      navigate('/student/adaptive-learning')
    } else if (type === 'practice_word') {
      const word = payload?.word || activeWord
      if (word) {
        sendMessage(`Can we practice the word "${word}" together?`)
      }
    } else {
      navigate('/student/reading-coach')
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-h-[820px] bg-stone-100/60 rounded-3xl border border-stone-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 bg-white border-b border-stone-200 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-teal-500 text-white flex items-center justify-center shadow-xs text-xl">
            🤖
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base sm:text-lg font-extrabold text-stone-900 leading-tight">
                Personal AI Tutor
              </h2>
              <span className="flex items-center gap-1 text-[11px] font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-200">
                <span>✨</span>
                <span>V2 Companion</span>
              </span>
            </div>
            <p className="text-xs text-stone-500 hidden sm:block">
              Your patient, step-by-step reading and word guide
            </p>
          </div>
        </div>

        <button
          onClick={clearHistory}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-stone-500 hover:text-stone-800 hover:bg-stone-100 rounded-xl transition-all cursor-pointer"
          title="Reset conversation"
        >
          <span>🔄</span>
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>

      {/* Context Badge Ribbon */}
      <div className="px-4 sm:px-6 py-2 bg-stone-50/80 border-b border-stone-200 shrink-0">
        <TutorContextBadge
          context={context}
          activePassageTitle={context?.currentPassage?.title}
          activeWord={activeWord}
          onClearPassage={activePassageId ? () => setActivePassageId(null) : null}
          onClearWord={activeWord ? () => setActiveWord(null) : null}
        />
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-2">
        {messages.map((msg, index) => (
          <TutorMessageBubble
            key={msg.id || index}
            message={msg}
            onExecuteAction={handleExecuteAction}
            studentName={studentName}
          />
        ))}

        {loading && (
          <div className="flex items-center gap-2.5 text-stone-500 text-xs sm:text-sm font-medium py-2 px-3 bg-white/70 rounded-2xl w-fit border border-stone-200 animate-pulse">
            <span className="animate-spin inline-block">⏳</span>
            <span>Thinking of the best explanation...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-xs text-amber-800 bg-amber-50 p-2.5 rounded-xl border border-amber-200">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts & Input Area */}
      <div className="p-3 sm:p-4 bg-white border-t border-stone-200 shrink-0 space-y-2">
        <TutorPromptChips onSelectPrompt={handleSelectPrompt} disabled={loading} />

        <form onSubmit={handleSend} className="flex items-center gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about a word, sentence, or story..."
            disabled={loading}
            className="flex-1 px-4 py-3 rounded-2xl bg-stone-50 border border-stone-300 focus:border-teal-500 focus:bg-white focus:outline-hidden text-sm sm:text-base font-medium text-stone-900 transition-all placeholder:text-stone-400"
          />

          <button
            type="submit"
            disabled={!inputText.trim() || loading}
            className="p-3 bg-[#1A6B6B] hover:bg-[#145555] active:scale-95 disabled:opacity-40 disabled:hover:bg-[#1A6B6B] text-white rounded-2xl transition-all shadow-xs cursor-pointer shrink-0 font-bold"
            title="Send message"
          >
            ➔
          </button>
        </form>
      </div>
    </div>
  )
}
