/**
 * frontend/src/components/insights/ClassInsightsSection.jsx
 *
 * Dedicated Phase 13 classroom learning insights module for Teacher Analytics.
 * Renders cohort distribution, longitudinal averages, common focus areas,
 * and individual learner progress cards with zero N+1 database queries.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { insightsV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'
import PeriodSelector from './PeriodSelector'
import toast from 'react-hot-toast'

export default function ClassInsightsSection({ onSelectLearner }) {
  const { t } = useTranslation()
  const [period, setPeriod] = useState('30d')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await insightsV2API.getTeacherClassOverview(period)
      setData(res)
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to load classroom learning insights.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  return (
    <section
      aria-labelledby="class-insights-heading"
      className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs space-y-6"
    >
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">💡</span>
            <h2 id="class-insights-heading" className="text-lg font-black text-stone-900 tracking-tight">
              {t('insights.teacherClassTitle', 'Class Learning Trends & Insights')}
            </h2>
          </div>
          <p className="text-xs text-stone-500 mt-1 max-w-xl">
            {t(
              'insights.teacherClassSubtitle',
              'Classroom-wide longitudinal performance and active learner progress cards.'
            )}
          </p>
        </div>

        <PeriodSelector selectedPeriod={period} onSelectPeriod={setPeriod} disabled={loading} />
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-stone-100 rounded-2xl" />
          ))}
        </div>
      ) : error ? (
        <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 text-xs text-amber-800">
          ⚠️ {error}
        </div>
      ) : data ? (
        <>
          {/* Cohort KPI Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-emerald-50/80 border border-emerald-200">
              <span className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                <span>↑</span> {t('insights.studentsImproving', 'Improving')}
              </span>
              <p className="text-2xl font-black text-emerald-950 mt-1">{data.improvingCount}</p>
            </div>

            <div className="p-4 rounded-2xl bg-blue-50/80 border border-blue-200">
              <span className="text-xs font-bold text-blue-800 flex items-center gap-1.5">
                <span>→</span> {t('insights.studentsStable', 'Steady')}
              </span>
              <p className="text-2xl font-black text-blue-950 mt-1">{data.stableCount}</p>
            </div>

            <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200">
              <span className="text-xs font-bold text-amber-800 flex items-center gap-1.5">
                <span>⚠️</span> {t('insights.studentsNeedsAttention', 'Needs Attention')}
              </span>
              <p className="text-2xl font-black text-amber-950 mt-1">{data.needsAttentionCount}</p>
            </div>

            <div className="p-4 rounded-2xl bg-stone-100 border border-stone-200">
              <span className="text-xs font-bold text-stone-700 flex items-center gap-1.5">
                <span>ℹ️</span> {t('insights.studentsBuildingData', 'Building History')}
              </span>
              <p className="text-2xl font-black text-stone-900 mt-1">{data.insufficientDataCount}</p>
            </div>
          </div>

          {/* Classroom Averages */}
          <div className="flex flex-wrap gap-4 text-xs font-semibold text-stone-700 p-3 bg-stone-50 rounded-2xl border border-stone-200/60">
            <span>
              📖 {t('insights.classAvgAccuracy', 'Class Avg Accuracy')}:{' '}
              <strong className="text-stone-900">{data.averageAccuracy !== null ? `${data.averageAccuracy}%` : '—'}</strong>
            </span>
            <span>•</span>
            <span>
              ⚡ {t('insights.classAvgSpeed', 'Class Avg Speed')}:{' '}
              <strong className="text-stone-900">{data.averageSpeedWpm !== null ? `${data.averageSpeedWpm} WPM` : '—'}</strong>
            </span>
            <span>•</span>
            <span>
              🏫 Classroom: <strong className="font-mono text-teal-800">{data.classroomCode}</strong>
            </span>
          </div>

          {/* Student Progress Cards Grid */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-stone-500 uppercase tracking-wider">
              Learner Progress Overview ({data.students?.length || 0})
            </h3>

            {(!data.students || data.students.length === 0) ? (
              <p className="text-xs text-stone-500 italic p-4 text-center bg-stone-50 rounded-2xl">
                No students enrolled in this classroom roster yet.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.students.map((st) => (
                  <div
                    key={st.studentId}
                    className="p-4 rounded-2xl border border-stone-200 bg-white hover:border-teal-400 hover:shadow-xs transition-all space-y-3 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-extrabold text-stone-900 truncate">
                          {st.studentName}
                        </h4>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${
                            st.overallTrend === 'improving'
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                              : st.overallTrend === 'needs_attention'
                              ? 'bg-amber-50 text-amber-800 border-amber-300'
                              : st.overallTrend === 'stable'
                              ? 'bg-blue-50 text-blue-800 border-blue-300'
                              : 'bg-stone-50 text-stone-600 border-stone-200'
                          }`}
                        >
                          {st.overallTrend === 'improving' ? '↑ Improving' : st.overallTrend === 'needs_attention' ? '⚠️ Practice' : st.overallTrend === 'stable' ? '→ Steady' : 'ℹ️ New'}
                        </span>
                      </div>

                      <div className="mt-2 flex items-center gap-3 text-xs text-stone-600">
                        <span>
                          Level {st.level}
                        </span>
                        <span>•</span>
                        <span>
                          {st.readingAccuracy !== null ? `${st.readingAccuracy}% acc` : 'No acc'}
                        </span>
                        <span>•</span>
                        <span>
                          {st.readingSpeedWpm !== null ? `${st.readingSpeedWpm} WPM` : 'No spd'}
                        </span>
                      </div>

                      {st.topStrength && (
                        <p className="mt-2 text-[11px] text-emerald-800 bg-emerald-50/60 p-1.5 rounded-lg truncate">
                          ✨ {st.topStrength}
                        </p>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => onSelectLearner && onSelectLearner(st.studentId)}
                      className="w-full py-1.5 px-3 bg-stone-100 hover:bg-stone-200 text-stone-800 text-xs font-bold rounded-xl transition-all text-center focus:outline-none focus:ring-2 focus:ring-teal-600"
                    >
                      {t('insights.studentCardViewDrilldown', 'View Detailed Insights')} →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : null}
    </section>
  )
}
