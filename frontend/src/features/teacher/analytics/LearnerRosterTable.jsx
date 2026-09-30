/**
 * frontend/src/features/teacher/analytics/LearnerRosterTable.jsx
 *
 * Renders an accessible, searchable, and filterable roster table for classroom learners.
 */
import React, { useState, useMemo } from 'react'

export default function LearnerRosterTable({
  learners = [],
  selectedLearnerId = null,
  onSelectLearner,
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterTab, setFilterTab] = useState('all') // 'all' | 'needs_attention' | 'on_track' | 'unscreened'

  const filteredLearners = useMemo(() => {
    return learners.filter((student) => {
      // Search match
      const query = searchQuery.toLowerCase().trim()
      const nameMatch = student.name?.toLowerCase().includes(query)
      const emailMatch = student.email?.toLowerCase().includes(query)
      const matchesSearch = !query || nameMatch || emailMatch

      if (!matchesSearch) return false

      const isScreened = student.screeningCompleted ?? student.isScreened ?? false
      const status = student.status || (student.needsAttention ? 'needs_attention' : isScreened ? 'on_track' : 'not_screened')

      // Tab match
      if (filterTab === 'needs_attention') {
        return status === 'needs_attention'
      }
      if (filterTab === 'on_track') {
        return status === 'on_track'
      }
      if (filterTab === 'unscreened') {
        return !isScreened || status === 'not_screened'
      }
      return true
    })
  }, [learners, searchQuery, filterTab])

  const renderTrendBadge = (trend) => {
    switch (trend) {
      case 'improving':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            <span>↗</span>
            <span className="hidden sm:inline">Improving</span>
          </span>
        )
      case 'declining':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
            <span>↘</span>
            <span className="hidden sm:inline">Declining</span>
          </span>
        )
      case 'stable':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
            <span>→</span>
            <span className="hidden sm:inline">Stable</span>
          </span>
        )
      case 'insufficient_data':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-stone-400 bg-stone-50 px-2 py-0.5 rounded-full border border-stone-200">
            <span>—</span>
            <span className="hidden sm:inline">Gathering data</span>
          </span>
        )
    }
  }

  return (
    <div className="bg-white rounded-3xl p-5 border border-stone-200 shadow-2xs">
      {/* Table Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-extrabold text-stone-900 flex items-center gap-2">
            <span>📋</span> Classroom Learner Roster
          </h3>
          <p className="text-xs text-stone-500 mt-0.5">
            Select any learner to examine their longitudinal progress, domain scores, and reading metrics.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search learner..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-64 pl-8 pr-3 py-1.5 text-xs bg-stone-50 border border-stone-200 rounded-full focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B] focus:bg-white transition-all text-stone-800"
          />
          <span className="absolute left-2.5 top-2 text-stone-400 text-xs">🔍</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1 border-b border-stone-100">
        {[
          { id: 'all', label: 'All Learners', count: learners.length },
          {
            id: 'needs_attention',
            label: 'Needs Attention',
            count: learners.filter((l) => (l.status === 'needs_attention' || l.needsAttention)).length,
          },
          {
            id: 'on_track',
            label: 'On Track',
            count: learners.filter((l) => (l.status === 'on_track' || (!l.needsAttention && (l.screeningCompleted || l.isScreened)))).length,
          },
          {
            id: 'unscreened',
            label: 'Awaiting Screening',
            count: learners.filter((l) => !(l.screeningCompleted ?? l.isScreened)).length,
          },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilterTab(tab.id)}
            className={`text-xs font-semibold px-3 py-1.5 rounded-full transition-all shrink-0 flex items-center gap-1.5 ${
              filterTab === tab.id
                ? 'bg-[#1A6B6B] text-white shadow-2xs'
                : 'text-stone-600 hover:bg-stone-100'
            }`}
          >
            <span>{tab.label}</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                filterTab === tab.id
                  ? 'bg-white/20 text-white'
                  : 'bg-stone-200 text-stone-700'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Table Content */}
      {filteredLearners.length === 0 ? (
        <div className="text-center py-10 px-4">
          <span className="text-3xl mb-2 block">🔍</span>
          <p className="text-sm font-semibold text-stone-700">No learners match this view</p>
          <p className="text-xs text-stone-400 mt-1">
            Try adjusting your search query or switching filter tabs.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-stone-200 text-stone-500 font-bold uppercase tracking-wider text-[10px]">
                <th className="pb-3 pl-2">Learner</th>
                <th className="pb-3 text-center">Level & Tier</th>
                <th className="pb-3 text-center">Comprehension</th>
                <th className="pb-3 text-center">Speech Accuracy</th>
                <th className="pb-3 text-center">Reading Trend</th>
                <th className="pb-3 text-center">Status</th>
                <th className="pb-3 pr-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filteredLearners.map((learner) => {
                const isSelected = selectedLearnerId === learner.studentId
                const comp = learner.avgComprehension ?? learner.avgReadingComprehension ?? 0
                const speechAcc = learner.speechAccuracy ?? learner.avgSpeechAccuracy ?? null
                const trend = learner.readingTrend ?? learner.trend ?? 'insufficient_data'
                const isScreened = learner.screeningCompleted ?? learner.isScreened ?? false
                const status = learner.status || (learner.needsAttention ? 'needs_attention' : isScreened ? 'on_track' : 'not_screened')

                return (
                  <tr
                    key={learner.studentId}
                    className={`transition-colors hover:bg-stone-50/80 ${
                      isSelected ? 'bg-teal-50/60' : ''
                    }`}
                  >
                    <td className="py-3 pl-2">
                      <div className="font-bold text-stone-900 text-sm">
                        {learner.name}
                      </div>
                      <div className="text-[11px] text-stone-400 font-mono">
                        {learner.email}
                      </div>
                    </td>

                    <td className="py-3 text-center">
                      <span className="inline-block px-2 py-0.5 rounded-md font-bold bg-teal-50 text-teal-800 border border-teal-200 text-[11px] mr-1">
                        L{learner.learningLevel}
                      </span>
                      <span className="inline-block px-2 py-0.5 rounded-md font-bold bg-stone-100 text-stone-700 border border-stone-200 text-[11px]">
                        T{learner.adaptiveTier}
                      </span>
                    </td>

                    <td className="py-3 text-center font-semibold text-stone-800">
                      {comp > 0 ? (
                        <span>{comp.toFixed(1)}%</span>
                      ) : (
                        <span className="text-stone-300 font-normal">—</span>
                      )}
                    </td>

                    <td className="py-3 text-center font-semibold text-stone-800">
                      {speechAcc != null && speechAcc > 0 ? (
                        <span>{speechAcc.toFixed(1)}%</span>
                      ) : (
                        <span className="text-stone-300 font-normal">—</span>
                      )}
                    </td>

                    <td className="py-3 text-center">
                      {renderTrendBadge(trend)}
                    </td>

                    <td className="py-3 text-center">
                      {status === 'needs_attention' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-rose-50 border border-rose-200 text-rose-700">
                          Focus
                        </span>
                      ) : isScreened ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-emerald-50 border border-emerald-200 text-emerald-700">
                          On Track
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-amber-50 border border-amber-200 text-amber-700">
                          Unprofiled
                        </span>
                      )}
                    </td>

                    <td className="py-3 pr-2 text-right">
                      <button
                        onClick={() => onSelectLearner(learner)}
                        className={`text-xs font-bold px-3 py-1.5 rounded-xl transition-all ${
                          isSelected
                            ? 'bg-[#1A6B6B] text-white shadow-2xs'
                            : 'bg-stone-100 hover:bg-[#1A6B6B] hover:text-white text-stone-700'
                        }`}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
