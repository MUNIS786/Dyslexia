/**
 * frontend/src/features/learner/LearnerProfileHeader.jsx
 * Friendly welcoming header for the student profile.
 */
import React from 'react'

export default function LearnerProfileHeader({
  name = 'Learner',
  preferredLanguage = 'English',
  onRefresh,
  refreshing = false,
}) {
  return (
    <div className="bg-gradient-to-br from-[#1A6B6B] to-[#258B8B] text-white rounded-3xl p-6 sm:p-8 shadow-md relative overflow-hidden">
      {/* Decorative background shapes */}
      <div
        className="absolute -right-12 -top-12 w-48 h-48 bg-white/10 rounded-full blur-2xl pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute right-20 -bottom-16 w-40 h-40 bg-[#E8A020]/20 rounded-full blur-xl pointer-events-none"
        aria-hidden="true"
      />

      <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-white/20 backdrop-blur-sm text-white border border-white/30">
              <span>🌟</span> My Learning Profile
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#E8A020]/90 text-white shadow-sm">
              <span>🗣️</span> {preferredLanguage.toUpperCase()}
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-400/25 text-emerald-100 border border-emerald-300/40">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse" />
              Active Intelligence
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white dyslexia-text">
            Hello, {name}! 👋
          </h1>
          <p className="text-white/85 text-sm sm:text-base max-w-xl leading-relaxed dyslexia-text font-normal">
            Here is your personalized learning map! See what you are super good at, the skills you are growing, and fun ways to practice reading.
          </p>
        </div>

        {onRefresh && (
          <div className="flex-shrink-0">
            <button
              onClick={onRefresh}
              disabled={refreshing}
              aria-label="Refresh learning profile"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-white/15 hover:bg-white/25 active:scale-95 text-white text-sm font-semibold border border-white/30 backdrop-blur-sm transition-all focus:outline-none focus:ring-2 focus:ring-white/80 disabled:opacity-50"
            >
              <span className={`text-base ${refreshing ? 'animate-spin' : ''}`}>🔄</span>
              <span>{refreshing ? 'Updating…' : 'Refresh Map'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
