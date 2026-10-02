/**
 * frontend/src/features/teacher/analytics/LearnerAnalyticsModal.jsx
 *
 * Detailed pedagogical drilldown modal for an individual learner.
 * Displays domain performance, reading coach statistics, speech read-aloud signals,
 * adaptive practice state, and actionable teacher recommendations.
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { teacherV2API, gamificationV2API } from '../../../api/v2/client'

export default function LearnerAnalyticsModal({
  studentId,
  classroomCode,
  timeRange = 'all',
  onClose,
}) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [gamificationData, setGamificationData] = useState(null)
  const [activeTab, setActiveTab] = useState('overview') // 'overview' | 'domains' | 'reading_speech' | 'adaptive' | 'trends'

  useEffect(() => {
    let isMounted = true

    async function fetchDetail() {
      if (!studentId) return
      setLoading(true)
      setError(null)
      try {
        const [res, gamRes] = await Promise.all([
          teacherV2API.getLearnerDetail(studentId, timeRange),
          gamificationV2API.getTeacherLearnerSummary(studentId).catch(() => null),
        ])
        if (isMounted) {
          setData(res)
          setGamificationData(gamRes)
        }
      } catch (err) {
        if (isMounted) {
          setError(err?.response?.data?.detail || err.message || 'Failed to load learner analytics.')
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    fetchDetail()

    return () => {
      isMounted = false
    }
  }, [studentId, timeRange])

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const renderTrendBadge = (trend) => {
    switch (trend) {
      case 'improving':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            <span>↗</span> Improving
          </span>
        )
      case 'declining':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
            <span>↘</span> Declining
          </span>
        )
      case 'stable':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
            <span>→</span> Stable
          </span>
        )
      case 'insufficient_data':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-stone-500 bg-stone-100 px-2 py-0.5 rounded-full border border-stone-200">
            <span>—</span> Insufficient data
          </span>
        )
    }
  }

  const readingMetrics = data?.readingMetrics || {}
  const speechSignals = data?.speechSignals || {}
  const adaptiveState = data?.adaptiveState || {}
  const domainScores = data?.domainScores || []
  const trends = data?.trends || {}
  const insights = data?.insights || []
  const suggestedActions = data?.suggestedActions || []
  const recentSessions = data?.recentReadingSessions || []
  const recentAttempts = data?.recentActivityAttempts || []

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="learner-modal-title"
      className="fixed inset-0 z-50 bg-stone-900/50 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
    >
      <div className="bg-white rounded-3xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl border border-stone-200 overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-stone-100 flex items-center justify-between bg-stone-50/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-100 text-teal-800 flex items-center justify-center text-lg font-bold">
              {data?.name ? data.name.charAt(0).toUpperCase() : '👤'}
            </div>
            <div>
              <h2 id="learner-modal-title" className="text-base font-extrabold text-stone-900">
                {data?.name || 'Learner Analytics'}
              </h2>
              <p className="text-xs text-stone-500">
                {data?.email} {data?.classroomCode ? `• Classroom: ${data.classroomCode}` : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {data && (
              <div className="hidden sm:flex items-center gap-1.5 mr-2">
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-teal-50 border border-teal-200 text-teal-800">
                  Level {data.learningLevel} ({data.learningLevelName})
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-stone-100 border border-stone-200 text-stone-700">
                  Tier {data.adaptiveTier}
                </span>
              </div>
            )}
            <button
              onClick={() => {
                onClose()
                navigate('/teacher/interventions')
              }}
              className="px-3 py-1 bg-[#1A6B6B] hover:bg-[#155353] text-white text-xs font-bold rounded-full transition-all flex items-center gap-1 shadow-2xs"
            >
              <span>🎯</span> Support Activities
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 text-stone-600 flex items-center justify-center font-bold text-sm transition-colors"
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 px-5 py-2.5 bg-stone-50 border-b border-stone-100 overflow-x-auto shrink-0">
          {[
            { id: 'overview', label: 'Overview & Actions', icon: '💡' },
            { id: 'domains', label: 'Domain Strengths', icon: '📊' },
            { id: 'reading_speech', label: 'Reading & Speech', icon: '📖' },
            { id: 'adaptive', label: 'Adaptive Practice', icon: '🎯' },
            { id: 'trends', label: 'Longitudinal Trends', icon: '📈' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`text-xs font-bold px-3 py-1.5 rounded-full transition-all shrink-0 flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? 'bg-[#1A6B6B] text-white shadow-2xs'
                  : 'text-stone-600 hover:bg-stone-200/60'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6 overflow-y-auto flex-1 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-10 h-10 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-stone-500 font-semibold">
                Aggregating educational signals...
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              <span className="font-bold">Error loading analytics: </span>
              {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* TAB 1: OVERVIEW & TEACHER ACTIONS */}
              {activeTab === 'overview' && (
                <div className="space-y-5">
                  {/* Summary Metric Strip */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200">
                      <div className="text-[10px] uppercase font-bold text-stone-400">
                        Profile Baseline
                      </div>
                      <div className="text-sm font-extrabold text-stone-800 mt-1">
                        {data.screeningCompleted ? 'Completed' : 'Awaiting Screening'}
                      </div>
                      <div className="text-[11px] text-stone-500 mt-0.5">
                        Level {data.learningLevel} • {data.learningLevelName}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200">
                      <div className="text-[10px] uppercase font-bold text-stone-400">
                        Reading Comprehension
                      </div>
                      <div className="text-sm font-extrabold text-stone-800 mt-1">
                        {readingMetrics.avgComprehensionAccuracy > 0
                          ? `${readingMetrics.avgComprehensionAccuracy.toFixed(1)}%`
                          : '—'}
                      </div>
                      <div className="text-[11px] text-stone-500 mt-0.5">
                        {readingMetrics.totalWordsRead?.toLocaleString() || 0} words read
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200">
                      <div className="text-[10px] uppercase font-bold text-stone-400">
                        Oral Reading Accuracy
                      </div>
                      <div className="text-sm font-extrabold text-stone-800 mt-1">
                        {speechSignals.avgAccuracyRate != null
                          ? `${speechSignals.avgAccuracyRate.toFixed(1)}%`
                          : '—'}
                      </div>
                      <div className="text-[11px] text-stone-500 mt-0.5">
                        {speechSignals.sessionCount || 0} oral read sessions
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200">
                      <div className="text-[10px] uppercase font-bold text-stone-400">
                        Reading Trajectory
                      </div>
                      <div className="mt-1">
                        {renderTrendBadge(readingMetrics.trend || trends.readingTrend)}
                      </div>
                      <div className="text-[11px] text-stone-500 mt-0.5">
                        {readingMetrics.completedSessions || 0} completed readings
                      </div>
                    </div>
                  </div>

                  {/* Practice Engagement & Consistency */}
                  {gamificationData && (
                    <div id="teacher-learner-gamification-card" className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs uppercase font-extrabold text-amber-950 flex items-center gap-1.5">
                          <span>🏆</span> Practice Consistency & Achievements
                        </span>
                        <span className="text-xs font-bold text-amber-900 bg-amber-100 px-2.5 py-0.5 rounded-full border border-amber-200">
                          {gamificationData.totalPoints} Learning Points
                        </span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs mt-2">
                        <div>
                          <span className="text-stone-500 block">Active Consistency</span>
                          <span className="font-bold text-stone-800">
                            {gamificationData.currentStreak} {gamificationData.currentStreak === 1 ? 'day' : 'days'}
                          </span>
                        </div>
                        <div>
                          <span className="text-stone-500 block">Longest Streak</span>
                          <span className="font-bold text-stone-800">
                            {gamificationData.longestStreak} {gamificationData.longestStreak === 1 ? 'day' : 'days'}
                          </span>
                        </div>
                        <div>
                          <span className="text-stone-500 block">Badges Unlocked</span>
                          <span className="font-bold text-stone-800">
                            {gamificationData.earnedBadgesCount} achievements
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Suggested Teacher Actions */}
                  <div>
                    <h3 className="text-sm font-extrabold text-stone-900 mb-3 flex items-center gap-2">
                      <span>🎯</span> Recommended Instructional Next Steps
                    </h3>
                    {suggestedActions.length === 0 ? (
                      <p className="text-xs text-stone-500 italic bg-stone-50 p-4 rounded-2xl border border-stone-200">
                        Learner is progressing smoothly on track. Continue standard curriculum pacing.
                      </p>
                    ) : (
                      <div className="space-y-2.5">
                        {suggestedActions.map((action, i) => (
                          <div
                            key={action.id || i}
                            className="p-3.5 rounded-2xl border border-teal-200 bg-teal-50/50 flex items-start justify-between gap-3"
                          >
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-teal-950">
                                  {action.label}
                                </span>
                                <span className="text-[9px] uppercase font-extrabold px-1.5 py-0.2 rounded-full bg-teal-100 text-teal-800">
                                  {action.category}
                                </span>
                              </div>
                              <p className="text-xs text-stone-700 leading-relaxed">
                                {action.description}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Educational Insights List */}
                  <div>
                    <h3 className="text-sm font-extrabold text-stone-900 mb-3 flex items-center gap-2">
                      <span>💡</span> Educational Observations
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {insights.map((ins, i) => (
                        <div
                          key={ins.id || i}
                          className="p-3.5 rounded-2xl border border-stone-200 bg-white space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-xs font-bold text-stone-800">
                            <span>{ins.title}</span>
                            <span className="text-[10px] text-stone-500 uppercase font-semibold">
                              {ins.category}
                            </span>
                          </div>
                          <p className="text-xs text-stone-700 leading-relaxed">
                            {ins.description}
                          </p>
                          {ins.evidence && (
                            <div className="text-[10px] font-mono text-stone-500 bg-stone-50 p-1.5 rounded-md border border-stone-100">
                              <span className="font-semibold text-stone-700">Evidence: </span>
                              {ins.evidence}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: DOMAIN PERFORMANCE */}
              {activeTab === 'domains' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-extrabold text-stone-900">
                        Cognitive & Literacy Domains
                      </h3>
                      <p className="text-xs text-stone-500">
                        Dynamically loaded from learner intelligence profile.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" /> Strength
                      </span>
                      <span className="flex items-center gap-1 text-rose-700 font-semibold">
                        <span className="w-2 h-2 rounded-full bg-rose-500" /> Focus Area
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {domainScores.map((d, i) => (
                      <div
                        key={d.domainKey || i}
                        className="p-3.5 rounded-2xl border border-stone-200 bg-white space-y-2"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-stone-900">{d.domainName}</span>
                          <span className="font-extrabold text-stone-800">
                            {d.score > 0 ? `${Math.round(d.score)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-stone-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${
                              d.isStrength
                                ? 'bg-emerald-600'
                                : d.isPracticeArea
                                ? 'bg-rose-500'
                                : 'bg-[#1A6B6B]'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(5, d.score))}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-stone-500">
                          <span>{d.label}</span>
                          {d.isStrength && (
                            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded-full border border-emerald-200">
                              Strength
                            </span>
                          )}
                          {d.isPracticeArea && (
                            <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.2 rounded-full border border-rose-200">
                              Practice Priority
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: READING & SPEECH SIGNALS */}
              {activeTab === 'reading_speech' && (
                <div className="space-y-6">
                  {/* Reading Coach Section */}
                  <div className="bg-stone-50/50 p-4 rounded-2xl border border-stone-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-extrabold text-stone-900 flex items-center gap-2">
                        <span>📖</span> Reading Coach Metrics
                      </h3>
                      {renderTrendBadge(readingMetrics.trend)}
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Comprehension
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {readingMetrics.avgComprehensionAccuracy > 0
                            ? `${readingMetrics.avgComprehensionAccuracy.toFixed(1)}%`
                            : '—'}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Total Sessions
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {readingMetrics.completedSessions || 0}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Reading Time
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {readingMetrics.totalMinutesRead || 0} min
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Words Read
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {readingMetrics.totalWordsRead?.toLocaleString() || 0}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Speech Read-Aloud Signals Section */}
                  <div className="bg-stone-50/50 p-4 rounded-2xl border border-stone-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-extrabold text-stone-900 flex items-center gap-2">
                        <span>🎙️</span> Read-Aloud Speech Signals
                      </h3>
                      {renderTrendBadge(trends.speechTrend)}
                    </div>
                    <p className="text-[11px] text-stone-500">
                      Derived educational signals from microphone read-aloud practice. Zero raw audio recordings are stored.
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Word Accuracy
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {speechSignals.avgAccuracyRate != null
                            ? `${speechSignals.avgAccuracyRate.toFixed(1)}%`
                            : '—'}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Reading Pace
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {speechSignals.avgWpm != null
                            ? `~${Math.round(speechSignals.avgWpm)} WPM`
                            : '—'}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Latest Practice Score
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {speechSignals.latestScore != null
                            ? `${speechSignals.latestScore.toFixed(1)}%`
                            : '—'}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-stone-100">
                        <span className="text-stone-400 font-bold uppercase text-[10px] block">
                          Text Coverage
                        </span>
                        <span className="text-base font-extrabold text-stone-800">
                          {speechSignals.latestCoverage != null
                            ? `${speechSignals.latestCoverage.toFixed(1)}%`
                            : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: ADAPTIVE PRACTICE */}
              {activeTab === 'adaptive' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-extrabold text-stone-900">
                        Zone of Proximal Development & Difficulty
                      </h3>
                      <p className="text-xs text-stone-500">
                        Engineered to calibrate practice without cognitive fatigue.
                      </p>
                    </div>
                    {renderTrendBadge(trends.adaptiveTrend)}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="bg-stone-50 p-3.5 rounded-2xl border border-stone-200">
                      <span className="text-stone-400 font-bold uppercase text-[10px] block">
                        Current Tier
                      </span>
                      <span className="text-lg font-extrabold text-stone-800">
                        Tier {adaptiveState.activeDifficultyTier || 1}
                      </span>
                    </div>
                    <div className="bg-stone-50 p-3.5 rounded-2xl border border-stone-200">
                      <span className="text-stone-400 font-bold uppercase text-[10px] block">
                        Daily Streak
                      </span>
                      <span className="text-lg font-extrabold text-stone-800">
                        {adaptiveState.currentStreak || 0} days
                      </span>
                    </div>
                    <div className="bg-stone-50 p-3.5 rounded-2xl border border-stone-200">
                      <span className="text-stone-400 font-bold uppercase text-[10px] block">
                        Consecutive Passes
                      </span>
                      <span className="text-lg font-extrabold text-stone-800">
                        {adaptiveState.consecutivePasses || 0}
                      </span>
                    </div>
                    <div className="bg-stone-50 p-3.5 rounded-2xl border border-stone-200">
                      <span className="text-stone-400 font-bold uppercase text-[10px] block">
                        Tasks Completed Today
                      </span>
                      <span className="text-lg font-extrabold text-stone-800">
                        {adaptiveState.todayTasksCompleted || 0}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 5: LONGITUDINAL TRENDS */}
              {activeTab === 'trends' && (
                <div className="space-y-5">
                  <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-stone-900">
                        Longitudinal Progress Summary
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-stone-500">Reading:</span>
                        {renderTrendBadge(trends.readingTrend)}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs pt-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-stone-500">Speech Oral Read:</span>
                        {renderTrendBadge(trends.speechTrend)}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-stone-500">Adaptive Practice:</span>
                        {renderTrendBadge(trends.adaptiveTrend)}
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-extrabold text-stone-900 mb-3">
                      Historical Trend Points ({trends.points?.length || 0})
                    </h3>
                    {(!trends.points || trends.points.length === 0) ? (
                      <p className="text-xs text-stone-500 italic bg-stone-50 p-4 rounded-2xl border border-stone-200">
                        No activity checkpoints recorded in this time range.
                      </p>
                    ) : (
                      <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                        {trends.points.map((pt, i) => (
                          <div
                            key={i}
                            className="p-3 rounded-xl bg-white border border-stone-200 flex items-center justify-between text-xs"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-stone-400 font-mono text-[11px]">
                                {pt.date || '—'}
                              </span>
                              {pt.comprehensionScore != null && (
                                <span className="text-emerald-700 font-bold">
                                  Reading: {pt.comprehensionScore.toFixed(1)}%
                                </span>
                              )}
                              {pt.speechAccuracy != null && (
                                <span className="text-purple-700 font-bold">
                                  Speech: {pt.speechAccuracy.toFixed(1)}%
                                </span>
                              )}
                              {pt.activityScore != null && (
                                <span className="text-teal-700 font-bold">
                                  Activity: {pt.activityScore.toFixed(1)}%
                                </span>
                              )}
                            </div>
                            {pt.difficultyTier != null && (
                              <span className="text-[10px] font-bold bg-stone-100 text-stone-700 px-2 py-0.5 rounded-full">
                                Tier {pt.difficultyTier}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-stone-100 bg-stone-50/50 flex items-center justify-between shrink-0">
          <span className="text-[11px] text-stone-500 flex items-center gap-1">
            <span>🛡️</span> Descriptive educational analytics only. No clinical or medical diagnoses.
          </span>
          <button
            onClick={onClose}
            className="text-xs font-bold px-4 py-2 rounded-xl bg-stone-200 hover:bg-stone-300 text-stone-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
