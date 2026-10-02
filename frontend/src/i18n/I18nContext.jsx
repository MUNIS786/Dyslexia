/**
 * frontend/src/i18n/I18nContext.jsx — Central Internationalization (i18n) Provider.
 * Provides accessible, zero-dependency translation with safe fallbacks and persistence.
 */
import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import en from './locales/en'
import mr from './locales/mr'
import hi from './locales/hi'
import { authAPI } from '../api/client'

const DICTIONARIES = { en, mr, hi }

export const SUPPORTED_LOCALES = [
  { code: 'en', name: 'English', nativeName: 'English', speechCode: 'en-IN', flag: '🇬🇧' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', speechCode: 'mr-IN', flag: '🇮🇳' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', speechCode: 'hi-IN', flag: '🇮🇳' },
]

const ALLOWED_CODES = SUPPORTED_LOCALES.map((l) => l.code)

const I18nContext = createContext(null)

/**
 * Resolves a nested key (e.g. 'auth.loginTitle') inside an object.
 */
function getNestedValue(obj, keyPath) {
  if (!obj || !keyPath) return null
  const keys = keyPath.split('.')
  let current = obj
  for (const k of keys) {
    if (current && typeof current === 'object' && k in current) {
      current = current[k]
    } else {
      return null
    }
  }
  return typeof current === 'string' ? current : null
}

/**
 * Interpolates variables in a string: "Hello, {name}!" -> "Hello, Aarav!"
 */
function interpolate(template, params) {
  if (!template || !params) return template
  return template.replace(/\{(\w+)\}/g, (match, paramKey) => {
    return paramKey in params ? String(params[paramKey]) : match
  })
}

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => {
    try {
      const saved = localStorage.getItem('dyslexaid_locale')
      if (saved && ALLOWED_CODES.includes(saved)) {
        return saved
      }
      // Check browser language
      const navLang = navigator.language?.toLowerCase() || ''
      if (navLang.startsWith('mr')) return 'mr'
      if (navLang.startsWith('hi')) return 'hi'
    } catch (e) {
      // LocalStorage access issues
    }
    return 'en'
  })

  // Synchronize document lang attribute
  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const setLocale = useCallback((newLocale, syncBackend = true) => {
    if (!ALLOWED_CODES.includes(newLocale)) {
      console.warn(`[i18n] Unsupported locale '${newLocale}', keeping '${locale}'`)
      return
    }

    setLocaleState(newLocale)
    try {
      localStorage.setItem('dyslexaid_locale', newLocale)
    } catch (e) {
      // Ignore storage errors
    }

    // Optionally sync with backend if user is authenticated
    if (syncBackend) {
      const token = localStorage.getItem('dyslexaid_token')
      if (token) {
        authAPI.updateSettings({ ttsLanguage: `${newLocale}-IN` }).catch(() => {
          // Non-blocking sync error
        })
      }
    }
  }, [locale])

  const t = useCallback((key, params) => {
    const currentDict = DICTIONARIES[locale] || DICTIONARIES.en
    const fallbackDict = DICTIONARIES.en

    // 1. Try active locale dictionary
    let text = getNestedValue(currentDict, key)

    // 2. Fall back to English dictionary if missing
    if (!text && locale !== 'en') {
      text = getNestedValue(fallbackDict, key)
    }

    // 3. Fallback to raw key if completely absent
    if (!text) {
      return key
    }

    // 4. Perform parameter interpolation
    return params ? interpolate(text, params) : text
  }, [locale])

  const activeLocaleMeta = useMemo(() => {
    return SUPPORTED_LOCALES.find((l) => l.code === locale) || SUPPORTED_LOCALES[0]
  }, [locale])

  const value = useMemo(() => ({
    locale,
    setLocale,
    t,
    supportedLocales: SUPPORTED_LOCALES,
    activeLocaleMeta,
  }), [locale, setLocale, t, activeLocaleMeta])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useTranslation() {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useTranslation must be used within an I18nProvider')
  }
  return context
}

export default I18nContext
