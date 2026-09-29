/**
 * frontend/src/features/learner/LearnerDisclaimer.jsx
 * Prominent, friendly educational disclaimer.
 */
import React from 'react'

export default function LearnerDisclaimer({ compact = false }) {
  if (compact) {
    return (
      <div
        role="note"
        aria-label="Educational Disclaimer"
        className="p-3 bg-amber-50/90 border border-amber-200/80 rounded-xl text-xs text-amber-900 leading-relaxed flex items-start gap-2.5 shadow-sm"
      >
        <span className="text-base select-none" aria-hidden="true">💡</span>
        <div>
          <strong className="font-semibold text-amber-950">Educational Indicator:</strong>{' '}
          This profile reflects educational observations and learning preferences to customize reading accommodations. It does not constitute a clinical or medical diagnosis.
        </div>
      </div>
    )
  }

  return (
    <div
      role="note"
      aria-label="Educational Disclaimer"
      className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl text-xs text-amber-900 leading-relaxed shadow-sm flex items-start gap-3"
    >
      <div className="w-8 h-8 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0 text-amber-700 text-base font-bold shadow-inner">
        💡
      </div>
      <div className="space-y-1">
        <p className="font-bold text-amber-950 text-sm">Educational Support Platform Notice</p>
        <p className="text-amber-800/90">
          This learning profile summarizes educational screening indicators, strengths, and reading preferences to tailor assistive learning tools. It does not provide or represent a medical or clinical diagnosis.
        </p>
      </div>
    </div>
  )
}
