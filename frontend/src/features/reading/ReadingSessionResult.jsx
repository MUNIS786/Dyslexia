/**
 * frontend/src/features/reading/ReadingSessionResult.jsx
 *
 * Child-friendly result celebration screen:
 * - What you did (passage, words, time, practiced words)
 * - How it went (encouraging feedback, celebration badges)
 * - What's next (explainable adaptive progression update)
 * - Action: Try Next Reading or Back to Home
 */
import React from 'react'

export default function ReadingSessionResult({
  result,
  activePassage,
  onTryNextReading,
  onGoHome,
}) {
  if (!result) return null

  const {
    correctCount = 0,
    totalQuestions = 0,
    wordsRead = 0,
    durationSeconds = 0,
    practicedWordsCount = 0,
    overallScore = 80,
    comprehensionScore = 80,
    adaptation = {},
    nextStepMessage,
    currentTier = 1,
  } = result

  const formatMinutes = (secs) => {
    const mins = Math.max(1, Math.round(secs / 60))
    return `${mins} min${mins > 1 ? 's' : ''}`
  }

  // Encouraging summary based on comprehension accuracy
  let performancePraise = 'Great reading! You understood the story really well.'
  let praiseEmoji = '🌟'
  if (comprehensionScore >= 90) {
    performancePraise = 'Outstanding reading superstar! You understood every detail.'
    praiseEmoji = '🏆'
  } else if (comprehensionScore < 60) {
    performancePraise = 'Good effort! Every story you read builds your reading brain.'
    praiseEmoji = '🌱'
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Celebration Header Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 text-center shadow-sm border border-stone-200">
        <div className="w-20 h-20 mx-auto mb-4 bg-amber-100 rounded-3xl flex items-center justify-center text-4xl shadow-inner animate-bounce">
          {praiseEmoji}
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-stone-900 mb-2">
          {comprehensionScore >= 75 ? 'Super Reading!' : 'Nice Job Finishing!'}
        </h1>
        <p className="text-base sm:text-lg text-stone-700 font-medium max-w-md mx-auto">
          {performancePraise}
        </p>

        {/* Level Up Banner if Tier Changed */}
        {adaptation?.tierChanged && adaptation.newTier > adaptation.previousTier && (
          <div className="mt-5 p-4 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-emerald-900 font-extrabold text-base flex items-center justify-center gap-2">
            <span>🎉</span>
            <span>LEVEL UP! You unlocked Reading Level {adaptation.newTier}!</span>
          </div>
        )}

        {/* Gamification Points & Badges Reward Callout */}
        {result?.gamification && result.gamification.pointsAwarded > 0 && (
          <div id="reading-gamification-reward" className="mt-4 p-3.5 bg-amber-50 rounded-2xl border border-amber-200 flex items-center justify-between text-xs font-bold text-amber-950">
            <div className="flex items-center gap-2">
              <span className="text-xl" aria-hidden="true">🏆</span>
              <span>{result.gamification.celebrationMessage || `+${result.gamification.pointsAwarded} Learning Points Earned!`}</span>
            </div>
            <span className="bg-amber-100 text-amber-900 px-2.5 py-1 rounded-full border border-amber-300">
              Total: {result.gamification.totalPoints} pts
            </span>
          </div>
        )}
      </div>

      {/* What You Did — Stat Cards */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 shadow-sm border border-stone-200">
        <h3 className="text-xs font-bold text-stone-500 uppercase tracking-wide mb-4">
          What You Accomplished
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-[#FFF8F0] p-4 rounded-2xl border border-amber-200 text-center">
            <span className="text-xl block mb-1">📖</span>
            <span className="text-lg sm:text-xl font-extrabold text-stone-900 block">
              {wordsRead}
            </span>
            <span className="text-xs text-stone-600 font-medium">Words Read</span>
          </div>

          <div className="bg-sky-50 p-4 rounded-2xl border border-sky-200 text-center">
            <span className="text-xl block mb-1">⏱️</span>
            <span className="text-lg sm:text-xl font-extrabold text-stone-900 block">
              {formatMinutes(durationSeconds)}
            </span>
            <span className="text-xs text-stone-600 font-medium">Reading Time</span>
          </div>

          <div className="bg-teal-50 p-4 rounded-2xl border border-teal-200 text-center">
            <span className="text-xl block mb-1">❓</span>
            <span className="text-lg sm:text-xl font-extrabold text-stone-900 block">
              {correctCount}/{totalQuestions}
            </span>
            <span className="text-xs text-stone-600 font-medium">Questions</span>
          </div>

          <div className="bg-purple-50 p-4 rounded-2xl border border-purple-200 text-center">
            <span className="text-xl block mb-1">💡</span>
            <span className="text-lg sm:text-xl font-extrabold text-stone-900 block">
              {practicedWordsCount}
            </span>
            <span className="text-xs text-stone-600 font-medium">New Words</span>
          </div>
        </div>
      </div>

      {/* Voice Reading Practice Badge if Speech Mode was used */}
      {result.speechWordAccuracy !== undefined && (
        <div className="bg-gradient-to-r from-teal-50 to-emerald-50 rounded-3xl p-5 border border-teal-200 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🎙️</span>
            <div>
              <h4 className="text-sm font-extrabold text-stone-900">
                Voice Reading Practice
              </h4>
              <p className="text-xs text-stone-600">
                {Math.round(result.speechWordAccuracy)}% words read clearly • {Math.round(result.speechWordsPerMinute || 0)} WPM pace
              </p>
            </div>
          </div>
          <span className="px-3 py-1 bg-white rounded-xl text-teal-800 font-extrabold text-xs border border-teal-200">
            Score: {Math.round(result.speechPracticeScore || result.speechWordAccuracy)}/100
          </span>
        </div>
      )}

      {/* What's Next Adaptive Decision */}
      <div className="bg-[#FFF8F0] rounded-3xl p-6 sm:p-7 border-2 border-[#E8A020]/40">
        <div className="flex items-start gap-3">
          <span className="text-2xl shrink-0">🧭</span>
          <div>
            <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide mb-1">
              What We'll Do Next
            </h4>
            <p className="text-stone-800 text-sm sm:text-base font-medium leading-relaxed">
              {nextStepMessage || "You're doing great! Let's explore your next reading recommendation."}
            </p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <button
          onClick={onTryNextReading}
          className="w-full sm:flex-1 py-4 bg-[#1A6B6B] hover:bg-[#145555] active:scale-[0.98] text-white font-bold text-base rounded-2xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>Try Next Reading</span>
          <span>🚀</span>
        </button>

        <button
          onClick={onGoHome}
          className="w-full sm:w-auto px-6 py-4 bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold text-base rounded-2xl transition-all cursor-pointer"
        >
          Back to Home
        </button>
      </div>
    </div>
  )
}
