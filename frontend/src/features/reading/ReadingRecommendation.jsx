/**
 * frontend/src/features/reading/ReadingRecommendation.jsx
 *
 * Child-friendly preview card showing the adaptive reading recommendation
 * with explainable pedagogical rationale and "Start Reading" action.
 */
import { useState } from 'react'
import { Card, Button, Badge } from '../../components/ui'

const TIER_LABELS = {
  1: { name: 'Foundation', color: 'green', icon: '🌱' },
  2: { name: 'Supported', color: 'teal', icon: '🌊' },
  3: { name: 'Standard', color: 'amber', icon: '⭐' },
  4: { name: 'Advanced', color: 'indigo', icon: '🚀' },
  5: { name: 'Mastery', color: 'purple', icon: '👑' },
}

export default function ReadingRecommendation({
  recommendation,
  activePassage,
  allPassages = [],
  onSelectPassage,
  onStartReading,
  loading = false,
}) {
  const [langFilter, setLangFilter] = useState('all')
  const passage = activePassage || recommendation?.recommendedPassage
  if (!passage) return null

  const tier = passage.difficulty || 1
  const tierInfo = TIER_LABELS[tier] || TIER_LABELS[1]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Top Welcome Card */}
      <Card className="p-6 sm:p-8 shadow-card border-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📖</span>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              Recommended Reading
            </span>
          </div>

          <Badge color={tierInfo.color} className="text-xs font-bold">
            <span>{tierInfo.icon}</span> Level {tier} • {tierInfo.name}
          </Badge>
        </div>

        <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold text-slate-900 mb-3 leading-snug">
          {passage.title}
        </h1>

        {/* Passage Metadata Chips */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs font-medium text-slate-600 mb-6 dyslexia-text">
          <span className="bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200 flex items-center gap-1 font-semibold">
            ⏱️ ~{passage.estimatedMinutes || 3} mins
          </span>
          <span className="bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200 flex items-center gap-1 font-semibold">
            📝 {passage.wordCount || 80} words
          </span>
          <span className="bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200 flex items-center gap-1 font-semibold">
            🎓 {passage.gradeBand || 'Elementary'}
          </span>
          <Badge color="indigo" className="font-semibold">
            🌐 {passage.language === 'mr' ? 'मराठी (Marathi)' : passage.language === 'hi' ? 'हिन्दी (Hindi)' : 'English'}
          </Badge>
          {passage.topics?.map((topic) => (
            <Badge key={topic} color="amber" className="capitalize">
              #{topic}
            </Badge>
          ))}
        </div>

        {/* Explainable Pedagogical Rationale */}
        {recommendation?.reason && (
          <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-4 sm:p-5 mb-6">
            <div className="flex items-start gap-3">
              <span className="text-2xl shrink-0">💡</span>
              <div>
                <p className="dyslexia-text text-xs font-bold text-amber-900 uppercase tracking-wide mb-1">
                  Why this story is picked for you
                </p>
                <p className="dyslexia-text text-sm sm:text-base text-slate-800 leading-relaxed font-medium">
                  {recommendation.reason}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Big Start Button */}
        <Button
          onClick={() => onStartReading(passage)}
          loading={loading}
          size="lg"
          className="w-full sm:w-auto shadow-md"
        >
          <span>🚀</span>
          <span>Start Reading Now →</span>
        </Button>
      </Card>

      {/* Alternative Stories at this Level */}
      {allPassages.length > 1 && (
        <Card className="p-6 border-slate-200 bg-slate-50/50 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="dyslexia-text text-sm font-bold text-slate-700 uppercase tracking-wide flex items-center gap-2">
              <span>📚</span> Library Stories at Level {tier}
            </h2>
            {/* Language filter pills */}
            <div className="flex items-center gap-1 text-xs bg-white p-1 rounded-xl border border-slate-200">
              <span className="text-slate-400 px-2 font-medium">Filter:</span>
              {[
                { code: 'all', label: 'All' },
                { code: 'en', label: 'English' },
                { code: 'mr', label: 'मराठी' },
                { code: 'hi', label: 'हिन्दी' },
              ].map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setLangFilter(lang.code)}
                  className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                    langFilter === lang.code
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {allPassages
              .filter((p) => langFilter === 'all' || (p.language || 'en') === langFilter)
              .map((p) => {
                const isSelected = p.passageId === passage.passageId
                const pLang = p.language === 'mr' ? 'मराठी' : p.language === 'hi' ? 'हिन्दी' : 'EN'
                return (
                  <button
                    key={p.passageId}
                    type="button"
                    onClick={() => onSelectPassage(p)}
                    className={`text-left p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-50/70 border-indigo-500 shadow-2xs'
                        : 'bg-white border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-indigo-700">Level {p.difficulty}</span>
                        <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px] font-bold">
                          {pLang}
                        </span>
                      </div>
                      <span className="font-medium">~{p.estimatedMinutes}m</span>
                    </div>
                    <p className="dyslexia-text font-bold text-slate-900 text-sm truncate">{p.title}</p>
                  </button>
                )
              })}
          </div>
        </Card>
      )}
    </div>
  )
}
