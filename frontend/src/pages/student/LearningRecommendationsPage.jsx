/**
 * frontend/src/pages/student/LearningRecommendationsPage.jsx
 *
 * Dedicated Phase 14 Student Learning Recommendations & Study Plan page.
 * Answers: "What should this learner practice next, and why?"
 * Integrates directly with real performance data across Phases 2-13.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { recommendationsV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'
import {
  RecommendationCard,
  StudyPlan,
  RecommendationEmptyState,
} from '../../components/recommendations'
import toast from 'react-hot-toast'

export default function LearningRecommendationsPage() {
  const { t } = useTranslation()
  const [horizon, setHorizon] = useState('today') // 'today' | '7d'
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const loadRecommendations = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)
    try {
      const res = isRefresh
        ? await recommendationsV2API.refreshStudentRecommendations(horizon)
        : await recommendationsV2API.getStudentRecommendations(horizon)
      setData(res)
      if (isRefresh) {
        toast.success('✨ Plan updated with your latest reading progress!')
      }
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err.message ||
        'Could not load personalized recommendations.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [horizon])

  useEffect(() => {
    loadRecommendations()
  }, [loadRecommendations])

  const recommendations = data?.recommendations || []
  const studyPlan = data?.studyPlan
  const dataSufficiency = data?.dataSufficiency || 'no_data'
  const isNoData = dataSufficiency === 'no_data'

  return (
    <div className="max-w-6xl mx-auto py-6 px-3 sm:px-6 space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200/90 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-3xl sm:text-4xl" aria-hidden="true">🧭</span>
            <h1 className="text-2xl sm:text-3xl font-black text-stone-900 tracking-tight">
              {t('recommendations.pageTitle', 'Your Next Steps & Study Plan')}
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-stone-600 max-w-2xl leading-relaxed">
            {t(
              'recommendations.pageSubtitle',
              'Personalized learning activities chosen for your reading goals, tricky words, and daily practice.'
            )}
          </p>

          {/* Level Badges */}
          {data && (
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-teal-50 text-teal-900 border border-teal-200">
                <span aria-hidden="true">🏆</span>
                <span>
                  {t('common.level', 'Level')} {data.currentLearningLevel}: {data.currentLearningLevelName}
                </span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-amber-50 text-amber-900 border border-amber-200">
                <span aria-hidden="true">🎯</span>
                <span>
                  {t('common.tier', 'Tier')} {data.currentAdaptiveTier}: {data.currentAdaptiveTierName}
                </span>
              </span>
            </div>
          )}
        </div>

        {/* Refresh Action */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => loadRecommendations(true)}
            disabled={loading || refreshing}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold bg-stone-100 text-stone-800 hover:bg-stone-200 transition-all border border-stone-200 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B]"
            title="Refresh recommendations based on recent activity"
          >
            <span aria-hidden="true" className={refreshing ? 'animate-spin' : ''}>
              🔄
            </span>
            <span>
              {refreshing
                ? t('recommendations.refreshing', 'Updating...')
                : t('recommendations.refreshBtn', 'Update Plan')}
            </span>
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && !loading && (
        <div
          role="alert"
          className="rounded-3xl p-6 bg-red-50 border border-red-200 text-red-900 flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl" aria-hidden="true">⚠️</span>
            <span className="text-sm font-semibold">{error}</span>
          </div>
          <button
            type="button"
            onClick={() => loadRecommendations(false)}
            className="px-4 py-2 bg-red-800 text-white text-xs font-bold rounded-xl hover:bg-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-6 animate-pulse">
          <div className="h-48 bg-stone-200/60 rounded-3xl" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-64 bg-stone-200/60 rounded-3xl" />
            <div className="h-64 bg-stone-200/60 rounded-3xl" />
          </div>
        </div>
      )}

      {/* Content View */}
      {!loading && !error && (
        <>
          {/* Empty / Getting to Know You State */}
          {isNoData ? (
            <RecommendationEmptyState
              message={data?.dataSufficiencyMessage}
              actionUrl="/student/reading-coach"
            />
          ) : (
            <div className="space-y-8">
              {/* 1. Daily Study Plan Section */}
              {studyPlan && (
                <StudyPlan
                  studyPlan={studyPlan}
                  horizon={horizon}
                  onSelectHorizon={(h) => setHorizon(h)}
                />
              )}

              {/* 2. Detailed Recommended Next Steps Cards */}
              <section aria-labelledby="next-steps-heading" className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl" aria-hidden="true">🚀</span>
                    <h2 id="next-steps-heading" className="text-lg font-black text-stone-900 tracking-tight">
                      {t('recommendations.nextStepsTitle', 'Your Next Steps')}
                    </h2>
                  </div>
                  <span className="text-xs font-semibold text-stone-500">
                    {recommendations.length} Recommended Activities
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {recommendations.map((rec) => (
                    <RecommendationCard
                      key={rec.id}
                      recommendation={rec}
                      onLaunch={() => {}}
                    />
                  ))}
                </div>
              </section>
            </div>
          )}
        </>
      )}

      {/* Educational Notice */}
      <footer
        role="contentinfo"
        className="rounded-2xl p-4 bg-stone-100/80 border border-stone-200/80 text-[11px] text-stone-500 leading-relaxed space-y-1"
      >
        <div className="flex items-center gap-1.5 font-bold text-stone-700">
          <span aria-hidden="true">ℹ️</span>
          <span>{t('recommendations.disclaimerTitle', 'Educational Support Notice')}</span>
        </div>
        <p>
          {data?.disclaimer ||
            t(
              'recommendations.disclaimerText',
              'These practice recommendations are personalized learning activities based on your reading progress. They do not constitute a medical or clinical diagnosis.'
            )}
        </p>
      </footer>
    </div>
  )
}
