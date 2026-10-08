/**
 * frontend/src/pages/student/LearningInsightsPage.jsx
 *
 * Dedicated Phase 13 Student Learning Insights & Progress Reports page.
 * Provides child-friendly, non-clinical visibility into reading accuracy,
 * comfortable reading speed, practice consistency, strengths, and recommended focus.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { insightsV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'
import {
  PeriodSelector,
  TrendCard,
  ProgressChart,
  DataSufficiencyBanner,
  StrengthsFocusCard,
} from '../../components/insights'
import toast from 'react-hot-toast'

export default function LearningInsightsPage() {
  const { t } = useTranslation()
  const [period, setPeriod] = useState('30d')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview') // 'overview' | 'trends' | 'strengths' | 'timeline'

  const loadInsights = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await insightsV2API.getStudentInsights(period)
      setData(res)
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err.message ||
        'Could not load learning insights.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    loadInsights()
  }, [loadInsights])

  const summary = data?.summary
  const trends = data?.trends
  const timeline = data?.timeline || []
  const dataSufficiency = summary?.dataSufficiency || 'no_data'

  return (
    <div className="max-w-6xl mx-auto py-6 px-3 sm:px-6 space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200/90 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-3xl sm:text-4xl" aria-hidden="true">📈</span>
            <h1 className="text-2xl sm:text-3xl font-black text-stone-900 tracking-tight">
              {t('insights.pageTitle', 'Learning Insights & Progress')}
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-stone-600 max-w-2xl leading-relaxed">
            {t(
              'insights.pageSubtitle',
              'See your reading journey, skill trends, and personal strengths grow over time.'
            )}
          </p>

          {/* Level & Tier Badges */}
          {summary && (
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-teal-50 text-teal-900 border border-teal-200">
                <span aria-hidden="true">🏆</span>
                <span>
                  {t('insights.currentLevelTitle', 'Level')}{' '}
                  {summary.currentLearningLevel}: {summary.currentLearningLevelName}
                </span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-amber-50 text-amber-900 border border-amber-200">
                <span aria-hidden="true">🎯</span>
                <span>
                  {t('insights.adaptiveTierTitle', 'Tier')}{' '}
                  {summary.currentAdaptiveTier}: {summary.currentAdaptiveTierName}
                </span>
              </span>
              {summary.currentStreak > 0 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-orange-50 text-orange-900 border border-orange-200">
                  <span aria-hidden="true">🔥</span>
                  <span>{summary.currentStreak} {t('insights.streakDays', 'Day Streak')}</span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Period Selector */}
        <div className="flex flex-col sm:items-end gap-2">
          <span className="text-xs font-bold text-stone-500 uppercase tracking-wider">
            {t('insights.selectPeriod', 'Reporting Period')}
          </span>
          <PeriodSelector
            selectedPeriod={period}
            onSelectPeriod={(p) => setPeriod(p)}
            disabled={loading}
          />
        </div>
      </div>

      {/* Error state */}
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
            onClick={loadInsights}
            className="px-4 py-2 bg-red-800 text-white text-xs font-bold rounded-xl hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {/* Data Sufficiency Banner */}
      {!loading && (
        <DataSufficiencyBanner
          dataSufficiency={dataSufficiency}
          message={summary?.dataSufficiencyMessage}
          actionUrl="/student/reading-coach"
        />
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-stone-200">
        <nav
          className="flex space-x-2 sm:space-x-6 overflow-x-auto"
          aria-label="Insights Sections"
        >
          {[
            { id: 'overview', label: t('insights.overviewTab', 'Overview'), icon: '📊' },
            { id: 'trends', label: t('insights.trendsTab', 'Skill Trends'), icon: '📈' },
            { id: 'strengths', label: t('insights.strengthsTab', 'Strengths & Focus'), icon: '✨' },
            { id: 'timeline', label: t('insights.timelineTab', 'Daily Timeline'), icon: '📅' },
          ].map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-3 sm:px-4 text-xs sm:text-sm font-bold border-b-2 flex items-center gap-2 transition-all whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] ${
                  isActive
                    ? 'border-[#1A6B6B] text-[#1A6B6B]'
                    : 'border-transparent text-stone-500 hover:text-stone-800 hover:border-stone-300'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <span aria-hidden="true">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metric Trend Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <TrendCard
              title={t('insights.readingAccuracyTitle', 'Reading Accuracy')}
              subtitle={t('insights.readingAccuracyDesc', 'Comprehension & story understanding')}
              icon="📖"
              trend={trends?.readingAccuracy}
              currentValue={summary?.readingAccuracy}
              unit="%"
              loading={loading}
            />
            <TrendCard
              title={t('insights.readingSpeedTitle', 'Reading Speed')}
              subtitle={t('insights.readingSpeedDesc', 'Comfortable words per minute')}
              icon="⚡"
              trend={trends?.readingSpeedWpm}
              currentValue={summary?.readingSpeedWpm}
              unit=" WPM"
              loading={loading}
            />
            <TrendCard
              title={t('insights.practiceConsistencyTitle', 'Practice Consistency')}
              subtitle={t('insights.practiceConsistencyDesc', 'Active reading days logged')}
              icon="🔥"
              trend={trends?.practiceConsistency}
              currentValue={summary?.activeDaysCount}
              unit=" days"
              loading={loading}
            />
            <TrendCard
              title={t('insights.speechAccuracyTitle', 'Read Aloud Accuracy')}
              subtitle={t('insights.speechAccuracyDesc', 'Pronunciation & phoneme clarity')}
              icon="🎤"
              trend={trends?.speechAccuracy}
              currentValue={summary?.speechAccuracy}
              unit="%"
              loading={loading}
            />
          </div>

          {/* Quick Snapshot Progress Chart */}
          <ProgressChart
            timeline={timeline}
            reportingPeriod={period}
            loading={loading}
          />

          {/* Strengths and Focus summary */}
          <StrengthsFocusCard
            learningLevel={summary?.currentLearningLevel || 1}
            learningLevelName={summary?.currentLearningLevelName || 'Foundation'}
            adaptiveTier={summary?.currentAdaptiveTier || 1}
            adaptiveTierName={summary?.currentAdaptiveTierName || 'Foundation'}
            strengths={summary?.strengths || []}
            focusAreas={summary?.improvementAreas || []}
            difficultWords={summary?.difficultWords || []}
          />
        </div>
      )}

      {/* Tab Content: Skill Trends */}
      {activeTab === 'trends' && (
        <div className="space-y-6">
          <ProgressChart
            timeline={timeline}
            reportingPeriod={period}
            loading={loading}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TrendCard
              title={t('insights.readingAccuracyTitle', 'Reading Accuracy')}
              subtitle={t('insights.readingAccuracyDesc', 'Comprehension & story understanding')}
              icon="📖"
              trend={trends?.readingAccuracy}
              currentValue={summary?.readingAccuracy}
              unit="%"
              loading={loading}
            />
            <TrendCard
              title={t('insights.readingSpeedTitle', 'Reading Speed')}
              subtitle={t('insights.readingSpeedDesc', 'Comfortable words per minute')}
              icon="⚡"
              trend={trends?.readingSpeedWpm}
              currentValue={summary?.readingSpeedWpm}
              unit=" WPM"
              loading={loading}
            />
          </div>
        </div>
      )}

      {/* Tab Content: Strengths & Focus */}
      {activeTab === 'strengths' && (
        <div className="space-y-6">
          <StrengthsFocusCard
            learningLevel={summary?.currentLearningLevel || 1}
            learningLevelName={summary?.currentLearningLevelName || 'Foundation'}
            adaptiveTier={summary?.currentAdaptiveTier || 1}
            adaptiveTierName={summary?.currentAdaptiveTierName || 'Foundation'}
            strengths={summary?.strengths || []}
            focusAreas={summary?.improvementAreas || []}
            difficultWords={summary?.difficultWords || []}
          />

          {/* Practice Action Banner */}
          <div className="bg-stone-50 rounded-3xl p-6 border border-stone-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-extrabold text-stone-900">
                Ready to level up your reading?
              </h4>
              <p className="text-xs text-stone-600 mt-1">
                Personalized reading coach sessions adapt in real-time to your pace.
              </p>
            </div>
            <Link
              to="/student/reading-coach"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#1A6B6B] text-white text-xs font-bold rounded-2xl hover:bg-[#155555] transition-all shadow-xs"
            >
              <span>📖</span>
              <span>Open Reading Coach</span>
            </Link>
          </div>
        </div>
      )}

      {/* Tab Content: Daily Timeline */}
      {activeTab === 'timeline' && (
        <div className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between gap-2 border-b border-stone-100 pb-3">
            <h3 className="text-sm font-black text-stone-900 uppercase tracking-wider">
              {t('insights.timelineTab', 'Daily Timeline')} ({timeline.length} Days in Period)
            </h3>
            <span className="text-xs text-stone-500">
              {summary?.readingSessionsCount || 0} Total Sessions Logged
            </span>
          </div>

          {timeline.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-stone-700">
                <thead className="bg-stone-50 text-stone-600 font-extrabold uppercase text-[10px] tracking-wider border-b border-stone-200">
                  <tr>
                    <th scope="col" className="py-2.5 px-3">Date</th>
                    <th scope="col" className="py-2.5 px-3">Sessions</th>
                    <th scope="col" className="py-2.5 px-3">Words Read</th>
                    <th scope="col" className="py-2.5 px-3">Accuracy</th>
                    <th scope="col" className="py-2.5 px-3">Reading Speed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {timeline.slice().reverse().map((point, idx) => (
                    <tr key={idx} className="hover:bg-stone-50/70 transition-colors">
                      <td className="py-2 px-3 font-semibold text-stone-900">
                        {point.date}
                      </td>
                      <td className="py-2 px-3">
                        {point.sessionCount > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-teal-50 text-teal-800 font-bold text-[11px]">
                            {point.sessionCount}
                          </span>
                        ) : (
                          <span className="text-stone-400">0</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        {point.wordsRead > 0 ? point.wordsRead.toLocaleString() : '—'}
                      </td>
                      <td className="py-2 px-3">
                        {point.readingAccuracy !== null && point.readingAccuracy !== undefined ? (
                          <span className="font-bold text-emerald-800">
                            {point.readingAccuracy}%
                          </span>
                        ) : (
                          <span className="text-stone-400">—</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        {point.readingSpeedWpm !== null && point.readingSpeedWpm !== undefined ? (
                          <span className="font-bold text-stone-800">
                            {point.readingSpeedWpm} WPM
                          </span>
                        ) : (
                          <span className="text-stone-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-stone-500 py-6 text-center italic">
              No daily practice records found for this period.
            </p>
          )}
        </div>
      )}

      {/* Non-clinical Educational Disclaimer */}
      <footer
        role="contentinfo"
        className="rounded-2xl p-4 bg-stone-100/80 border border-stone-200/80 text-[11px] text-stone-500 leading-relaxed space-y-1"
      >
        <div className="flex items-center gap-1.5 font-bold text-stone-700">
          <span aria-hidden="true">ℹ️</span>
          <span>{t('insights.disclaimerTitle', 'Educational Progress Notice')}</span>
        </div>
        <p>
          {t(
            'insights.disclaimerText',
            'These insights measure reading practice consistency and skill growth. They do not constitute a medical, psychological, or clinical diagnosis.'
          )}
        </p>
      </footer>
    </div>
  )
}
