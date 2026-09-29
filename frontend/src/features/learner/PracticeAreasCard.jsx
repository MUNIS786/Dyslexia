/**
 * frontend/src/features/learner/PracticeAreasCard.jsx
 * Displays targeted practice areas framed positively as growth opportunities.
 */
import React from 'react'

const PRIORITY_BADGES = {
  high: {
    label: 'High Focus',
    badgeClass: 'bg-rose-100 text-rose-800 border-rose-200',
    indicator: '🎯 Recommended Next',
  },
  medium: {
    label: 'Helpful Practice',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-200',
    indicator: '🌱 Skill Builder',
  },
  low: {
    label: 'Gentle Reinforce',
    badgeClass: 'bg-blue-100 text-blue-800 border-blue-200',
    indicator: '✨ Light Practice',
  },
}

export default function PracticeAreasCard({ practiceAreas = [] }) {
  if (!practiceAreas || practiceAreas.length === 0) {
    return (
      <div className="bg-white rounded-3xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2 dyslexia-text">
          <span>🎯</span> AREAS TO PRACTICE
        </h3>
        <p className="text-sm text-gray-500 italic">
          Complete your learning check to see targeted practice recommendations!
        </p>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-blue-50/70 to-indigo-50/40 rounded-3xl border border-blue-200 p-6 sm:p-7 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-2xl bg-[#1A6B6B] text-white flex items-center justify-center text-lg shadow-sm">
            🎯
          </div>
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-gray-900 dyslexia-text">
              AREAS TO PRACTICE
            </h3>
            <p className="text-xs text-gray-600 font-medium">
              Targeted skills that will make reading smoother and more fun
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300/60">
          {practiceAreas.length} Growth Areas
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {practiceAreas.map((item, idx) => {
          const priorityInfo = PRIORITY_BADGES[item.priority] || PRIORITY_BADGES.medium
          const score = Math.round(item.score || 0)

          return (
            <div
              key={item.domain || idx}
              className="bg-white rounded-2xl p-5 border border-blue-100 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${priorityInfo.badgeClass}`}>
                    {priorityInfo.label}
                  </span>
                  <span className="text-xs font-semibold text-gray-500 bg-gray-50 px-2 py-0.5 rounded-md border border-gray-200">
                    Growth Score: {score}%
                  </span>
                </div>

                <h4 className="font-bold text-gray-900 text-base dyslexia-text pt-1">
                  {item.friendly_name || item.domain}
                </h4>

                <p className="text-xs sm:text-sm text-gray-600 leading-relaxed dyslexia-text">
                  {item.description}
                </p>
              </div>

              <div className="pt-3 mt-3 border-t border-gray-100 flex items-center justify-between gap-2 flex-wrap text-xs">
                {item.suggested_activity_type && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-teal-50 text-teal-800 border border-teal-200 font-medium">
                    <span>🎮</span> Suggested: {item.suggested_activity_type.replace(/_/g, ' ')}
                  </span>
                )}
                {item.technical_name && (
                  <span className="text-[11px] text-gray-400">
                    {item.technical_name}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
