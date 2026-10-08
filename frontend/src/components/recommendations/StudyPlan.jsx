/**
 * frontend/src/components/recommendations/StudyPlan.jsx
 *
 * Lightweight, structured daily study plan for learners.
 * Bounded to 2-4 manageable activities. Reflects real database completion state.
 */
import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from '../../i18n/I18nContext'

export default function StudyPlan({
  studyPlan,
  horizon = 'today',
  onSelectHorizon,
}) {
  const { t } = useTranslation()

  if (!studyPlan) return null

  const items = studyPlan.items || []
  const totalMinutes = studyPlan.totalEstimatedMinutes || 0
  const completedCount = studyPlan.completedCount || 0
  const totalCount = studyPlan.totalCount || items.length
  const percentComplete = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  return (
    <section
      className="bg-white rounded-3xl p-6 border border-stone-200/90 shadow-2xs space-y-5"
      aria-labelledby="study-plan-heading"
    >
      {/* Plan Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">📋</span>
            <h2 id="study-plan-heading" className="text-lg font-black text-stone-900 tracking-tight">
              {t('recommendations.studyPlanTitle', 'Your Daily Study Plan')}
            </h2>
          </div>
          <p className="text-xs text-stone-500 mt-0.5">
            Manageable, sequential practice tailored for today.
          </p>
        </div>

        {/* Horizon Toggle */}
        <div className="flex items-center gap-2">
          <div className="inline-flex p-1 bg-stone-100 rounded-2xl border border-stone-200">
            {[
              { id: 'today', label: t('recommendations.horizonToday', 'Today') },
              { id: '7d', label: t('recommendations.horizon7d', 'Next 7 Days') },
            ].map((h) => {
              const isSelected = horizon === h.id
              return (
                <button
                  key={h.id}
                  type="button"
                  onClick={() => onSelectHorizon && onSelectHorizon(h.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] ${
                    isSelected
                      ? 'bg-[#1A6B6B] text-white shadow-xs'
                      : 'text-stone-600 hover:text-stone-900'
                  }`}
                  aria-pressed={isSelected}
                >
                  {h.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Progress & Duration Bar */}
      <div className="bg-stone-50 rounded-2xl p-4 border border-stone-200/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="text-xs font-bold text-stone-600">
            <span>🎯 Progress: </span>
            <span className="text-stone-900 font-black">{completedCount}</span>
            <span> of </span>
            <span className="text-stone-900 font-black">{totalCount}</span>
            <span> ({percentComplete}%)</span>
          </div>

          <div className="w-28 sm:w-40 bg-stone-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-emerald-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${percentComplete}%` }}
              role="progressbar"
              aria-valuenow={percentComplete}
              aria-valuemin="0"
              aria-valuemax="100"
            />
          </div>
        </div>

        <div className="text-xs font-bold text-stone-500 flex items-center gap-1.5">
          <span aria-hidden="true">⏱️</span>
          <span>{t('recommendations.totalTime', 'Est. Time')}: </span>
          <span className="text-stone-900 font-black">{totalMinutes} mins</span>
        </div>
      </div>

      {/* Activities List */}
      <div className="space-y-3">
        {items.map((item, idx) => (
          <div
            key={item.id || idx}
            className={`p-4 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
              item.completed
                ? 'bg-emerald-50/40 border-emerald-200/80 text-emerald-950'
                : 'bg-white border-stone-200 hover:border-[#1A6B6B]/40'
            }`}
          >
            <div className="flex items-start sm:items-center gap-3">
              <span
                className={`w-7 h-7 shrink-0 rounded-full flex items-center justify-center text-xs font-extrabold ${
                  item.completed
                    ? 'bg-emerald-600 text-white'
                    : 'bg-stone-100 text-stone-700 border border-stone-300'
                }`}
                aria-label={item.completed ? 'Completed' : `Priority ${item.priority}`}
              >
                {item.completed ? '✓' : item.priority}
              </span>

              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-extrabold text-stone-900">
                    {item.title}
                  </h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 bg-stone-100 text-stone-600 rounded-full border border-stone-200">
                    {item.estimatedDurationMinutes}m
                  </span>
                </div>
                <p className="text-xs text-stone-600 line-clamp-1">
                  {item.reason}
                </p>
              </div>
            </div>

            <Link
              to={item.actionUrl}
              className={`shrink-0 inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-offset-1 ${
                item.completed
                  ? 'bg-emerald-100 text-emerald-900 hover:bg-emerald-200 focus:ring-emerald-500'
                  : 'bg-[#1A6B6B] text-white hover:bg-[#155555] focus:ring-[#1A6B6B]'
              }`}
            >
              <span>{item.completed ? 'Review' : 'Start'}</span>
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        ))}
      </div>
    </section>
  )
}
