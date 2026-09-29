/**
 * frontend/src/features/learner/StrengthsCard.jsx
 * Displays student's primary strengths using data-driven, encouraging cards.
 */
import React from 'react'

export default function StrengthsCard({ strengths = [] }) {
  if (!strengths || strengths.length === 0) {
    return (
      <div className="bg-white rounded-3xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2 dyslexia-text">
          <span>⭐</span> YOUR STRENGTHS
        </h3>
        <p className="text-sm text-gray-500 italic">
          Complete your learning check to discover your top superpowers!
        </p>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-emerald-50/80 to-teal-50/50 rounded-3xl border border-emerald-200 p-6 sm:p-7 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-2xl bg-emerald-500 text-white flex items-center justify-center text-lg shadow-sm">
            ⭐
          </div>
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-emerald-950 dyslexia-text">
              YOUR STRENGTHS
            </h3>
            <p className="text-xs text-emerald-700 font-medium">
              Skills you excel in and can rely on while reading
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300/60">
          {strengths.length} Superpowers Found
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strengths.map((item, idx) => {
          const score = Math.round(item.score || 0)
          return (
            <div
              key={item.domain || idx}
              className="bg-white rounded-2xl p-5 border border-emerald-100 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    {item.label || 'Strength'}
                  </span>
                  <span className="text-xs font-extrabold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-200">
                    {score}%
                  </span>
                </div>

                <h4 className="font-bold text-gray-900 text-base dyslexia-text pt-1">
                  {item.friendly_name || item.domain}
                </h4>

                <p className="text-xs sm:text-sm text-gray-600 leading-relaxed dyslexia-text">
                  {item.description}
                </p>
              </div>

              {item.technical_name && (
                <div className="pt-3 mt-3 border-t border-gray-100 text-[11px] text-gray-400">
                  Domain: {item.technical_name}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
