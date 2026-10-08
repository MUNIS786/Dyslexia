/**
 * frontend/src/components/recommendations/ParentSuggestedPracticeCard.jsx
 *
 * Dedicated Phase 14 component for Parent Portal.
 * Written in warm, non-clinical language with practical reading tips for home.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { recommendationsV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'

export default function ParentSuggestedPracticeCard({ studentId }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadParentRecommendations = useCallback(async () => {
    if (!studentId) return
    setLoading(true)
    setError(null)
    try {
      const res = await recommendationsV2API.getParentLearnerRecommendations(studentId, 'today')
      setData(res)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Could not load home practice suggestions.')
    } finally {
      setLoading(false)
    }
  }, [studentId])

  useEffect(() => {
    loadParentRecommendations()
  }, [loadParentRecommendations])

  if (!studentId) return null

  if (loading) {
    return (
      <div className="bg-white rounded-3xl p-6 border border-stone-200 animate-pulse space-y-3">
        <div className="h-4 bg-stone-200 rounded w-1/3" />
        <div className="h-6 bg-stone-200 rounded w-3/4" />
      </div>
    )
  }

  if (error || !data) return null

  return (
    <div className="bg-white rounded-3xl p-6 border border-amber-200/80 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-amber-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden="true">🏡</span>
          <h3 className="text-sm font-extrabold text-stone-900 uppercase tracking-wider">
            {t('recommendations.parentPracticeTitle', 'Suggested Practice at Home')}
          </h3>
        </div>
        <span className="px-2.5 py-0.5 bg-amber-50 text-amber-900 text-xs font-bold rounded-full border border-amber-200">
          ⏱️ ~{data.recommendedMinutes} Mins Daily
        </span>
      </div>

      {/* Suggested Practice Message */}
      <p className="text-xs sm:text-sm text-stone-700 leading-relaxed font-medium">
        {data.suggestedPracticeAtHome}
      </p>

      {/* Words in focus */}
      {data.focusWords && data.focusWords.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider block">
            {t('recommendations.targetWords', 'Words in Focus:')}
          </span>
          <div className="flex flex-wrap gap-1.5">
            {data.focusWords.map((word, idx) => (
              <span
                key={idx}
                className="px-2.5 py-0.5 rounded-xl bg-amber-50 text-amber-950 border border-amber-200 text-xs font-bold"
              >
                {word}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Parent Tips */}
      {data.parentTips && data.parentTips.length > 0 && (
        <div className="pt-3 border-t border-stone-100 space-y-2">
          <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider block">
            {t('recommendations.parentTipsTitle', 'At-Home Encouragement Tips')}
          </span>
          <ul className="space-y-1.5">
            {data.parentTips.map((tip, idx) => (
              <li key={idx} className="flex items-start gap-2 text-xs text-stone-600 leading-relaxed">
                <span className="text-amber-600 font-bold shrink-0 mt-0.5">🌱</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
