/**
 * frontend/src/features/teacher/analytics/TeacherInsightCards.jsx
 *
 * Renders descriptive, non-clinical educational insights and suggested teacher actions.
 */
import React from 'react'

export default function TeacherInsightCards({ insights = [] }) {
  if (!insights || insights.length === 0) {
    return (
      <div className="bg-white rounded-3xl p-5 border border-stone-200 shadow-2xs">
        <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1.5">
          <span>💡</span> Educational Observations
        </h3>
        <p className="text-xs text-stone-500 italic">
          Additional learning sessions will generate pedagogical observations.
        </p>
      </div>
    )
  }

  const getBadgeStyle = (type) => {
    switch (type) {
      case 'warning':
        return 'bg-amber-50/80 border-amber-200 text-amber-900'
      case 'success':
        return 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
      case 'info':
      default:
        return 'bg-teal-50/80 border-teal-200 text-teal-900'
    }
  }

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'reading':
        return '📖'
      case 'speech':
        return '🎙️'
      case 'adaptive':
        return '🎯'
      case 'engagement':
        return '🌟'
      default:
        return '💡'
    }
  }

  return (
    <div className="bg-white rounded-3xl p-5 border border-stone-200 shadow-2xs flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-extrabold text-stone-900 flex items-center gap-2">
            <span>💡</span> Educational Observations & Teaching Ideas
          </h3>
          <span className="text-[11px] font-semibold text-stone-500">
            Cohort pedagogical analysis
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {insights.map((ins, i) => {
            const title = ins.title || ins.message || 'Educational Insight'
            const description = ins.description || ins.message || ''
            const evidence = ins.evidence || ''
            const category = ins.category || 'general'
            const type = ins.type || 'info'

            return (
              <div
                key={ins.id || i}
                className={`p-3.5 rounded-2xl border transition-all ${getBadgeStyle(type)} flex flex-col justify-between`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-xs font-bold flex items-center gap-1.5">
                      <span>{getCategoryIcon(category)}</span>
                      <span>{title}</span>
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-white/70 border border-current/20">
                      {category}
                    </span>
                  </div>
                  <p className="text-xs font-normal leading-relaxed text-stone-700">
                    {description}
                  </p>
                  {evidence && (
                    <div className="text-[11px] text-stone-600 bg-white/70 rounded-lg p-2 font-mono border border-current/10 mt-2">
                      <span className="font-semibold text-stone-800">Evidence: </span>
                      {evidence}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-stone-100 text-[11px] text-stone-500 flex items-center gap-1">
        <span>🛡️</span>
        <span>Descriptive educational insights only. Zero medical or clinical diagnoses.</span>
      </div>
    </div>
  )
}
