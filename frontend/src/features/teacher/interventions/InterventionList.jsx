/**
 * frontend/src/features/teacher/interventions/InterventionList.jsx
 *
 * Renders the filterable list/cards of classroom educational support activities.
 */
import React, { useState } from 'react'

export default function InterventionList({
  interventions,
  onSelectIntervention,
  onOpenReview,
  onOpenCreate,
}) {
  const [statusFilter, setStatusFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = (interventions || []).filter((item) => {
    if (statusFilter !== 'all' && item.status !== statusFilter) return false
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchName = (item.learnerName || '').toLowerCase().includes(q)
      const matchGoal = (item.goal || '').toLowerCase().includes(q)
      const matchDomain = (item.targetDomain || '').toLowerCase().includes(q)
      if (!matchName && !matchGoal && !matchDomain) return false
    }
    return true
  })

  const statusConfig = {
    planned: { bg: 'bg-stone-100 text-stone-700 border-stone-300', label: 'Planned' },
    active: { bg: 'bg-teal-50 text-teal-800 border-teal-200', label: 'Active' },
    review: { bg: 'bg-amber-50 text-amber-800 border-amber-200', label: 'Needs Review' },
    completed: { bg: 'bg-emerald-50 text-emerald-800 border-emerald-200', label: 'Completed' },
    cancelled: { bg: 'bg-stone-100 text-stone-500 border-stone-200', label: 'Cancelled' },
  }

  const formatDate = (ts) => {
    if (!ts) return null
    return new Date(ts * 1000).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="space-y-4">
      {/* Filters Bar */}
      <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <span className="absolute left-3 top-2.5 text-stone-400 text-sm">🔍</span>
          <input
            type="text"
            placeholder="Search by student, goal, or domain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-stone-50 border border-stone-200 rounded-xl text-xs sm:text-sm focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B]"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {[
            { id: 'all', label: 'All Activities' },
            { id: 'active', label: 'Active' },
            { id: 'planned', label: 'Planned' },
            { id: 'review', label: 'In Review' },
            { id: 'completed', label: 'Completed' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap ${
                statusFilter === tab.id
                  ? 'bg-[#1A6B6B] text-white shadow-2xs'
                  : 'bg-stone-100 text-stone-600 hover:text-stone-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* List / Cards */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 border border-stone-200 text-center space-y-4 shadow-2xs">
          <div className="w-16 h-16 bg-stone-100 text-3xl rounded-2xl flex items-center justify-center mx-auto">
            🎯
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-base font-bold text-stone-800">
              {interventions.length === 0 ? 'No Support Activities Documented' : 'No Matching Activities'}
            </h3>
            <p className="text-xs text-stone-500 leading-relaxed">
              {interventions.length === 0
                ? 'Document a targeted learning support activity (like guided reading or vocabulary drills) to automatically establish a baseline and measure longitudinal progress.'
                : 'Try adjusting your search query or status filter to see other support activities.'}
            </p>
          </div>
          {interventions.length === 0 && (
            <button
              type="button"
              onClick={onOpenCreate}
              className="px-4 py-2 bg-[#1A6B6B] hover:bg-[#155353] text-white text-xs font-bold rounded-xl shadow-2xs transition-all inline-flex items-center gap-1.5"
            >
              <span>+</span> New Support Activity
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((item) => {
            const statusInfo = statusConfig[item.status] || {
              bg: 'bg-stone-100 text-stone-700',
              label: item.status,
            }

            const hasBaseline = (item.baselineMeasurements || []).some((b) => b.status === 'sufficient')
            const followUpCount = (item.followUpMeasurements || []).length

            return (
              <div
                key={item.interventionId}
                className="bg-white rounded-2xl border border-stone-200 p-5 shadow-2xs hover:shadow-xs hover:border-stone-300 transition-all flex flex-col justify-between gap-4"
              >
                {/* Card Top */}
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-xs font-bold text-stone-900 hover:text-[#1A6B6B] cursor-pointer">
                        {item.learnerName || 'Student'}
                      </span>
                      <p className="text-[11px] text-stone-400 font-mono">
                        Classroom: {item.classroomCode}
                      </p>
                    </div>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${statusInfo.bg}`}
                    >
                      {statusInfo.label}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-stone-900 leading-snug line-clamp-1">
                      {item.goal}
                    </h4>
                    <p className="text-xs text-stone-600 line-clamp-2 mt-0.5 leading-relaxed">
                      {item.supportActivity}
                    </p>
                  </div>
                </div>

                {/* Card Meta Badges */}
                <div className="pt-3 border-t border-stone-100 space-y-2.5">
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="px-2 py-0.5 rounded-md bg-stone-100 text-stone-700 font-semibold capitalize">
                      {item.targetDomain.replace('_', ' ')}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-md font-semibold ${
                        hasBaseline
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-amber-50 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {hasBaseline ? '✓ Baseline Ready' : '⏳ Baseline Insufficient'}
                    </span>
                    {followUpCount > 0 && (
                      <span className="px-2 py-0.5 rounded-md bg-teal-50 text-teal-800 border border-teal-200 font-semibold">
                        {followUpCount} Follow-Up(s)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-stone-400">
                    <span>Started: {formatDate(item.startDate)}</span>
                    {item.plannedReviewDate && (
                      <span>Review: {formatDate(item.plannedReviewDate)}</span>
                    )}
                  </div>
                </div>

                {/* Card Actions */}
                <div className="pt-2 flex items-center justify-end gap-2 border-t border-stone-100">
                  {item.status === 'review' && (
                    <button
                      type="button"
                      onClick={() => onOpenReview(item)}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-xl transition-all"
                    >
                      Review Evidence
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => onSelectIntervention(item.interventionId)}
                    className="px-3.5 py-1.5 bg-[#1A6B6B] hover:bg-[#155353] text-white text-xs font-bold rounded-xl shadow-2xs transition-all flex items-center gap-1"
                  >
                    <span>Inspect & Measure</span> →
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
