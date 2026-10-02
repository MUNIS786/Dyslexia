/**
 * frontend/src/components/accessibility/ReadingRuler.jsx
 *
 * Interactive Reading Ruler & Focus Guide for DyslexAid V2.
 * Helps readers track lines of text without losing their place or skipping sentences.
 * Features:
 * - Follows mouse/pointer movement vertically across reading passages
 * - Keyboard controls: ArrowUp / ArrowDown to move ruler step-by-step
 * - Escape key to quickly dismiss
 * - Non-blocking: pointer-events-none on backdrop allows full word clicking and selection
 * - Accessible floating badge to adjust ruler height or close
 */
import React, { useState, useEffect, useCallback } from 'react'
import { useAccessibility } from '../../context/AccessibilityContext'
import { useTranslation } from '../../i18n/I18nContext'

export default function ReadingRuler() {
  const { preferences, updatePreference } = useAccessibility()
  const { t } = useTranslation()
  const { readingRuler, rulerSize = 60, rulerColor = 'amber' } = preferences

  const [mouseY, setMouseY] = useState(() => (typeof window !== 'undefined' ? window.innerHeight / 2 : 300))
  const [isKeyboardControlled, setIsKeyboardControlled] = useState(false)

  // Color styles
  const colorStyles = {
    amber: {
      border: 'border-amber-400',
      bg: 'bg-amber-400/15',
      badge: 'bg-amber-500 text-white',
    },
    cyan: {
      border: 'border-cyan-400',
      bg: 'bg-cyan-400/15',
      badge: 'bg-cyan-500 text-white',
    },
    yellow: {
      border: 'border-yellow-400',
      bg: 'bg-yellow-400/15',
      badge: 'bg-yellow-500 text-black',
    },
    gray: {
      border: 'border-stone-400',
      bg: 'bg-stone-400/15',
      badge: 'bg-stone-600 text-white',
    },
  }[rulerColor] || {
    border: 'border-amber-400',
    bg: 'bg-amber-400/15',
    badge: 'bg-amber-500 text-white',
  }

  // Pointer tracking
  useEffect(() => {
    if (!readingRuler) return

    const handleMouseMove = (e) => {
      if (!isKeyboardControlled) {
        setMouseY(e.clientY)
      }
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [readingRuler, isKeyboardControlled])

  // Keyboard navigation (Arrow keys & Escape)
  useEffect(() => {
    if (!readingRuler) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        updatePreference('readingRuler', false)
      } else if (e.key === 'ArrowUp' && (e.altKey || e.ctrlKey)) {
        e.preventDefault()
        setIsKeyboardControlled(true)
        setMouseY((prev) => Math.max(40, prev - 24))
      } else if (e.key === 'ArrowDown' && (e.altKey || e.ctrlKey)) {
        e.preventDefault()
        setIsKeyboardControlled(true)
        setMouseY((prev) => Math.min(window.innerHeight - 40, prev + 24))
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [readingRuler, updatePreference])

  if (!readingRuler) return null

  const topOffset = Math.max(0, mouseY - rulerSize / 2)

  return (
    <>
      {/* Dimmed top mask */}
      <div
        className="fixed inset-x-0 top-0 bg-stone-900/15 pointer-events-none z-40 transition-[height] duration-75"
        style={{ height: `${topOffset}px` }}
        aria-hidden="true"
      />

      {/* Clear Focus Window with tinted border */}
      <div
        className={`fixed inset-x-0 z-40 pointer-events-none border-y-2 ${colorStyles.border} ${colorStyles.bg} transition-[top,height] duration-75 shadow-xs`}
        style={{
          top: `${topOffset}px`,
          height: `${rulerSize}px`,
        }}
        aria-label="Reading Ruler Focus Window"
        role="region"
      />

      {/* Dimmed bottom mask */}
      <div
        className="fixed inset-x-0 bottom-0 bg-stone-900/15 pointer-events-none z-40 transition-[top] duration-75"
        style={{ top: `${topOffset + rulerSize}px` }}
        aria-hidden="true"
      />

      {/* Floating control widget (positioned in bottom-right corner) */}
      <aside
        className="fixed bottom-4 right-4 z-50 bg-white/95 backdrop-blur border border-stone-300 rounded-2xl shadow-lg p-2.5 flex items-center gap-2 text-xs font-bold text-stone-800"
        aria-label={t('accessibility.rulerControls', 'Reading Ruler Controls')}
      >
        <span className="flex items-center gap-1.5 pl-1">
          <span>📏</span>
          <span>{t('accessibility.readingRuler', 'Reading Ruler')}</span>
        </span>

        {/* Height adjuster */}
        <div className="flex items-center gap-1 bg-stone-100 rounded-xl px-2 py-1">
          <button
            onClick={() => updatePreference('rulerSize', Math.max(30, rulerSize - 10))}
            className="hover:text-teal-700 px-1 py-0.5"
            title="Make ruler thinner"
            aria-label="Make reading ruler thinner"
          >
            −
          </button>
          <span className="text-[11px] font-mono text-stone-600">{rulerSize}px</span>
          <button
            onClick={() => updatePreference('rulerSize', Math.min(140, rulerSize + 10))}
            className="hover:text-teal-700 px-1 py-0.5"
            title="Make ruler taller"
            aria-label="Make reading ruler taller"
          >
            +
          </button>
        </div>

        {/* Close ruler */}
        <button
          onClick={() => updatePreference('readingRuler', false)}
          className="px-2 py-1 bg-stone-200 hover:bg-stone-300 rounded-xl transition-all cursor-pointer text-stone-700"
          title="Turn off reading ruler (Esc)"
          aria-label={t('accessibility.closeRuler', 'Close Reading Ruler')}
        >
          ✕
        </button>
      </aside>
    </>
  )
}
