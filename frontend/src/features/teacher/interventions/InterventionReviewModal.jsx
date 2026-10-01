/**
 * frontend/src/features/teacher/interventions/InterventionReviewModal.jsx
 *
 * Dedicated modal for teachers to review intervention evidence, record pedagogical observations,
 * and select next steps (Continue, Complete, or Cancel) subject to valid state transitions.
 */
import React, { useState } from 'react'
import { interventionV2API } from '../../../api/v2/client'
import toast from 'react-hot-toast'

export default function InterventionReviewModal({ isOpen, onClose, intervention, onReviewed }) {
  const [decision, setDecision] = useState('continue') // 'continue' | 'complete' | 'cancel'
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!isOpen || !intervention) return null

  const handleReviewSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const intvId = intervention.interventionId
      let res

      if (decision === 'continue') {
        // Transition review -> active (continue)
        res = await interventionV2API.startIntervention(intvId, {
          notes: notes.trim() || 'Teacher decided to continue support activity.',
          reviewDecision: 'continue',
        })
        toast.success('Intervention status maintained as active.')
      } else if (decision === 'complete') {
        // Transition review -> completed
        res = await interventionV2API.completeIntervention(intvId, {
          notes: notes.trim() || 'Teacher marked support activity as completed.',
          reviewDecision: 'complete',
        })
        toast.success('Support activity marked as completed.')
      } else if (decision === 'cancel') {
        // Transition review -> cancelled
        res = await interventionV2API.cancelIntervention(intvId, {
          notes: notes.trim() || 'Teacher cancelled support activity.',
          reviewDecision: 'cancel',
        })
        toast.success('Support activity cancelled.')
      }

      onReviewed(res)
      onClose()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to submit review decision.'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/60 backdrop-blur-xs overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl border border-stone-200 shadow-2xl max-w-xl w-full p-6 sm:p-8 space-y-6 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-stone-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">📋</span>
              <h2 className="text-xl font-black text-stone-900">Review Support Activity</h2>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              Review observed changes and determine next pedagogical steps for {intervention.learnerName || 'this student'}.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 text-2xl leading-none p-1 rounded-lg"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* Goal Summary */}
        <div className="p-4 bg-stone-50 rounded-2xl border border-stone-200/70 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-stone-700 uppercase tracking-wider">Goal:</span>
            <span className="font-mono text-stone-500 text-[11px]">{intervention.interventionId}</span>
          </div>
          <p className="text-stone-900 font-semibold text-sm">{intervention.goal}</p>
          <p className="text-stone-600">{intervention.supportActivity}</p>
        </div>

        {/* Decision Form */}
        <form onSubmit={handleReviewSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-2">
              Teacher Decision *
            </label>
            <div className="space-y-2">
              <label
                className={`flex items-start gap-3 p-3.5 rounded-2xl border cursor-pointer transition-all ${
                  decision === 'continue'
                    ? 'border-[#1A6B6B] bg-teal-50/40 text-stone-900 ring-1 ring-[#1A6B6B]'
                    : 'border-stone-200 bg-white hover:bg-stone-50 text-stone-700'
                }`}
              >
                <input
                  type="radio"
                  name="decision"
                  value="continue"
                  checked={decision === 'continue'}
                  onChange={() => setDecision('continue')}
                  className="mt-0.5 text-[#1A6B6B] focus:ring-[#1A6B6B]"
                />
                <div>
                  <p className="font-bold text-sm">Continue Support Activity</p>
                  <p className="text-xs text-stone-500 mt-0.5">
                    Keep the intervention active to continue gathering student practice measurements.
                  </p>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3.5 rounded-2xl border cursor-pointer transition-all ${
                  decision === 'complete'
                    ? 'border-emerald-600 bg-emerald-50/40 text-stone-900 ring-1 ring-emerald-600'
                    : 'border-stone-200 bg-white hover:bg-stone-50 text-stone-700'
                }`}
              >
                <input
                  type="radio"
                  name="decision"
                  value="complete"
                  checked={decision === 'complete'}
                  onChange={() => setDecision('complete')}
                  className="mt-0.5 text-emerald-600 focus:ring-emerald-600"
                />
                <div>
                  <p className="font-bold text-sm">Complete Support Activity</p>
                  <p className="text-xs text-stone-500 mt-0.5">
                    Mark intervention as completed. Locks in final measurements and stores review history.
                  </p>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3.5 rounded-2xl border cursor-pointer transition-all ${
                  decision === 'cancel'
                    ? 'border-stone-400 bg-stone-100 text-stone-900 ring-1 ring-stone-400'
                    : 'border-stone-200 bg-white hover:bg-stone-50 text-stone-700'
                }`}
              >
                <input
                  type="radio"
                  name="decision"
                  value="cancel"
                  checked={decision === 'cancel'}
                  onChange={() => setDecision('cancel')}
                  className="mt-0.5 text-stone-600 focus:ring-stone-600"
                />
                <div>
                  <p className="font-bold text-sm">Discontinue / Cancel Support</p>
                  <p className="text-xs text-stone-500 mt-0.5">
                    Cancel this support activity if the learning priority has changed or is no longer applicable.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Teacher Review Notes */}
          <div>
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
              Teacher Review Observations & Next Steps
            </label>
            <textarea
              rows={3}
              placeholder="e.g. Student showed steady progress on story comprehension. Will transition to independent reading practice."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-stone-200 bg-stone-50 text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B]"
            />
          </div>

          {/* Notice */}
          <p className="text-[11px] text-stone-500 italic">
            Note: The system supports your decision by recording educational observations. Decisions are always teacher-directed.
          </p>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-stone-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-stone-600 hover:text-stone-900 text-sm font-bold rounded-xl transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 bg-[#1A6B6B] hover:bg-[#155353] text-white text-sm font-bold rounded-xl shadow-2xs transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {submitting ? 'Applying Decision...' : 'Confirm Review Decision'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
