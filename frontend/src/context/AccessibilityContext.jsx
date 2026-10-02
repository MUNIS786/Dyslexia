/**
 * frontend/src/context/AccessibilityContext.jsx
 *
 * Centralized Accessibility & Personalization Provider for DyslexAid V2.
 * Manages typography ergonomics, focus tools (reading ruler), visual stress tints,
 * high-contrast display, reduced motion, and child-friendly text-to-speech preferences.
 * Automatically synchronizes CSS variables, body classes, localStorage, and backend persistence.
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { accessibilityV2API } from '../api/v2/client'
import { useAuth } from './AuthContext'

export const DEFAULT_ACCESSIBILITY_PREFERENCES = {
  font: 'OpenDyslexic, Lexend, sans-serif',
  fontSize: 18,
  lineSpacing: 2.0,
  letterSpacing: 0.08,
  wordSpacing: 0.05,
  contentWidth: 'standard', // 'standard' (max-w-4xl) | 'narrow' (max-w-xl) | 'compact' (max-w-2xl)
  bgColor: '#FFF8F0',
  textColor: '#1A2A2A',
  highContrast: false,
  reducedMotion: false,
  readingRuler: false,
  rulerSize: 60,
  rulerColor: 'amber', // 'amber' | 'cyan' | 'yellow' | 'gray'
  tintOverlay: 'none', // 'none' | 'peach' | 'mint' | 'sky' | 'butter'
  ttsSpeed: 0.85,
  ttsLanguage: 'en-IN',
  highlightWords: true,
  showBulletPoints: true,
  autoSimplify: true,
}

const STORAGE_KEY = 'dyslexaid_accessibility_preferences'

const AccessibilityContext = createContext(null)

export function applyAccessibilityDOM(prefs = {}) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  const body = document.body

  if (prefs.font) {
    const fontVal = prefs.font.includes(',') ? prefs.font : `${prefs.font}, Lexend, sans-serif`
    root.style.setProperty('--font-family', fontVal)
  }
  if (prefs.fontSize) {
    root.style.setProperty('--font-size', `${prefs.fontSize}px`)
  }
  if (prefs.lineSpacing) {
    root.style.setProperty('--line-spacing', String(prefs.lineSpacing))
  }
  if (prefs.letterSpacing !== undefined) {
    root.style.setProperty('--letter-spacing', `${prefs.letterSpacing}em`)
  }
  if (prefs.wordSpacing !== undefined) {
    root.style.setProperty('--word-spacing', `${prefs.wordSpacing}em`)
  }
  if (prefs.contentWidth) {
    const maxWidthMap = {
      narrow: '36rem',
      compact: '44rem',
      standard: '56rem',
    }
    root.style.setProperty('--reading-max-width', maxWidthMap[prefs.contentWidth] || '56rem')
  }
  if (prefs.rulerSize) {
    root.style.setProperty('--ruler-height', `${prefs.rulerSize}px`)
  }
  if (prefs.rulerColor) {
    const colorMap = {
      amber: '#E8A020',
      cyan: '#06b6d4',
      yellow: '#eab308',
      gray: '#6b7280',
    }
    root.style.setProperty('--ruler-color', colorMap[prefs.rulerColor] || '#E8A020')
  }

  // High contrast & reduced motion toggles
  if (body) {
    body.classList.toggle('high-contrast', !!prefs.highContrast)
    body.classList.toggle('reduced-motion', !!prefs.reducedMotion)

    if (prefs.highContrast) {
      body.style.backgroundColor = '#FFFFFF'
      body.style.color = '#000000'
    } else {
      if (prefs.bgColor) {
        root.style.setProperty('--bg-color', prefs.bgColor)
        body.style.backgroundColor = prefs.bgColor
      }
      if (prefs.textColor) {
        root.style.setProperty('--text-color', prefs.textColor)
        body.style.color = prefs.textColor
      }
    }
  }
}

export function AccessibilityProvider({ children }) {
  const { user, token } = useAuth()
  const [preferences, setPreferencesState] = useState(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY)
      if (cached) {
        const parsed = JSON.parse(cached)
        return { ...DEFAULT_ACCESSIBILITY_PREFERENCES, ...parsed }
      }
    } catch {
      // LocalStorage access issues
    }
    return DEFAULT_ACCESSIBILITY_PREFERENCES
  })

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  // Apply initial DOM properties on mount and when preferences change
  useEffect(() => {
    applyAccessibilityDOM(preferences)
  }, [preferences])

  // Sync from backend when user logs in
  useEffect(() => {
    if (!token) return

    let cancelled = false
    setLoading(true)

    accessibilityV2API
      .getPreferences()
      .then((data) => {
        if (!cancelled && data && data.preferences) {
          const merged = { ...DEFAULT_ACCESSIBILITY_PREFERENCES, ...data.preferences }
          setPreferencesState(merged)
          applyAccessibilityDOM(merged)
          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
          } catch {}
        }
      })
      .catch((err) => {
        console.warn('[AccessibilityContext] Could not fetch remote preferences:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [token, user?.id])

  // Optimistic single-key preference update
  const updatePreference = useCallback((key, value) => {
    setPreferencesState((prev) => {
      const next = { ...prev, [key]: value }
      applyAccessibilityDOM(next)
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      } catch {}
      return next
    })

    if (token) {
      accessibilityV2API
        .patchPreferences({ [key]: value })
        .catch((err) => {
          console.warn(`[AccessibilityContext] Error saving preference ${key}:`, err)
        })
    }
  }, [token])

  // Batch update all preferences
  const updateAllPreferences = useCallback(async (newPrefs) => {
    setSaving(true)
    setError(null)
    const merged = { ...preferences, ...newPrefs }

    // Immediate optimistic local update
    setPreferencesState(merged)
    applyAccessibilityDOM(merged)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
    } catch {}

    if (token) {
      try {
        const res = await accessibilityV2API.updatePreferences(merged)
        if (res && res.preferences) {
          const finalPrefs = { ...DEFAULT_ACCESSIBILITY_PREFERENCES, ...res.preferences }
          setPreferencesState(finalPrefs)
          applyAccessibilityDOM(finalPrefs)
          localStorage.setItem(STORAGE_KEY, JSON.stringify(finalPrefs))
        }
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to save preferences to server.')
        throw err
      } finally {
        setSaving(false)
      }
    } else {
      setSaving(false)
    }
  }, [preferences, token])

  // Reset to canonical factory defaults
  const resetDefaults = useCallback(async () => {
    setSaving(true)
    setError(null)

    setPreferencesState(DEFAULT_ACCESSIBILITY_PREFERENCES)
    applyAccessibilityDOM(DEFAULT_ACCESSIBILITY_PREFERENCES)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_ACCESSIBILITY_PREFERENCES))
    } catch {}

    if (token) {
      try {
        await accessibilityV2API.resetPreferences()
      } catch (err) {
        console.warn('[AccessibilityContext] Reset failed on server:', err)
      } finally {
        setSaving(false)
      }
    } else {
      setSaving(false)
    }
  }, [token])

  const contextValue = useMemo(() => ({
    preferences,
    updatePreference,
    updateAllPreferences,
    resetDefaults,
    loading,
    saving,
    error,
  }), [preferences, updatePreference, updateAllPreferences, resetDefaults, loading, saving, error])

  return (
    <AccessibilityContext.Provider value={contextValue}>
      {children}
    </AccessibilityContext.Provider>
  )
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext)
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider')
  }
  return context
}

export default AccessibilityContext
