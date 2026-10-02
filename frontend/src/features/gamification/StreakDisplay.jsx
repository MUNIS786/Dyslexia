/**
 * frontend/src/features/gamification/StreakDisplay.jsx
 *
 * Friendly, encouraging practice consistency indicator.
 * Strictly non-shaming: never displays loss warnings or failure messages.
 */
import React from 'react'

export default function StreakDisplay({
  currentStreak = 0,
  longestStreak = 0,
  streakMessage = 'Keep learning at your own pace!',
  lastActiveDate,
}) {
  return (
    <div
      id="streak-display-card"
      tabIndex={0}
      className="bg-white rounded-3xl p-6 sm:p-7 border border-stone-200 shadow-sm focus:ring-2 focus:ring-teal-600 focus:outline-none"
      aria-label={`Practice consistency: ${currentStreak} days active streak, best streak ${longestStreak} days.`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="flex items-start sm:items-center gap-4">
          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center text-3xl shadow-sm ${
              currentStreak > 0
                ? 'bg-amber-100 border border-amber-200 text-amber-800'
                : 'bg-stone-100 border border-stone-200 text-stone-500'
            }`}
            aria-hidden="true"
          >
            {currentStreak > 0 ? '✨' : '🌱'}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-bold text-stone-500">
                Practice Consistency
              </span>
              {currentStreak > 0 && (
                <span className="bg-amber-50 text-amber-800 text-xs px-2.5 py-0.5 rounded-full font-bold border border-amber-200">
                  Active
                </span>
              )}
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-stone-900 mt-0.5">
              {currentStreak === 1
                ? '1 Day Practiced'
                : `${currentStreak} Days Practiced`}
            </h2>
            <p className="text-sm text-stone-600 mt-1 font-medium max-w-lg">
              {streakMessage}
            </p>
          </div>
        </div>

        {/* Milestone Streak Stats */}
        <div className="flex items-center gap-6 sm:border-l sm:border-stone-200 sm:pl-8 pt-4 sm:pt-0 border-t sm:border-t-0 border-stone-100">
          <div>
            <span className="text-xs font-semibold text-stone-500 block">
              Best Streak
            </span>
            <span className="text-lg sm:text-xl font-bold text-teal-800">
              {longestStreak} {longestStreak === 1 ? 'day' : 'days'}
            </span>
          </div>

          {lastActiveDate && (
            <div>
              <span className="text-xs font-semibold text-stone-500 block">
                Last Practice
              </span>
              <span className="text-sm font-semibold text-stone-700">
                {lastActiveDate}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
