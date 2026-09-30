/**
 * frontend/src/features/reading/ReadingRecommendation.jsx
 *
 * Child-friendly preview card showing the adaptive reading recommendation
 * with explainable pedagogical rationale and "Start Reading" action.
 */
import React from 'react'

const TIER_LABELS = {
  1: { name: 'Foundation', color: 'bg-emerald-100 text-emerald-800 border-emerald-300', icon: '🌱' },
  2: { name: 'Supported', color: 'bg-sky-100 text-sky-800 border-sky-300', icon: '🌊' },
  3: { name: 'Standard', color: 'bg-amber-100 text-amber-800 border-amber-300', icon: '⭐' },
  4: { name: 'Advanced', color: 'bg-purple-100 text-purple-800 border-purple-300', icon: '🚀' },
  5: { name: 'Mastery', color: 'bg-rose-100 text-rose-800 border-rose-300', icon: '👑' },
}

export default function ReadingRecommendation({
  recommendation,
  activePassage,
  allPassages = [],
  onSelectPassage,
  onStartReading,
  loading = false,
}) {
  const passage = activePassage || recommendation?.recommendedPassage
  if (!passage) return null

  const tier = passage.difficulty || 1
  const tierInfo = TIER_LABELS[tier] || TIER_LABELS[1]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Top Welcome Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-stone-200">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📖</span>
            <span className="text-xs font-bold uppercase tracking-wider text-teal-700">
              Recommended Reading
            </span>
          </div>

          <span
            className={`text-xs font-bold px-3 py-1.5 rounded-full border flex items-center gap-1.5 ${tierInfo.color}`}
          >
            <span>{tierInfo.icon}</span> Level {tier} • {tierInfo.name}
          </span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-stone-900 mb-3 leading-snug">
          {passage.title}
        </h1>

        {/* Passage Metadata Chips */}
        <div className="flex flex-wrap items-center gap-3 text-xs font-medium text-stone-600 mb-6">
          <span className="bg-stone-100 px-3 py-1.5 rounded-xl border border-stone-200 flex items-center gap-1">
            ⏱️ ~{passage.estimatedMinutes || 3} mins
          </span>
          <span className="bg-stone-100 px-3 py-1.5 rounded-xl border border-stone-200 flex items-center gap-1">
            📝 {passage.wordCount || 80} words
          </span>
          <span className="bg-stone-100 px-3 py-1.5 rounded-xl border border-stone-200 flex items-center gap-1">
            🎓 {passage.gradeBand || 'Elementary'}
          </span>
          {passage.topics?.map((topic) => (
            <span
              key={topic}
              className="bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-1 rounded-xl capitalize"
            >
              #{topic}
            </span>
          ))}
        </div>

        {/* Explainable Pedagogical Rationale */}
        {recommendation?.reason && (
          <div className="bg-[#FFF8F0] border-2 border-[#E8A020]/40 rounded-2xl p-4 sm:p-5 mb-8">
            <div className="flex items-start gap-3">
              <span className="text-2xl shrink-0">💡</span>
              <div>
                <p className="text-xs font-bold text-amber-900 uppercase tracking-wide mb-1">
                  Why this story is picked for you
                </p>
                <p className="text-sm sm:text-base text-stone-800 leading-relaxed font-medium">
                  {recommendation.reason}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Big Start Button */}
        <button
          onClick={() => onStartReading(passage)}
          disabled={loading}
          className="w-full sm:w-auto px-8 py-4 bg-[#1A6B6B] hover:bg-[#145555] active:scale-[0.98] text-white font-bold text-lg rounded-2xl shadow-md transition-all flex items-center justify-center gap-3 cursor-pointer"
        >
          <span>🚀</span>
          <span>Start Reading Now</span>
        </button>
      </div>

      {/* Alternative Stories at this Level */}
      {allPassages.length > 1 && (
        <div className="bg-stone-50 rounded-3xl p-6 border border-stone-200">
          <h3 className="text-sm font-bold text-stone-700 uppercase tracking-wide mb-3 flex items-center gap-2">
            <span>📚</span> Or choose another story from our library:
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {allPassages.map((p) => {
              const isSelected = p.passageId === passage.passageId
              return (
                <button
                  key={p.passageId}
                  onClick={() => onSelectPassage(p)}
                  className={`text-left p-3.5 rounded-2xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-teal-50 border-teal-500 shadow-sm'
                      : 'bg-white border-stone-200 hover:border-stone-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs text-stone-500 mb-1">
                    <span className="font-semibold text-teal-800">Level {p.difficulty}</span>
                    <span>~{p.estimatedMinutes}m</span>
                  </div>
                  <p className="font-bold text-stone-900 text-sm truncate">{p.title}</p>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
