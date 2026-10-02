/**
 * frontend/src/components/shared/LanguageSelector.jsx — Accessible Multilingual Language Selector.
 * Displays recognizable native language names (English, मराठी, हिन्दी) with keyboard accessibility.
 */
import { useState, useRef, useEffect } from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function LanguageSelector({ variant = 'header', className = '' }) {
  const { locale, setLocale, supportedLocales, activeLocaleMeta, t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const handleSelect = (code) => {
    setLocale(code)
    setIsOpen(false)
  }

  if (variant === 'select') {
    return (
      <div className={`relative inline-block ${className}`}>
        <label htmlFor="language-select" className="sr-only">
          {t('common.selectLanguage')}
        </label>
        <select
          id="language-select"
          value={locale}
          onChange={(e) => setLocale(e.target.value)}
          className="appearance-none bg-white border border-stone-300 text-stone-800 text-sm font-semibold rounded-xl px-3 py-1.5 pr-8 hover:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600 shadow-sm cursor-pointer"
          aria-label={t('common.selectLanguage')}
        >
          {supportedLocales.map((loc) => (
            <option key={loc.code} value={loc.code}>
              {loc.nativeName} ({loc.name})
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-500 text-xs">
          ▼
        </span>
      </div>
    )
  }

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      <button
        type="button"
        id="language-selector-button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={`${t('common.language')}: ${activeLocaleMeta.nativeName}`}
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-stone-200 bg-white/90 hover:bg-stone-50 text-stone-800 text-xs sm:text-sm font-bold shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-teal-600"
      >
        <span className="text-base" aria-hidden="true">🌐</span>
        <span className="tracking-wide">{activeLocaleMeta.nativeName}</span>
        <span className="text-[10px] text-stone-400 ml-0.5" aria-hidden="true">
          {isOpen ? '▲' : '▼'}
        </span>
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-label={t('common.selectLanguage')}
          className="absolute right-0 mt-2 w-44 rounded-2xl bg-white shadow-xl border border-stone-200 py-1.5 z-50 focus:outline-none animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-3 py-1 text-[11px] font-bold text-stone-400 uppercase tracking-wider border-b border-stone-100 mb-1">
            {t('common.selectLanguage')}
          </div>
          {supportedLocales.map((loc) => {
            const isSelected = loc.code === locale
            return (
              <button
                key={loc.code}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(loc.code)}
                className={`w-full text-left px-3 py-2 text-xs sm:text-sm font-semibold flex items-center justify-between transition-colors ${
                  isSelected
                    ? 'bg-teal-50 text-teal-900 font-bold'
                    : 'text-stone-700 hover:bg-stone-50 hover:text-stone-900'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-base" aria-hidden="true">{loc.flag}</span>
                  <div>
                    <span className="block leading-tight">{loc.nativeName}</span>
                    <span className="block text-[11px] text-stone-400 font-normal">{loc.name}</span>
                  </div>
                </div>
                {isSelected && (
                  <span className="text-teal-700 font-bold text-xs" aria-hidden="true">
                    ✓
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
