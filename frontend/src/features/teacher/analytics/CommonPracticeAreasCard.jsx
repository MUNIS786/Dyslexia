/**
 * frontend/src/features/teacher/analytics/CommonPracticeAreasCard.jsx
 *
 * Displays cohort-wide practice focus areas to guide class-wide lesson planning.
 */
import React from 'react'

export default function CommonPracticeAreasCard({ areas = [] }) {
  if (!areas || areas.length === 0) {
    return (
      <div className="bg-white rounded-3xl p-5 border border-stone-200 shadow-2xs">
        <h3 className="text-sm font-bold uppercase tracking-wider text-stone-500 mb-2 flex items-center gap-1.5">
          <span>🎯</span> Common Practice Focus
        </h3>
        <p className="text-xs text-stone-500 italic">
          Complete learning checks to discover common growth areas.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-3xl p-5 border border-stone-200 shadow-2xs flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-extrabold text-stone-900 flex items-center gap-2">
            <span>🎯</span> Cohort Practice Priorities
          </h3>
          <span className="text-[11px] font-semibold text-stone-500">
            Across active learners
          </span>
        </div>

        <div className="space-y-3">
          {areas.map((a, i) => (
            <div key={i} className="space-y-1">
              <div className="flex items-center justify-between text-xs font-semibold text-stone-700">
                <span className="truncate pr-2">{a.area}</span>
                <span className="text-stone-500 shrink-0">
                  {a.learnerCount} learners ({a.percentage}%)
                </span>
              </div>
              <div className="w-full bg-stone-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-[#1A6B6B] h-2 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(8, a.percentage))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-stone-100 text-[11px] text-stone-500 flex items-center gap-1">
        <span>💡</span>
        <span>Target these skills in small-group reading or warm-up phonics exercises.</span>
      </div>
    </div>
  )
}
