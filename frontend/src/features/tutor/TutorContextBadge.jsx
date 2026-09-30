/**
 * frontend/src/features/tutor/TutorContextBadge.jsx
 *
 * Transparent context indicators showing the student what reading context
 * the Personal AI Tutor is currently aware of.
 */
import React from 'react'

export default function TutorContextBadge({
  context,
  activePassageTitle,
  activeWord,
  onClearPassage,
  onClearWord,
}) {
  const levelName = context?.learningLevelName || 'Developing'
  const level = context?.learningLevel || 2
  const storyTitle = activePassageTitle || context?.currentPassage?.title

  return (
    <div className="flex flex-wrap items-center gap-2 px-3 py-2 bg-stone-50 border border-stone-200 rounded-2xl text-xs text-stone-700 shadow-2xs">
      <div className="flex items-center gap-1.5 font-bold text-teal-800 bg-teal-50 px-2.5 py-1 rounded-xl border border-teal-200">
        <span>✨</span>
        <span>Level {level}: {levelName}</span>
      </div>

      {storyTitle && (
        <div className="flex items-center gap-1.5 bg-blue-50 text-blue-900 px-2.5 py-1 rounded-xl border border-blue-200 font-medium">
          <span>📖</span>
          <span className="truncate max-w-[140px] sm:max-w-[200px]" title={storyTitle}>
            {storyTitle}
          </span>
          {onClearPassage && (
            <button
              onClick={onClearPassage}
              className="hover:text-red-600 px-1 rounded cursor-pointer font-bold"
              title="Remove story context"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {activeWord && (
        <div className="flex items-center gap-1.5 bg-amber-50 text-amber-900 px-2.5 py-1 rounded-xl border border-amber-200 font-bold">
          <span>🔖</span>
          <span>Word: {activeWord}</span>
          {onClearWord && (
            <button
              onClick={onClearWord}
              className="hover:text-red-600 px-1 rounded cursor-pointer font-bold"
              title="Remove word context"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {context?.currentPassage?.difficulty && (
        <span className="text-[11px] text-stone-500 hidden md:inline ml-auto">
          Adaptive Tier {context.adaptiveTier || context.currentPassage.difficulty}
        </span>
      )}
    </div>
  )
}
