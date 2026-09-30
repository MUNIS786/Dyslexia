/**
 * frontend/src/features/teacher/analytics/ClassOverviewCards.jsx
 *
 * Renders cohort-level summary metric cards for the teacher dashboard.
 */
import React from 'react'

export default function ClassOverviewCards({ overview }) {
  if (!overview) return null

  const {
    totalLearners = 0,
    activeLearners = 0,
    screenedLearners = 0,
    needsAttentionCount = 0,
    onTrackCount = 0,
    avgLearningLevel = 0,
    avgAdaptiveTier = 1,
    avgReadingComprehension = 0,
    avgSpeechAccuracy = 0,
    avgWordsPerMinute = 0,
    totalWordsRead = 0,
    totalMinutesRead = 0,
    activityAttemptsCount = 0,
  } = overview

  const cards = [
    {
      title: 'Enrolled Learners',
      value: totalLearners,
      sub: `${activeLearners} active in window`,
      icon: '👥',
      color: 'bg-teal-50 border-teal-200 text-teal-900',
    },
    {
      title: 'Screening Baseline',
      value: `${screenedLearners}/${totalLearners}`,
      sub: `${totalLearners > 0 ? Math.round((screenedLearners / totalLearners) * 100) : 0}% profiled`,
      icon: '🌟',
      color: 'bg-amber-50 border-amber-200 text-amber-900',
    },
    {
      title: 'Avg Learning Level',
      value: `Level ${avgLearningLevel.toFixed(1)}`,
      sub: `Avg Tier ${avgAdaptiveTier.toFixed(1)}`,
      icon: '🎯',
      color: 'bg-blue-50 border-blue-200 text-blue-900',
    },
    {
      title: 'Reading Comprehension',
      value: avgReadingComprehension > 0 ? `${avgReadingComprehension.toFixed(1)}%` : '—',
      sub: `${totalWordsRead.toLocaleString()} words read`,
      icon: '📖',
      color: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    },
    {
      title: 'Read-Aloud Accuracy',
      value: avgSpeechAccuracy > 0 ? `${avgSpeechAccuracy.toFixed(1)}%` : '—',
      sub: avgWordsPerMinute > 0 ? `~${Math.round(avgWordsPerMinute)} WPM` : 'Awaiting practice',
      icon: '🎙️',
      color: 'bg-purple-50 border-purple-200 text-purple-900',
    },
    {
      title: 'Support Triage',
      value: `${needsAttentionCount} Needs Focus`,
      sub: `${onTrackCount} on track`,
      icon: '⚡',
      color: needsAttentionCount > 0 ? 'bg-rose-50 border-rose-200 text-rose-900' : 'bg-stone-50 border-stone-200 text-stone-900',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
      {cards.map((c, i) => (
        <div
          key={i}
          className={`p-4 rounded-3xl border shadow-2xs transition-all hover:shadow-xs ${c.color} flex flex-col justify-between`}
        >
          <div className="flex items-center justify-between gap-1 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider opacity-75 truncate">
              {c.title}
            </span>
            <span className="text-xl shrink-0">{c.icon}</span>
          </div>
          <div>
            <div className="text-xl sm:text-2xl font-extrabold tracking-tight">
              {c.value}
            </div>
            <div className="text-[11px] font-medium opacity-80 mt-1 truncate">
              {c.sub}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
