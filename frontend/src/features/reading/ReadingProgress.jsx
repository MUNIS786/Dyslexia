/**
 * frontend/src/features/reading/ReadingProgress.jsx
 *
 * Child-friendly header progress bar displaying reading time,
 * active stage (Reading -> Questions -> Results), and words practiced.
 */
import React from 'react'

export default function ReadingProgress({
  step,
  durationSeconds,
  wordCount = 0,
  difficultWordsCount = 0,
  practicedWordsCount = 0,
}) {
  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60)
    const remaining = secs % 60
    return `${mins}:${remaining < 10 ? '0' : ''}${remaining}`
  }

  const steps = [
    { id: 'reading', label: '1. Read Passage', icon: '📖' },
    { id: 'comprehension', label: '2. Questions', icon: '❓' },
    { id: 'result', label: '3. Celebrate', icon: '🏆' },
  ]

  return (
    <div className="bg-white rounded-2xl border border-stone-200 px-4 py-3 shadow-2xs mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Step Indicator */}
        <div className="flex items-center gap-2">
          {steps.map((s, idx) => {
            const isActive = step === s.id
            const isPassed =
              (s.id === 'reading' && (step === 'comprehension' || step === 'result')) ||
              (s.id === 'comprehension' && step === 'result')
            return (
              <div key={s.id} className="flex items-center gap-2">
                <span
                  className={`text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1 transition-all ${
                    isActive
                      ? 'bg-[#1A6B6B] text-white shadow-2xs'
                      : isPassed
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-stone-100 text-stone-400'
                  }`}
                >
                  <span>{s.icon}</span>
                  <span className="hidden sm:inline">{s.label}</span>
                </span>
                {idx < steps.length - 1 && (
                  <span className="text-stone-300 text-xs">→</span>
                )}
              </div>
            )
          })}
        </div>

        {/* Telemetry Chips (Time, Words) */}
        <div className="flex items-center gap-3 text-xs font-bold text-stone-600">
          <div className="flex items-center gap-1 bg-amber-50 text-amber-900 border border-amber-200 px-2.5 py-1 rounded-xl">
            <span>⏱️</span>
            <span>{formatTime(durationSeconds)}</span>
          </div>

          {practicedWordsCount > 0 && (
            <div className="flex items-center gap-1 bg-teal-50 text-teal-800 border border-teal-200 px-2.5 py-1 rounded-xl">
              <span>🌟</span>
              <span>{practicedWordsCount} words practiced</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
