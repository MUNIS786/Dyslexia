/**
 * frontend/src/pages/teacher/TeacherAnalyticsPage.jsx
 *
 * DyslexAid V2 — Phase 7: Teacher Analytics Page
 * Provides cohort overview, common practice priorities, descriptive educational insights,
 * and individual learner longitudinal inspection.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { teacherV2API } from '../../api/v2/client'
import { useAuth } from '../../context/AuthContext'
import {
  ClassOverviewCards,
  CommonPracticeAreasCard,
  TeacherInsightCards,
  LearnerRosterTable,
  LearnerAnalyticsModal,
} from '../../features/teacher/analytics'
import { ClassInsightsSection } from '../../components/insights'
import toast from 'react-hot-toast'

export default function TeacherAnalyticsPage() {
  const { user } = useAuth()
  const [timeRange, setTimeRange] = useState('all') // '7d' | '30d' | '90d' | 'all'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [overviewData, setOverviewData] = useState(null)
  const [learnersData, setLearnersData] = useState([])
  const [selectedLearner, setSelectedLearner] = useState(null)

  const loadAnalytics = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [overviewRes, learnersRes] = await Promise.all([
        teacherV2API.getOverview(timeRange),
        teacherV2API.getLearners(timeRange),
      ])
      setOverviewData(overviewRes)
      setLearnersData(learnersRes || [])
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err.message ||
        'Failed to load classroom analytics.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [timeRange])

  useEffect(() => {
    loadAnalytics()
  }, [loadAnalytics])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">📈</span>
            <h1 className="text-xl sm:text-2xl font-black text-stone-900 tracking-tight">
              Classroom Analytics & Progress
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-stone-500 max-w-2xl">
            Longitudinal educational tracking, reading comprehension, read-aloud speech signals,
            and adaptive practice across your classroom cohort.
          </p>
          {overviewData?.classroomCode && (
            <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-teal-50 border border-teal-200 rounded-full text-xs font-semibold text-teal-800">
              <span>🏫 Classroom Code:</span>
              <span className="font-mono font-bold tracking-wider">
                {overviewData.classroomCode}
              </span>
            </div>
          )}
        </div>

        {/* Time Range Selector & Refresh */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="inline-flex p-1 bg-stone-100 rounded-full border border-stone-200 text-xs">
            {[
              { id: '7d', label: '7D' },
              { id: '30d', label: '30D' },
              { id: '90d', label: '90D' },
              { id: 'all', label: 'All Time' },
            ].map((r) => (
              <button
                key={r.id}
                onClick={() => setTimeRange(r.id)}
                className={`px-3 py-1 rounded-full font-bold transition-all ${
                  timeRange === r.id
                    ? 'bg-[#1A6B6B] text-white shadow-2xs'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          <button
            onClick={loadAnalytics}
            disabled={loading}
            className="p-2 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-700 transition-colors disabled:opacity-50"
            title="Refresh analytics data"
            aria-label="Refresh data"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-3xl p-16 border border-stone-200 shadow-2xs flex flex-col items-center justify-center space-y-3">
          <div className="w-12 h-12 border-3 border-teal-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-semibold text-stone-600">
            Synthesizing classroom learning analytics...
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-rose-50 border border-rose-200 rounded-3xl p-6 text-rose-900 flex items-center justify-between gap-4">
          <div>
            <div className="font-bold text-sm">Failed to load analytics</div>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
          <button
            onClick={loadAnalytics}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition-colors shrink-0"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Analytics Content */}
      {!loading && !error && overviewData && (
        <>
          {overviewData.totalLearners === 0 ? (
            <div className="bg-white rounded-3xl p-12 border border-stone-200 shadow-2xs text-center max-w-lg mx-auto space-y-3">
              <span className="text-4xl block">🏫</span>
              <h2 className="text-base font-extrabold text-stone-900">
                No Learners Enrolled Yet
              </h2>
              <p className="text-xs text-stone-500 leading-relaxed">
                Students who join using classroom code{' '}
                <span className="font-mono font-bold text-teal-800">
                  {overviewData.classroomCode}
                </span>{' '}
                will appear here along with their profile baselines, reading performance, and practice trends.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 1. Overview Metric Cards */}
              <ClassOverviewCards overview={overviewData} />

              {/* Phase 13: Learning Insights & Longitudinal Progress Reports */}
              <ClassInsightsSection
                onSelectLearner={(learnerId) => {
                  const found = learnersData.find((l) => (l.studentId || l.learnerId || l.id) === learnerId)
                  if (found) {
                    setSelectedLearner(found)
                  } else {
                    setSelectedLearner({ studentId: learnerId })
                  }
                }}
              />

              {/* 2. Common Priorities & Educational Insights Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <CommonPracticeAreasCard
                  areas={overviewData.commonPracticeAreas || []}
                />
                <TeacherInsightCards
                  insights={overviewData.pedagogicalObservations || []}
                />
              </div>

              {/* 3. Learner Roster Table */}
              <LearnerRosterTable
                learners={learnersData}
                selectedLearnerId={selectedLearner?.studentId}
                onSelectLearner={(learner) => setSelectedLearner(learner)}
              />
            </div>
          )}
        </>
      )}

      {/* 4. Detailed Individual Learner Modal */}
      {selectedLearner && (
        <LearnerAnalyticsModal
          studentId={selectedLearner.studentId}
          classroomCode={overviewData?.classroomCode}
          timeRange={timeRange}
          onClose={() => setSelectedLearner(null)}
        />
      )}
    </div>
  )
}
