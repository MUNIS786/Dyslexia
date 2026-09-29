/**
 * frontend/src/features/learner/LearnerStates.jsx
 * Accessible loading skeleton, no-screening empty state, and friendly error state.
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'

export function LearnerEmptyState() {
  const navigate = useNavigate()

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <div className="max-w-lg w-full bg-white rounded-3xl border border-gray-200 p-8 sm:p-10 text-center shadow-md space-y-6">
        <div className="w-20 h-20 rounded-3xl bg-teal-50 text-[#1A6B6B] flex items-center justify-center text-4xl mx-auto shadow-inner border border-teal-100">
          🌱
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900 dyslexia-text">
            Your learning profile is getting ready.
          </h2>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed dyslexia-text">
            Complete your learning check to discover your strengths and areas to practice.
          </p>
        </div>

        <div className="p-4 bg-teal-50/70 border border-teal-200/80 rounded-2xl text-xs text-teal-900 text-left leading-relaxed">
          <strong className="block font-bold text-teal-950 mb-1">What to expect:</strong>
          A fun, untimed 10-minute check with friendly puzzles, sound games, and word questions to help us tailor the app just for you.
        </div>

        <button
          onClick={() => navigate('/student/screening')}
          className="w-full py-4 px-6 rounded-2xl bg-[#1A6B6B] hover:bg-[#145555] active:scale-98 text-white font-bold text-base shadow-lg transition-all focus:outline-none focus:ring-4 focus:ring-teal-200 dyslexia-text flex items-center justify-center gap-2"
        >
          <span>Complete Learning Check</span>
          <span>→</span>
        </button>
      </div>
    </div>
  )
}

export function LearnerProfileSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading your learning profile">
      {/* Header skeleton */}
      <div className="h-44 bg-gray-200 rounded-3xl w-full" />

      {/* Level card skeleton */}
      <div className="h-40 bg-gray-200 rounded-3xl w-full" />

      {/* Strengths & Practice grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="h-64 bg-gray-200 rounded-3xl w-full" />
        <div className="h-64 bg-gray-200 rounded-3xl w-full" />
      </div>

      {/* Learning Map skeleton */}
      <div className="h-80 bg-gray-200 rounded-3xl w-full" />
    </div>
  )
}

export function LearnerErrorState({ onRetry }) {
  return (
    <div className="min-h-[50vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-3xl border border-gray-200 p-8 text-center shadow-md space-y-5">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center text-3xl mx-auto border border-amber-200">
          ⚠️
        </div>

        <div className="space-y-1.5">
          <h2 className="text-xl font-bold text-gray-900 dyslexia-text">
            Your learning profile is temporarily unavailable.
          </h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            We could not reach the server right now. Don&apos;t worry, your progress is safe!
          </p>
        </div>

        {onRetry && (
          <button
            onClick={onRetry}
            className="w-full py-3 px-6 rounded-2xl bg-[#1A6B6B] hover:bg-[#145555] text-white font-bold text-sm shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}
