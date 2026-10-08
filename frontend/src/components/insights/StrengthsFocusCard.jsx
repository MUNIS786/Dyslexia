/**
 * frontend/src/components/insights/StrengthsFocusCard.jsx
 *
 * Highlights child strengths and actionable next practice priorities.
 * Uses real metrics and active vocabulary without clinical terminology.
 */
import React from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function StrengthsFocusCard({
  learningLevel = 1,
  learningLevelName = 'Foundation',
  adaptiveTier = 1,
  adaptiveTierName = 'Foundation',
  strengths = [],
  focusAreas = [],
  difficultWords = [],
}) {
  const { t } = useTranslation()

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {/* Strengths Card */}
      <div className="bg-white rounded-3xl p-6 border border-emerald-200/80 shadow-2xs space-y-4">
        <div className="flex items-center justify-between gap-2 border-b border-emerald-100 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden="true">✨</span>
            <h3 className="text-sm font-extrabold text-emerald-950 uppercase tracking-wider">
              {t('insights.strengthsTitle', 'Your Strengths & Superpowers')}
            </h3>
          </div>
          <span className="px-2.5 py-0.5 bg-emerald-50 text-emerald-800 text-xs font-bold rounded-full border border-emerald-200">
            {t('common.level', 'Level')} {learningLevel}: {learningLevelName}
          </span>
        </div>

        {strengths.length > 0 ? (
          <ul className="space-y-2.5">
            {strengths.map((str, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2.5 text-xs sm:text-sm text-stone-700 leading-relaxed"
              >
                <span className="text-emerald-600 font-bold shrink-0 mt-0.5">⭐</span>
                <span>{str}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-stone-500 italic">
            Complete reading sessions to discover your personal superpowers!
          </p>
        )}
      </div>

      {/* Focus Areas Card */}
      <div className="bg-white rounded-3xl p-6 border border-teal-200/80 shadow-2xs space-y-4">
        <div className="flex items-center justify-between gap-2 border-b border-teal-100 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden="true">🎯</span>
            <h3 className="text-sm font-extrabold text-teal-950 uppercase tracking-wider">
              {t('insights.focusAreasTitle', 'Recommended Next Steps')}
            </h3>
          </div>
          <span className="px-2.5 py-0.5 bg-teal-50 text-teal-800 text-xs font-bold rounded-full border border-teal-200">
            {t('common.tier', 'Tier')} {adaptiveTier}: {adaptiveTierName}
          </span>
        </div>

        {focusAreas.length > 0 ? (
          <ul className="space-y-2.5">
            {focusAreas.map((focus, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2.5 text-xs sm:text-sm text-stone-700 leading-relaxed"
              >
                <span className="text-teal-600 font-bold shrink-0 mt-0.5">🌱</span>
                <span>{focus}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-stone-500 italic">
            Keep practicing daily to unlock new story challenges!
          </p>
        )}

        {/* Tricky Words Chip List */}
        {difficultWords && difficultWords.length > 0 && (
          <div className="pt-3 border-t border-stone-100">
            <span className="text-xs font-bold text-stone-600 block mb-2">
              📝 Words to Review:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {difficultWords.map((word, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 bg-stone-100 text-stone-800 text-xs font-bold rounded-xl border border-stone-200"
                >
                  {word}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
