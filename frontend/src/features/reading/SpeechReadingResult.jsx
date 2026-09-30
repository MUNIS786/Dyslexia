/**
 * frontend/src/features/reading/SpeechReadingResult.jsx
 *
 * Child-friendly speech reading analysis result card:
 * - Encouraging, non-stigmatizing feedback
 * - Visual stats: Words Read Clearly (%), Reading Pace (WPM), Practice Score
 * - Omissions and tricky words highlighted constructively
 * - Clear next-step options: proceed to questions, practice tricky words, or re-read
 */
import React from 'react'

export default function SpeechReadingResult({
  analysis,
  feedback,
  nextAction,
  onProceedToQuestions,
  onReRead,
  onReadSilently,
}) {
  if (!analysis) return null

  const {
    wordAccuracy = 80,
    coverageRate = 80,
    wordsPerMinute = 70,
    readingPracticeScore = 80,
    omissions = [],
    substitutions = [],
    matchedWordCount = 0,
    passageWordCount = 0,
  } = analysis

  // Positive feedback emoji & tone
  let praiseEmoji = '🌟'
  if (wordAccuracy >= 85) praiseEmoji = '🏆'
  else if (wordAccuracy >= 70) praiseEmoji = '✨'
  else praiseEmoji = '🌱'

  return (
    <div className="my-6 p-6 sm:p-7 rounded-3xl bg-white border-2 border-teal-200 shadow-md animate-fade-in space-y-5">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center text-3xl shadow-inner">
          {praiseEmoji}
        </div>
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-full inline-block mb-1">
            Speech Practice Summary
          </span>
          <h3 className="text-lg sm:text-xl font-extrabold text-stone-900">
            {feedback || 'Great Reading Practice!'}
          </h3>
          <p className="text-xs text-stone-600 font-medium">
            {nextAction || "You're doing wonderfully. Every practice makes your reading stronger."}
          </p>
        </div>
      </div>

      {/* Metric Stat Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-emerald-50 p-3.5 rounded-2xl border border-emerald-200 text-center">
          <span className="text-xl block mb-1">🎯</span>
          <span className="text-lg sm:text-xl font-extrabold text-emerald-900 block">
            {Math.round(wordAccuracy)}%
          </span>
          <span className="text-[11px] text-emerald-700 font-medium">Words Matched</span>
        </div>

        <div className="bg-sky-50 p-3.5 rounded-2xl border border-sky-200 text-center">
          <span className="text-xl block mb-1">⚡</span>
          <span className="text-lg sm:text-xl font-extrabold text-sky-900 block">
            {Math.round(wordsPerMinute)}
          </span>
          <span className="text-[11px] text-sky-700 font-medium">Words / Min</span>
        </div>

        <div className="bg-amber-50 p-3.5 rounded-2xl border border-amber-200 text-center">
          <span className="text-xl block mb-1">📖</span>
          <span className="text-lg sm:text-xl font-extrabold text-amber-900 block">
            {matchedWordCount} / {passageWordCount}
          </span>
          <span className="text-[11px] text-amber-700 font-medium">Words Read</span>
        </div>

        <div className="bg-teal-50 p-3.5 rounded-2xl border border-teal-200 text-center">
          <span className="text-xl block mb-1">🌟</span>
          <span className="text-lg sm:text-xl font-extrabold text-teal-900 block">
            {Math.round(readingPracticeScore)}
          </span>
          <span className="text-[11px] text-teal-700 font-medium">Practice Score</span>
        </div>
      </div>

      {/* Tricky Words Section (if any substitutions or omissions) */}
      {(substitutions.length > 0 || omissions.length > 0) && (
        <div className="bg-stone-50 p-4 rounded-2xl border border-stone-200 space-y-2">
          <h4 className="text-xs font-bold text-stone-700 flex items-center gap-1.5">
            <span>💡</span>
            <span>Words to Practice Next Time:</span>
          </h4>
          <div className="flex flex-wrap gap-2">
            {substitutions.slice(0, 4).map((sub, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-xl bg-white border border-stone-300 text-xs font-semibold text-stone-800"
              >
                {sub.expected}
              </span>
            ))}
            {omissions.slice(0, 4).map((om, idx) => (
              <span
                key={`om-${idx}`}
                className="px-2.5 py-1 rounded-xl bg-white border border-stone-300 text-xs font-semibold text-stone-800"
              >
                {om}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="pt-2 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {onReRead && (
            <button
              onClick={onReRead}
              className="px-4 py-2 rounded-xl bg-stone-100 text-stone-700 hover:bg-stone-200 text-xs font-bold transition-all cursor-pointer"
            >
              🎤 Read Again
            </button>
          )}
          {onReadSilently && (
            <button
              onClick={onReadSilently}
              className="px-4 py-2 rounded-xl bg-stone-100 text-stone-700 hover:bg-stone-200 text-xs font-bold transition-all cursor-pointer"
            >
              📖 Read Silently
            </button>
          )}
        </div>

        {onProceedToQuestions && (
          <button
            onClick={onProceedToQuestions}
            className="px-5 py-2.5 rounded-xl bg-[#1A6B6B] text-white hover:bg-[#155757] text-xs sm:text-sm font-extrabold shadow-sm transition-all flex items-center gap-2 cursor-pointer"
          >
            <span>Answer Questions</span>
            <span>➡️</span>
          </button>
        )}
      </div>
    </div>
  )
}
