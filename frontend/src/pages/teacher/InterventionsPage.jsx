/**
 * frontend/src/pages/teacher/InterventionsPage.jsx
 *
 * DyslexAid V2 — Phase 8: Intervention Effectiveness Page
 * Helps teachers document learning support activities, establish baselines from existing
 * practice data, track subsequent learning measurements, and review observed changes over time.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { interventionV2API } from '../../api/v2/client'
import {
  InterventionList,
  CreateInterventionModal,
  InterventionDetailModal,
  InterventionReviewModal,
} from '../../features/teacher/interventions'
import toast from 'react-hot-toast'

export default function InterventionsPage() {
  const [interventions, setInterventions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Modals state
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [selectedInterventionId, setSelectedInterventionId] = useState(null)
  const [reviewIntervention, setReviewIntervention] = useState(null)

  const loadInterventions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await interventionV2API.getInterventions()
      setInterventions(data || [])
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err.message ||
        'Failed to load classroom interventions.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadInterventions()
  }, [loadInterventions])

  // Aggregate stats
  const totalCount = interventions.length
  const activeCount = interventions.filter((i) => i.status === 'active').length
  const reviewCount = interventions.filter((i) => i.status === 'review').length
  const completedCount = interventions.filter((i) => i.status === 'completed').length

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-3xl p-6 border border-stone-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">🎯</span>
            <h1 className="text-xl sm:text-2xl font-black text-stone-900 tracking-tight">
              Support Activities & Intervention Effectiveness
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-stone-500 max-w-2xl">
            Document educational support activities, establish student baselines from practice sessions,
            track follow-up measurements, and review observed changes over time.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            id="btn-refresh-interventions"
            type="button"
            onClick={loadInterventions}
            disabled={loading}
            className="p-2.5 rounded-xl border border-stone-200 bg-stone-50 text-stone-600 hover:text-stone-900 transition-all text-sm"
            title="Refresh interventions"
          >
            🔄
          </button>
          <button
            id="btn-new-support-activity"
            type="button"
            onClick={() => setCreateModalOpen(true)}
            className="px-4 py-2.5 bg-[#1A6B6B] hover:bg-[#155353] text-white text-xs sm:text-sm font-bold rounded-xl shadow-2xs transition-all flex items-center gap-1.5"
          >
            <span>+</span> New Support Activity
          </button>
        </div>
      </div>

      {/* Metrics Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-2xs">
          <p className="text-xs text-stone-500 font-semibold uppercase tracking-wider">Total Recorded</p>
          <p className="text-2xl font-black text-stone-900 mt-1">{totalCount}</p>
          <p className="text-[11px] text-stone-400 mt-0.5">Instructional activities</p>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-2xs">
          <p className="text-xs text-teal-700 font-semibold uppercase tracking-wider">Active Support</p>
          <p className="text-2xl font-black text-teal-800 mt-1">{activeCount}</p>
          <p className="text-[11px] text-teal-600 mt-0.5">Currently gathering data</p>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-2xs">
          <p className="text-xs text-amber-700 font-semibold uppercase tracking-wider">Needs Review</p>
          <p className="text-2xl font-black text-amber-800 mt-1">{reviewCount}</p>
          <p className="text-[11px] text-amber-600 mt-0.5">Pending teacher check-in</p>
        </div>

        <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-2xs">
          <p className="text-xs text-emerald-700 font-semibold uppercase tracking-wider">Completed</p>
          <p className="text-2xl font-black text-emerald-800 mt-1">{completedCount}</p>
          <p className="text-[11px] text-emerald-600 mt-0.5">Resolved activities</p>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="bg-white rounded-3xl p-16 border border-stone-200 text-center space-y-3 shadow-2xs">
          <div className="w-10 h-10 border-3 border-[#1A6B6B] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-stone-500 font-bold uppercase tracking-wider">
            Loading educational interventions...
          </p>
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-700 p-6 rounded-3xl border border-red-200 text-center space-y-3">
          <p className="font-bold text-sm">Failed to Load Support Activities</p>
          <p className="text-xs">{error}</p>
          <button
            type="button"
            onClick={loadInterventions}
            className="px-4 py-1.5 bg-red-600 text-white text-xs font-bold rounded-xl"
          >
            Retry
          </button>
        </div>
      ) : (
        <InterventionList
          interventions={interventions}
          onSelectIntervention={(id) => setSelectedInterventionId(id)}
          onOpenReview={(intv) => setReviewIntervention(intv)}
          onOpenCreate={() => setCreateModalOpen(true)}
        />
      )}

      {/* Create Support Activity Modal */}
      <CreateInterventionModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={() => {
          loadInterventions()
        }}
      />

      {/* Intervention Detail Modal */}
      <InterventionDetailModal
        isOpen={Boolean(selectedInterventionId)}
        interventionId={selectedInterventionId}
        onClose={() => setSelectedInterventionId(null)}
        onStatusChanged={() => {
          loadInterventions()
        }}
        onOpenReview={(intv) => {
          setSelectedInterventionId(null)
          setReviewIntervention(intv)
        }}
      />

      {/* Review Support Activity Modal */}
      <InterventionReviewModal
        isOpen={Boolean(reviewIntervention)}
        intervention={reviewIntervention}
        onClose={() => setReviewIntervention(null)}
        onReviewed={() => {
          loadInterventions()
        }}
      />
    </div>
  )
}
