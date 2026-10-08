/**
 * frontend/src/components/recommendations/RecommendationReason.jsx
 *
 * Child-friendly, non-clinical explanation of why an activity was recommended.
 * Avoids clinical or statistical language; focuses on encouragement and purpose.
 */
import React from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function RecommendationReason({
  reason,
  detailedExplanation,
  evidenceSignals = [],
}) {
  const { t } = useTranslation()

  return (
    <div className="bg-stone-50/80 rounded-2xl p-3.5 border border-stone-200/80 space-y-2">
      <div className="flex items-start gap-2">
        <span className="text-base shrink-0 mt-0.5" aria-hidden="true">💡</span>
        <div className="space-y-1">
          <span className="text-[11px] font-extrabold uppercase tracking-wider text-stone-500 block">
            {t('recommendations.whyTitle', 'Why this activity?')}
          </span>
          <p className="text-xs text-stone-700 leading-relaxed font-medium">
            {reason}
          </p>
        </div>
      </div>

      {detailedExplanation && (
        <p className="text-[11px] text-stone-500 leading-relaxed pl-6 border-l-2 border-stone-200 ml-1">
          {detailedExplanation}
        </p>
      )}

      {evidenceSignals && evidenceSignals.length > 0 && (
        <div className="pt-1.5 flex flex-wrap gap-1.5 pl-6">
          {evidenceSignals.map((sig, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-stone-200/60 text-stone-600 text-[10px] font-semibold"
            >
              <span>📌</span>
              <span>{sig}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
