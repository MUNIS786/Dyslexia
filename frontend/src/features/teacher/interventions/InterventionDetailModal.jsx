/**
 * frontend/src/features/teacher/interventions/InterventionDetailModal.jsx
 *
 * Detailed view of an individual learning support activity:
 * - Goal & description
 * - Pre-support baseline values and sources
 * - Follow-up observations
 * - Before-and-after metric comparisons (EffectivenessComparisonCard)
 * - Data sufficiency warnings & overall summary
 * - Teacher review history & stage notes
 * - Valid lifecycle actions (Start, Review, Complete, Cancel, Add Measurement)
 */
import React, { useState, useEffect, useCallback } from 'react'
import { interventionV2API } from '../../../api/v2/client'
import EffectivenessComparisonCard from './EffectivenessComparisonCard'
import toast from 'react-hot-toast'

export default function InterventionDetailModal({
  isOpen,
  onClose,
  interventionId,
  onStatusChanged,
  onOpenReview,
}) {
  const [loading, setLoading] = useState(true)
  const [report, setReport] = useState(null)
  const [intervention, setIntervention] = useState(null)
  const [error, setError] = useState(null)

  // Manual measurement form state
  const [showManualForm, setShowManualForm] = useState(false)
  const [manualMetric, setManualMetric] = useState('oral_reading_accuracy')
  const [manualValue, setManualValue] = useState('')
  const [manualNotes, setManualNotes] = useState('')
  const [savingManual, setSavingManual] = useState(false)

  const loadData = useCallback(async () => {
    if (!interventionId) return
    setLoading(true)
    setError(null)
    try {
      const [intvDoc, effReport] = await Promise.all([
        interventionV2API.getIntervention(interventionId),
        interventionV2API.getEffectiveness(interventionId),
      ])
      setIntervention(intvDoc)
      setReport(effReport)
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to load intervention details.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [interventionId])

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen, loadData])

  if (!isOpen) return null

  const handleStart = async () => {
    try {
      const res = await interventionV2API.startIntervention(interventionId, {
        notes: 'Intervention officially activated by teacher.',
      })
      toast.success('Support activity started!')
      onStatusChanged(res)
      loadData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to start intervention.')
    }
  }

  const handleComplete = async () => {
    try {
      const res = await interventionV2API.completeIntervention(interventionId, {
        notes: 'Intervention completed by teacher.',
      })
      toast.success('Support activity completed!')
      onStatusChanged(res)
      loadData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to complete intervention.')
    }
  }

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this support activity?')) return
    try {
      const res = await interventionV2API.cancelIntervention(interventionId, {
        notes: 'Intervention cancelled by teacher.',
      })
      toast.success('Support activity cancelled.')
      onStatusChanged(res)
      loadData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to cancel intervention.')
    }
  }

  const handleAddManualMeasurement = async (e) => {
    e.preventDefault()
    const val = parseFloat(manualValue)
    if (isNaN(val)) {
      toast.error('Please enter a valid numeric value.')
      return
    }

    setSavingManual(true)
    try {
      await interventionV2API.addMeasurement(interventionId, {
        metricName: manualMetric,
        value: val,
        unit: '%',
        scale: '0-100%',
        notes: manualNotes.trim() || undefined,
      })
      toast.success('Observation recorded!')
      setShowManualForm(false)
      setManualValue('')
      setManualNotes('')
      loadData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to record measurement.')
    } finally {
      setSavingManual(false)
    }
  }

  const statusBadge = (status) => {
    const map = {
      planned: 'bg-stone-100 text-stone-700 border-stone-300',
      active: 'bg-teal-50 text-teal-800 border-teal-200',
      review: 'bg-amber-50 text-amber-800 border-amber-200',
      completed: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      cancelled: 'bg-stone-100 text-stone-500 border-stone-200',
    }
    return map[status] || 'bg-stone-100 text-stone-700 border-stone-200'
  }

  const formatDate = (ts) => {
    if (!ts) return 'Not set'
    return new Date(ts * 1000).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/60 backdrop-blur-xs overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl border border-stone-200 shadow-2xl max-w-4xl w-full p-6 sm:p-8 space-y-6 my-8 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-stone-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎯</span>
              <h2 className="text-xl font-black text-stone-900">
                {report?.learnerName || intervention?.learnerName || 'Student'} — Support Activity
              </h2>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              ID: <span className="font-mono">{interventionId}</span> • Classroom:{' '}
              <span className="font-mono">{intervention?.classroomCode}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${statusBadge(
                intervention?.status
              )}`}
            >
              {intervention?.status || 'Loading'}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="text-stone-400 hover:text-stone-700 text-2xl leading-none p-1 rounded-lg"
              aria-label="Close modal"
            >
              ×
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-10 h-10 border-3 border-[#1A6B6B] border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-stone-500 font-bold uppercase tracking-wider">
              Gathering educational measurements & calculating changes...
            </p>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 text-red-700 rounded-2xl text-sm border border-red-200">
            {error}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Goal & Activity Card */}
            <div className="bg-stone-50 rounded-2xl p-5 border border-stone-200/70 space-y-3">
              <div>
                <span className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">
                  Target Domain & Goal
                </span>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs font-bold text-[#1A6B6B] uppercase tracking-wider px-2 py-0.5 bg-teal-50 rounded-md border border-teal-200">
                    {intervention.targetDomain.replace('_', ' ')}
                  </span>
                  <p className="text-base font-bold text-stone-900">{intervention.goal}</p>
                </div>
              </div>

              <div>
                <span className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">
                  Planned Support Activity
                </span>
                <p className="text-sm text-stone-700 mt-0.5 leading-relaxed">
                  {intervention.supportActivity}
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-stone-200/60 text-xs">
                <div>
                  <span className="text-stone-400">Start Date:</span>
                  <p className="font-semibold text-stone-800">{formatDate(intervention.startDate)}</p>
                </div>
                <div>
                  <span className="text-stone-400">Planned Review:</span>
                  <p className="font-semibold text-stone-800">{formatDate(intervention.plannedReviewDate)}</p>
                </div>
                <div>
                  <span className="text-stone-400">Created At:</span>
                  <p className="font-semibold text-stone-800">{formatDate(intervention.createdAt)}</p>
                </div>
                <div>
                  <span className="text-stone-400">Last Synced:</span>
                  <p className="font-semibold text-stone-800">{formatDate(intervention.updatedAt)}</p>
                </div>
              </div>
            </div>

            {/* Overall Sufficiency & Summary */}
            <div className="p-4 rounded-2xl border bg-white border-stone-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-stone-700 uppercase tracking-wider">
                  Longitudinal Evidence Summary
                </span>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                    report?.dataSufficiency === 'sufficient'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border border-amber-200'
                  }`}
                >
                  {report?.dataSufficiency.replace('_', ' ')}
                </span>
              </div>
              <p className="text-sm text-stone-800 leading-relaxed font-medium">
                {report?.overallSummary}
              </p>
            </div>

            {/* Comparisons Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black text-stone-900 uppercase tracking-wider">
                  Measured Performance Changes
                </h3>
                <button
                  type="button"
                  onClick={loadData}
                  className="text-xs font-bold text-[#1A6B6B] hover:text-[#155353] flex items-center gap-1"
                >
                  <span>🔄</span> Refresh Practice Data
                </button>
              </div>

              {report?.comparisons && report.comparisons.length > 0 ? (
                <div className="space-y-3">
                  {report.comparisons.map((c) => (
                    <EffectivenessComparisonCard key={c.metricName} comparison={c} />
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center bg-stone-50 rounded-2xl border border-stone-200 text-stone-500 text-xs">
                  No compatible metrics currently tracked for this domain.
                </div>
              )}
            </div>

            {/* Teacher Observations & Review History */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black text-stone-900 uppercase tracking-wider">
                  Teacher Observations & Review History
                </h3>
                {intervention.status === 'active' && !showManualForm && (
                  <button
                    type="button"
                    onClick={() => setShowManualForm(true)}
                    className="text-xs font-bold text-[#1A6B6B] hover:text-[#155353]"
                  >
                    + Add Interim Observation
                  </button>
                )}
              </div>

              {/* Optional Manual Observation Form */}
              {showManualForm && (
                <form
                  onSubmit={handleAddManualMeasurement}
                  className="p-4 bg-teal-50/50 rounded-2xl border border-teal-200 space-y-3 text-xs"
                >
                  <div className="flex items-center justify-between font-bold text-teal-900">
                    <span>Record Oral Check-In or Assessment</span>
                    <button
                      type="button"
                      onClick={() => setShowManualForm(false)}
                      className="text-stone-400 hover:text-stone-700"
                    >
                      Cancel
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-stone-700 font-bold mb-1">Metric Title</label>
                      <input
                        type="text"
                        value={manualMetric}
                        onChange={(e) => setManualMetric(e.target.value)}
                        className="w-full p-2 rounded-lg border border-stone-200 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-stone-700 font-bold mb-1">Score / Value (%)</label>
                      <input
                        type="number"
                        placeholder="e.g. 85"
                        value={manualValue}
                        onChange={(e) => setManualValue(e.target.value)}
                        className="w-full p-2 rounded-lg border border-stone-200 bg-white"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-stone-700 font-bold mb-1">Notes</label>
                    <input
                      type="text"
                      placeholder="e.g. Student read 2 paragraphs with good expression."
                      value={manualNotes}
                      onChange={(e) => setManualNotes(e.target.value)}
                      className="w-full p-2 rounded-lg border border-stone-200 bg-white"
                    />
                  </div>
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={savingManual}
                      className="px-3.5 py-1.5 bg-[#1A6B6B] text-white font-bold rounded-lg shadow-2xs"
                    >
                      {savingManual ? 'Saving...' : 'Save Observation'}
                    </button>
                  </div>
                </form>
              )}

              {intervention?.teacherObservations && intervention.teacherObservations.length > 0 ? (
                <div className="space-y-2">
                  {intervention.teacherObservations.map((obs, idx) => (
                    <div
                      key={obs.observationId || idx}
                      className="p-3 bg-stone-50 rounded-xl border border-stone-100 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between text-stone-400">
                        <span className="font-bold text-stone-700 uppercase tracking-wider">
                          Stage: {obs.stage || 'checkin'}
                        </span>
                        <span>{formatDate(obs.timestamp)}</span>
                      </div>
                      <p className="text-stone-800 leading-relaxed">{obs.notes}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-stone-400 italic">No notes recorded yet.</p>
              )}
            </div>

            {/* Non-Clinical Disclaimer */}
            <div className="p-3.5 bg-stone-100 rounded-xl text-stone-600 text-[11px] leading-relaxed border border-stone-200">
              <span className="font-bold text-stone-800">Educational Notice: </span>
              {report?.disclaimer ||
                'This educational measurement system provides descriptive comparisons of observed learner practice data over time. It does not establish clinical efficacy or prove that the support activity caused the observed changes.'}
            </div>

            {/* Modal Footer Lifecycle Actions */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-stone-100">
              <div className="flex items-center gap-2">
                {intervention.status !== 'completed' && intervention.status !== 'cancelled' && (
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-3.5 py-2 text-stone-500 hover:text-red-700 text-xs font-bold rounded-xl transition-all"
                  >
                    Cancel Activity
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                {intervention.status === 'planned' && (
                  <button
                    type="button"
                    onClick={handleStart}
                    className="px-5 py-2.5 bg-[#1A6B6B] hover:bg-[#155353] text-white text-xs font-bold rounded-xl shadow-2xs transition-all"
                  >
                    ▶ Start Support Activity
                  </button>
                )}

                {intervention.status === 'active' && (
                  <>
                    <button
                      type="button"
                      onClick={() => onOpenReview(intervention)}
                      className="px-4 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-xl shadow-2xs transition-all flex items-center gap-1.5"
                    >
                      <span>📋</span> Review Evidence
                    </button>
                    <button
                      type="button"
                      onClick={handleComplete}
                      className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-2xs transition-all flex items-center gap-1.5"
                    >
                      <span>✓</span> Mark Completed
                    </button>
                  </>
                )}

                {intervention.status === 'review' && (
                  <button
                    type="button"
                    onClick={() => onOpenReview(intervention)}
                    className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-xl shadow-2xs transition-all flex items-center gap-1.5"
                  >
                    <span>📋</span> Complete Review Decision
                  </button>
                )}

                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold rounded-xl transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
