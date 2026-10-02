/**
 * frontend/src/hooks/v2/useTutor.js — Personal AI Tutor Hook.
 * Manages conversational state, compact context loading, bounded history,
 * suggested actions, and robust fallback handling.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { tutorV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'

const DEFAULT_WELCOME = {
  id: 'welcome-1',
  role: 'assistant',
  content: "Hi there! I'm your Personal Learning Companion. 🌟\n\nI can help you understand tricky words, give you clues on reading questions, or practice spelling together!",
  followUpQuestion: 'What would you like to explore today?',
  suggestedAction: {
    type: 'open_reading_coach',
    label: 'Explore Reading Stories',
    payload: {},
  },
  source: 'offline-fallback',
  timestamp: Date.now(),
}

export function useTutor(initialPassageId = null, initialWord = null) {
  const { locale } = useTranslation()
  const [messages, setMessages] = useState([DEFAULT_WELCOME])
  const [context, setContext] = useState(null)
  const [activePassageId, setActivePassageId] = useState(initialPassageId)
  const [activeWord, setActiveWord] = useState(initialWord)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const isMounted = useRef(true)

  // 1. Load compact pedagogical context
  const refreshContext = useCallback(async (passageId = activePassageId, word = activeWord) => {
    try {
      const data = await tutorV2API.getContext({
        activePassageId: passageId || undefined,
        activeWord: word || undefined,
        language: locale,
      })
      if (isMounted.current && data) {
        setContext(data)
      }
    } catch (err) {
      console.warn('Could not load tutor context:', err?.message)
    }
  }, [activePassageId, activeWord, locale])

  // 2. Load conversation history
  const loadHistory = useCallback(async () => {
    try {
      const res = await tutorV2API.getHistory({ limit: 16 })
      if (isMounted.current && res?.messages && res.messages.length > 0) {
        setMessages(res.messages)
      }
    } catch (err) {
      console.warn('Could not load tutor history:', err?.message)
    }
  }, [])

  useEffect(() => {
    isMounted.current = true
    loadHistory()
    refreshContext(initialPassageId, initialWord)
    return () => {
      isMounted.current = false
    }
  }, [loadHistory, refreshContext, initialPassageId, initialWord])

  // 3. Send student message
  const sendMessage = useCallback(
    async (text, overrideOptions = {}) => {
      const messageText = (text || '').trim()
      if (!messageText) return null

      setLoading(true)
      setError(null)

      const passageId = overrideOptions.activePassageId ?? activePassageId
      const word = overrideOptions.activeWord ?? activeWord

      // Temporary local user message
      const tempUserMsg = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: messageText,
        timestamp: Date.now(),
      }

      setMessages((prev) => [...prev, tempUserMsg])

      try {
        // Build recent history slice (up to 4 turns)
        const historySlice = messages.slice(-4).map((m) => ({
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content || '',
        }))

        const response = await tutorV2API.sendMessage({
          message: messageText,
          activePassageId: passageId || undefined,
          activeWord: word || undefined,
          history: historySlice,
          language: locale,
        })

        if (isMounted.current && response) {
          const assistantMsg = {
            id: `asst-${Date.now()}`,
            role: 'assistant',
            content: response.message,
            explanation: response.explanation,
            suggestedAction: response.suggestedAction,
            followUpQuestion: response.followUpQuestion,
            source: response.source,
            timestamp: response.timestamp || Date.now(),
          }
          setMessages((prev) => [...prev, assistantMsg])
          // Refresh context if needed
          refreshContext(passageId, word)
          return response
        }
      } catch (err) {
        console.error('Tutor send error:', err)
        const errMsg = err?.response?.data?.detail || err?.message || 'Trouble connecting to tutor.'
        if (isMounted.current) {
          setError(errMsg)
          // Add helpful offline fallback message bubble so child is never left stranded
          const fallbackMsg = {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: "I'm having a little trouble connecting right now, but don't worry! Let's take it one step at a time.",
            suggestedAction: {
              type: 'open_reading_coach',
              label: 'Open Reading Stories',
              payload: {},
            },
            followUpQuestion: 'Would you like to try asking again or practice a reading story?',
            source: 'offline-fallback',
            timestamp: Date.now(),
          }
          setMessages((prev) => [...prev, fallbackMsg])
        }
      } finally {
        if (isMounted.current) {
          setLoading(false)
        }
      }
      return null
    },
    [activePassageId, activeWord, messages, refreshContext, locale]
  )

  // 4. Clear conversation history
  const clearHistory = useCallback(async () => {
    try {
      await tutorV2API.clearHistory()
      if (isMounted.current) {
        setMessages([DEFAULT_WELCOME])
      }
    } catch (err) {
      console.warn('Could not clear history:', err)
      if (isMounted.current) {
        setMessages([DEFAULT_WELCOME])
      }
    }
  }, [])

  return {
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
    refreshContext,
  }
}

export default useTutor
