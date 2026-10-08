/**
 * frontend/src/components/recommendations/TeacherRecommendedFocusCard.jsx
 *
 * Dedicated Phase 14 component for Teacher Analytics.
 * Renders the learner's recommended focus, pedagogical rationale, and supporting evidence.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { recommendationsV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'

export default function TeacherRecommendedFocusCard({ learnerId }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadRecommendations = useCallback(async () => {
    if (!learnerId) return
    setLoading(true)
    setError(null)
    try {
      const res = await recommendationsV2API.getTeacherLearnerRecommendations(learnerId, 'today')
      setData(res)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Could not load recommended focus.')
    } finally {
      setLoading(false)
    }
  }, [learnerId])

  useEffect(() => {
    loadRecommendations()
  }, [loadRecommendations])

  if (!learnerId) return null

  if (loading) {
    return (
      <div className="bg-white rounded-3xl p-6 border border-stone-200 animate-pulse space-y-3">
        <div className="h-4 bg-stone-200 rounded w-1/3" />
        <div className="h-6 bg-stone-200 rounded w-2/3" />
        <div className="h-4 bg-stone-100 rounded w-full" />
      </div>
    )
  }

  if (error || !data) return null

  return (
    <div className="bg-white rounded-3xl p-6 border border-teal-200/80 shadow-2xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-teal-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden="true">🎯</span>
          <h3 className="text-sm font-extrabold text-stone-900 uppercase tracking-wider">
            {t('recommendations.teacherFocusTitle', 'Recommended Focus for Learner')}
          </h3>
        </div>
        <span className="px-2.5 py-0.5 bg-teal-50 text-teal-800 text-xs font-bold rounded-full border border-teal-200">
          Level {data.currentLearningLevel} • Tier {data.currentAdaptiveTier}
        </span>
      </div>

      {/* Focus & Reason */}
      <div className="space-y-1.5">
        <h4 className="text-base font-black text-teal-950">
          {data.recommendedFocus}
        </h4>
        <p className="text-xs text-stone-600 leading-relaxed">
          {data.primaryReason}
        </p>
      </div>

      {/* Recent Evidence */}
      {data.recentEvidence && data.recentEvidence.length > 0 && (
        <div className="pt-2 border-t border-stone-100 space-y-1.5">
          <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider block">
            {t('recommendations.teacherEvidenceTitle', 'Recent Observations & Evidence')}
          </span>
          <ul className="space-y-1">
            {data.recentEvidence.map((ev, idx) => (
              <li key={idx} className="flex items-center gap-2 text-xs text-stone-700">
                <span className="text-teal-600 font-bold shrink-0">📌</span>
                <span>{ev}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
