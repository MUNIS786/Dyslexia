/**
 * frontend/src/components/insights/ParentProgressSection.jsx
 *
 * Dedicated Phase 13 learning progress card for Parent Portal.
 * Written in parent-friendly, encouraging language with practical home support tips.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { insightsV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'
import PeriodSelector from './PeriodSelector'

export default function ParentProgressSection({ studentId }) {
  const { t } = useTranslation()
  const [period, setPeriod] = useState('30d')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadParentInsights = useCallback(async () => {
    if (!studentId) return
    setLoading(true)
    setError(null)
    try {
      const res = await insightsV2API.getParentLearnerInsights(studentId, period)
      setData(res)
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to load child learning progress.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [studentId, period])

  useEffect(() => {
    loadParentInsights()
  }, [loadParentInsights])

  if (!studentId) return null

  return (
    <section
      aria-labelledby="parent-insights-heading"
      className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs space-y-5"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-stone-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">🌱</span>
            <h3 id="parent-insights-heading" className="text-lg font-black text-stone-900 tracking-tight">
              {t('insights.parentSectionTitle', 'Child Learning Progress')}
            </h3>
          </div>
          <p className="text-xs text-stone-500 mt-1 max-w-xl">
            {t(
              'insights.parentSectionSubtitle',
              'Simple, encouraging overview of reading growth and consistency at home.'
            )}
          </p>
        </div>

        <PeriodSelector selectedPeriod={period} onSelectPeriod={setPeriod} disabled={loading} />
      </div>

      {loading ? (
        <div className="space-y-3 animate-pulse">
          <div className="h-6 bg-stone-100 rounded w-1/3" />
          <div className="h-16 bg-stone-100 rounded-2xl" />
        </div>
      ) : error ? (
        <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 text-xs text-amber-800">
          ⚠️ {error}
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Consistency & Trend Overview Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-teal-50/70 border border-teal-200/80 space-y-1">
              <span className="text-xs font-bold text-teal-800 uppercase tracking-wider flex items-center gap-1.5">
                <span>🗓️</span> Practice Consistency
              </span>
              <p className="text-xs text-stone-700 leading-relaxed pt-1">
                {data.practiceConsistencyMessage}
              </p>
              <div className="pt-2 flex items-center gap-3 text-xs font-bold text-teal-900">
                <span>{data.activePracticeDays} active days</span>
                <span>•</span>
                <span>🔥 {data.currentStreak} day streak</span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200/80 space-y-1">
              <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                <span>📈</span> Reading Comprehension Trend
              </span>
              <p className="text-xs text-stone-700 leading-relaxed pt-1">
                {data.readingTrendMessage}
              </p>
              <div className="pt-2 text-xs font-bold text-emerald-900">
                Level: {data.learningLevelName} ({data.totalWordsRead} words read)
              </div>
            </div>
          </div>

          {/* At-Home Supportive Tips */}
          {data.homeSupportTips && data.homeSupportTips.length > 0 && (
            <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200/70 space-y-2">
              <h4 className="text-xs font-extrabold text-amber-950 uppercase tracking-wider flex items-center gap-1.5">
                <span>💡</span> {t('insights.parentHomeTipsTitle', 'Supportive Reading Tips for Home')}
              </h4>
              <ul className="space-y-1.5 text-xs text-amber-900/90 list-disc list-inside">
                {data.homeSupportTips.map((tip, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : null}
    </section>
  )
}
