/**
 * frontend/src/components/accessibility/AccessibilityToolbar.jsx
 *
 * Fast, accessible quick-controls toolbar embedded in the application top navigation.
 * Allows learners to quickly change text size, toggle the reading ruler, switch contrast,
 * and change color tints on any page without leaving their current task.
 */
import React, { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAccessibility } from '../../context/AccessibilityContext'
import { useTranslation } from '../../i18n/I18nContext'

export default function AccessibilityToolbar() {
  const { preferences, updatePreference, resetDefaults } = useAccessibility()
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef(null)
  const buttonRef = useRef(null)

  const {
    fontSize = 18,
    readingRuler = false,
    highContrast = false,
    reducedMotion = false,
    tintOverlay = 'none',
  } = preferences

  // Close on Escape or click outside
  useEffect(() => {
    if (!isOpen) return

    const handleClickOutside = (e) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target)
      ) {
        setIsOpen(false)
      }
    }

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  return (
    <div className="relative inline-block text-left">
      {/* Trigger Button */}
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`h-10 px-3 flex items-center gap-1.5 rounded-xl border transition-all text-xs font-bold cursor-pointer
          ${
            isOpen || readingRuler || highContrast || tintOverlay !== 'none'
              ? 'bg-amber-100 text-amber-900 border-amber-300 shadow-2xs'
              : 'bg-white text-stone-700 border-stone-200 hover:bg-stone-50'
          }`}
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label={t('accessibility.quickTools', 'Reading & Accessibility Tools')}
        title={t('accessibility.quickTools', 'Reading & Accessibility Tools')}
      >
        <span className="text-base" aria-hidden="true">👓</span>
        <span className="hidden sm:inline">{t('accessibility.readingTools', 'Reading Tools')}</span>
        {(readingRuler || highContrast || tintOverlay !== 'none') && (
          <span className="w-2 h-2 rounded-full bg-amber-600 ml-0.5" aria-label="Active adjustments" />
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          ref={menuRef}
          className="absolute right-0 top-12 w-72 sm:w-80 bg-white rounded-3xl shadow-xl border border-stone-200 p-4 z-50 animate-fade-in space-y-4"
          role="dialog"
          aria-label={t('accessibility.quickTools', 'Reading & Accessibility Tools')}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2 border-b border-stone-100">
            <span className="text-xs font-extrabold uppercase tracking-wider text-teal-800 flex items-center gap-1.5">
              <span>👓</span>
              <span>{t('accessibility.quickTools', 'Reading Tools')}</span>
            </span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-stone-400 hover:text-stone-700 text-sm font-bold px-1"
              aria-label={t('common.close', 'Close')}
            >
              ✕
            </button>
          </div>

          {/* Font Size Adjuster */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-bold text-stone-700">
              <span>{t('accessibility.textSize', 'Text Size')}</span>
              <span className="font-mono text-teal-700">{fontSize}px</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => updatePreference('fontSize', Math.max(14, fontSize - 2))}
                disabled={fontSize <= 14}
                className="flex-1 py-1.5 bg-stone-100 hover:bg-stone-200 disabled:opacity-40 rounded-xl text-xs font-extrabold transition-all cursor-pointer"
                aria-label="Decrease text size"
              >
                A−
              </button>
              <button
                type="button"
                onClick={() => updatePreference('fontSize', Math.min(32, fontSize + 2))}
                disabled={fontSize >= 32}
                className="flex-1 py-1.5 bg-[#1A6B6B] hover:bg-[#145555] disabled:opacity-40 text-white rounded-xl text-xs font-extrabold transition-all cursor-pointer"
                aria-label="Increase text size"
              >
                A+
              </button>
            </div>
          </div>

          {/* Reading Ruler Toggle */}
          <div className="flex items-center justify-between pt-1">
            <div>
              <p className="text-xs font-bold text-stone-800">
                {t('accessibility.readingRuler', 'Reading Ruler')}
              </p>
              <p className="text-[11px] text-stone-500">
                {t('accessibility.rulerHelp', 'Follows your lines to stay focused')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => updatePreference('readingRuler', !readingRuler)}
              className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
                readingRuler ? 'bg-amber-500' : 'bg-stone-200'
              }`}
              role="switch"
              aria-checked={readingRuler}
              aria-label={t('accessibility.readingRuler', 'Reading Ruler')}
            >
              <div
                className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${
                  readingRuler ? 'left-7' : 'left-1'
                }`}
              />
            </button>
          </div>

          {/* High Contrast Toggle */}
          <div className="flex items-center justify-between pt-1">
            <div>
              <p className="text-xs font-bold text-stone-800">
                {t('accessibility.highContrast', 'High Contrast')}
              </p>
              <p className="text-[11px] text-stone-500">
                {t('accessibility.contrastHelp', 'Sharp black text on white background')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => updatePreference('highContrast', !highContrast)}
              className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
                highContrast ? 'bg-teal-700' : 'bg-stone-200'
              }`}
              role="switch"
              aria-checked={highContrast}
              aria-label={t('accessibility.highContrast', 'High Contrast')}
            >
              <div
                className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${
                  highContrast ? 'left-7' : 'left-1'
                }`}
              />
            </button>
          </div>

          {/* Page Color Tint */}
          <div className="space-y-1.5 pt-1">
            <span className="text-xs font-bold text-stone-700 block">
              {t('accessibility.colorTint', 'Page Color Tint')}
            </span>
            <div className="flex items-center gap-1.5">
              {[
                { id: 'none', label: 'Off', color: '#FFFFFF', border: 'border-stone-300' },
                { id: 'peach', label: 'Peach', color: '#FFE5D9', border: 'border-orange-300' },
                { id: 'mint', label: 'Mint', color: '#E8F5E9', border: 'border-green-300' },
                { id: 'sky', label: 'Sky', color: '#E1F5FE', border: 'border-sky-300' },
                { id: 'butter', label: 'Butter', color: '#FFF9C4', border: 'border-yellow-300' },
              ].map((tint) => (
                <button
                  key={tint.id}
                  type="button"
                  onClick={() => updatePreference('tintOverlay', tint.id)}
                  className={`flex-1 py-1 text-[11px] font-bold rounded-xl border transition-all cursor-pointer ${
                    tintOverlay === tint.id
                      ? 'ring-2 ring-teal-600 scale-105 font-extrabold shadow-2xs'
                      : 'hover:opacity-80'
                  } ${tint.border}`}
                  style={{ backgroundColor: tint.color }}
                  aria-pressed={tintOverlay === tint.id}
                  title={tint.label}
                >
                  {tint.label}
                </button>
              ))}
            </div>
          </div>

          {/* Bottom Actions */}
          <div className="pt-2 border-t border-stone-100 flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={resetDefaults}
              className="text-stone-500 hover:text-stone-800 underline font-medium"
            >
              {t('accessibility.resetDefaults', 'Reset Defaults')}
            </button>
            <Link
              to="/student/accessibility"
              onClick={() => setIsOpen(false)}
              className="text-teal-700 hover:text-teal-900 font-bold flex items-center gap-1"
            >
              <span>{t('accessibility.allSettings', 'All Settings')}</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
