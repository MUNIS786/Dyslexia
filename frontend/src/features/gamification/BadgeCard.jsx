/**
 * frontend/src/features/gamification/BadgeCard.jsx
 *
 * Child-friendly, accessible achievement badge card.
 * High contrast, clear typography, aria progress indicators,
 * calm aesthetics suitable for learners with dyslexia.
 */
import React from 'react'

const CATEGORY_STYLES = {
  milestone: 'bg-amber-100 text-amber-800 border-amber-200',
  reading: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  practice: 'bg-teal-100 text-teal-800 border-teal-200',
  vocabulary: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  comprehension: 'bg-purple-100 text-purple-800 border-purple-200',
  streak: 'bg-rose-100 text-rose-800 border-rose-200',
  points: 'bg-blue-100 text-blue-800 border-blue-200',
}

export default function BadgeCard({ badge }) {
  const {
    badgeId,
    title,
    description,
    icon,
    category = 'practice',
    threshold,
    currentProgress = 0,
    progressPercent = 0,
    unlocked = false,
    unlockedAt,
  } = badge

  const formatDate = (epochSecs) => {
    if (!epochSecs) return ''
    const d = new Date(epochSecs * 1000)
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const categoryStyle = CATEGORY_STYLES[category] || 'bg-stone-100 text-stone-700 border-stone-200'

  return (
    <div
      id={`badge-card-${badgeId}`}
      tabIndex={0}
      className={`rounded-2xl p-5 border transition-all duration-200 flex flex-col justify-between focus:ring-2 focus:ring-teal-600 focus:outline-none ${
        unlocked
          ? 'bg-white border-stone-200 shadow-sm hover:shadow-md'
          : 'bg-stone-50/80 border-stone-200/70 opacity-90'
      }`}
      aria-label={`${title} achievement badge: ${unlocked ? 'Unlocked' : `In progress, ${currentProgress} of ${threshold}`}`}
    >
      <div>
        {/* Top: Icon & Category */}
        <div className="flex items-center justify-between gap-3 mb-3">
          <div
            className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shadow-sm ${
              unlocked
                ? 'bg-amber-100 border border-amber-200'
                : 'bg-stone-200/80 border border-stone-300 filter grayscale'
            }`}
            aria-hidden="true"
          >
            {icon}
          </div>
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${categoryStyle} capitalize`}
          >
            {category}
          </span>
        </div>

        {/* Title & Description */}
        <h3 className="text-base font-bold text-stone-900 mb-1 leading-snug">
          {title}
        </h3>
        <p className="text-xs sm:text-sm text-stone-600 mb-4 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Status / Progress Footer */}
      <div className="pt-3 border-t border-stone-100">
        {unlocked ? (
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
            <span className="flex items-center gap-1.5">
              <span aria-hidden="true">✓</span> Unlocked!
            </span>
            {unlockedAt && (
              <span className="text-emerald-700/80 font-normal">
                {formatDate(unlockedAt)}
              </span>
            )}
          </div>
        ) : (
          <div>
            <div className="flex justify-between items-center text-xs font-medium text-stone-600 mb-1.5">
              <span>Progress</span>
              <span className="font-bold text-stone-800">
                {currentProgress} / {threshold}
              </span>
            </div>
            <div
              className="w-full h-2.5 bg-stone-200 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={currentProgress}
              aria-valuemin={0}
              aria-valuemax={threshold}
              aria-label={`${title} progress`}
            >
              <div
                className="h-full bg-teal-600 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
