/**
 * frontend/src/features/teacher/interventions/CreateInterventionModal.jsx
 *
 * Validated modal form for creating an educational support activity / intervention.
 * Enforces learner selection, domain selection, goal, support activity description,
 * start date, and optional review date.
 */
import React, { useState, useEffect } from 'react'
import { teacherV2API, interventionV2API } from '../../../api/v2/client'
import toast from 'react-hot-toast'

const DOMAIN_OPTIONS = [
  { id: 'reading_comprehension', label: 'Reading Comprehension (Story Understanding)' },
  { id: 'reading_fluency', label: 'Reading Fluency (Flow & Pacing)' },
  { id: 'phonological_awareness', label: 'Phonological Awareness (Sound Practice)' },
  { id: 'orthographic_spelling', label: 'Orthographic & Spelling (Word Patterns)' },
  { id: 'working_memory', label: 'Working Memory (Sequence & Memory)' },
  { id: 'visual_processing', label: 'Visual Processing (Shape & Letter Tracking)' },
  { id: 'language_processing', label: 'Language Processing (Vocabulary & Sentences)' },
  { id: 'letter_reversal', label: 'Letter Orientation (b/d/p/q Clarity)' },
]

export default function CreateInterventionModal({ isOpen, onClose, onCreated, preselectedStudentId }) {
  const [learners, setLearners] = useState([])
  const [loadingLearners, setLoadingLearners] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const todayStr = new Date().toISOString().split('T')[0]

  const [formData, setFormData] = useState({
    learnerId: preselectedStudentId || '',
    targetDomain: 'reading_comprehension',
    goal: '',
    supportActivity: '',
    startDate: todayStr,
    plannedReviewDate: '',
    initialNotes: '',
  })
  const [errors, setErrors] = useState({})

  useEffect(() => {
    if (!isOpen) return
    const fetchLearners = async () => {
      setLoadingLearners(true)
      try {
        const roster = await teacherV2API.getLearners('all')
        setLearners(roster || [])
        if (!formData.learnerId && roster && roster.length > 0) {
          setFormData((prev) => ({ ...prev, learnerId: roster[0].studentId }))
        }
      } catch (err) {
        toast.error('Failed to load student list.')
      } finally {
        setLoadingLearners(false)
      }
    }
    fetchLearners()
  }, [isOpen])

  useEffect(() => {
    if (preselectedStudentId) {
      setFormData((prev) => ({ ...prev, learnerId: preselectedStudentId }))
    }
  }, [preselectedStudentId])

  if (!isOpen) return null

  const validate = () => {
    const errs = {}
    if (!formData.learnerId) errs.learnerId = 'Please select a student.'
    if (!formData.goal || formData.goal.trim().length < 3) {
      errs.goal = 'Educational goal must be at least 3 characters.'
    }
    if (!formData.supportActivity || formData.supportActivity.trim().length < 3) {
      errs.supportActivity = 'Support activity description must be at least 3 characters.'
    }
    if (!formData.startDate) {
      errs.startDate = 'Start date is required.'
    }
    if (formData.plannedReviewDate && formData.plannedReviewDate < formData.startDate) {
      errs.plannedReviewDate = 'Review date cannot be earlier than start date.'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    try {
      const startTimestamp = Math.floor(new Date(formData.startDate).getTime() / 1000)
      const reviewTimestamp = formData.plannedReviewDate
        ? Math.floor(new Date(formData.plannedReviewDate).getTime() / 1000)
        : null

      const payload = {
        learnerId: formData.learnerId,
        targetDomain: formData.targetDomain,
        goal: formData.goal.trim(),
        supportActivity: formData.supportActivity.trim(),
        startDate: startTimestamp,
        plannedReviewDate: reviewTimestamp,
        initialNotes: formData.initialNotes.trim() || null,
      }

      const res = await interventionV2API.createIntervention(payload)
      toast.success('Support activity recorded and baseline established!')
      onCreated(res)
      onClose()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Failed to create intervention.'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const selectedLearner = learners.find((l) => l.studentId === formData.learnerId)

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/60 backdrop-blur-xs overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl border border-stone-200 shadow-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-stone-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎯</span>
              <h2 className="text-xl font-black text-stone-900">New Learning Support Activity</h2>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              Document an educational intervention and automatically establish a practice baseline.
            </p>
          </div>
          <button
            id="btn-close-create-modal"
            type="button"
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 text-2xl leading-none p-1 rounded-lg"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Student Selector */}
          <div>
            <label htmlFor="select-intervention-student" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
              Select Student *
            </label>
            <select
              id="select-intervention-student"
              value={formData.learnerId}
              onChange={(e) => setFormData({ ...formData, learnerId: e.target.value })}
              disabled={loadingLearners || preselectedStudentId}
              className={`w-full px-3.5 py-2.5 rounded-xl border text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B] ${
                errors.learnerId ? 'border-red-400 bg-red-50/50' : 'border-stone-200 bg-stone-50'
              }`}
            >
              {loadingLearners ? (
                <option>Loading student roster...</option>
              ) : learners.length === 0 ? (
                <option value="">No students found in classroom</option>
              ) : (
                learners.map((s) => (
                  <option key={s.studentId} value={s.studentId}>
                    {s.name} ({s.learningLevelName || 'Developing'})
                  </option>
                ))
              )}
            </select>
            {errors.learnerId && <p className="text-xs text-red-600 mt-1">{errors.learnerId}</p>}
          </div>

          {/* Target Learning Domain */}
          <div>
            <label htmlFor="select-intervention-domain" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
              Target Learning Domain *
            </label>
            <select
              id="select-intervention-domain"
              value={formData.targetDomain}
              onChange={(e) => setFormData({ ...formData, targetDomain: e.target.value })}
              className="w-full px-3.5 py-2.5 rounded-xl border border-stone-200 bg-stone-50 text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B]"
            >
              {DOMAIN_OPTIONS.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>

          {/* Educational Goal */}
          <div>
            <label htmlFor="input-intervention-goal" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
              Educational Goal *
            </label>
            <input
              id="input-intervention-goal"
              type="text"
              placeholder="e.g. Improve reading comprehension on Grade 2 narrative passages"
              value={formData.goal}
              onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
              className={`w-full px-3.5 py-2.5 rounded-xl border text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B] ${
                errors.goal ? 'border-red-400 bg-red-50/50' : 'border-stone-200 bg-stone-50'
              }`}
            />
            {errors.goal && <p className="text-xs text-red-600 mt-1">{errors.goal}</p>}
          </div>

          {/* Support Activity Description */}
          <div>
            <label htmlFor="textarea-intervention-activity" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
              Planned Support Activity *
            </label>
            <textarea
              id="textarea-intervention-activity"
              rows={2}
              placeholder="e.g. Conduct daily 15-minute guided repeated reading sessions with pre-reading vocabulary preview"
              value={formData.supportActivity}
              onChange={(e) => setFormData({ ...formData, supportActivity: e.target.value })}
              className={`w-full px-3.5 py-2.5 rounded-xl border text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B] ${
                errors.supportActivity ? 'border-red-400 bg-red-50/50' : 'border-stone-200 bg-stone-50'
              }`}
            />
            {errors.supportActivity && <p className="text-xs text-red-600 mt-1">{errors.supportActivity}</p>}
          </div>

          {/* Dates: Start Date and Planned Review Date */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="input-intervention-start-date" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
                Start Date *
              </label>
              <input
                id="input-intervention-start-date"
                type="date"
                value={formData.startDate}
                onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl border border-stone-200 bg-stone-50 text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B]"
              />
              {errors.startDate && <p className="text-xs text-red-600 mt-1">{errors.startDate}</p>}
            </div>

            <div>
              <label htmlFor="input-intervention-review-date" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
                Planned Review Date (Optional)
              </label>
              <input
                id="input-intervention-review-date"
                type="date"
                value={formData.plannedReviewDate}
                onChange={(e) => setFormData({ ...formData, plannedReviewDate: e.target.value })}
                className={`w-full px-3.5 py-2.5 rounded-xl border text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B] ${
                  errors.plannedReviewDate ? 'border-red-400 bg-red-50/50' : 'border-stone-200 bg-stone-50'
                }`}
              />
              {errors.plannedReviewDate && <p className="text-xs text-red-600 mt-1">{errors.plannedReviewDate}</p>}
            </div>
          </div>

          {/* Initial Teacher Notes */}
          <div>
            <label htmlFor="textarea-intervention-notes" className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1">
              Initial Instructional Notes (Optional)
            </label>
            <textarea
              id="textarea-intervention-notes"
              rows={2}
              placeholder="e.g. Student responds well to visual line guides and syllable breakdowns during reading."
              value={formData.initialNotes}
              onChange={(e) => setFormData({ ...formData, initialNotes: e.target.value })}
              className="w-full px-3.5 py-2.5 rounded-xl border border-stone-200 bg-stone-50 text-sm font-medium focus:outline-hidden focus:ring-2 focus:ring-[#1A6B6B]"
            />
          </div>

          {/* Baseline Explanatory Notice */}
          <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-200/80 text-xs text-amber-900 space-y-1">
            <p className="font-bold flex items-center gap-1.5">
              <span>ℹ️</span> Educational Baseline Methodology:
            </p>
            <p className="text-amber-800 leading-relaxed text-[11px]">
              DyslexAid automatically establishes a pre-support baseline by querying relevant historical reading sessions,
              speech-accuracy records, or adaptive activity attempts completed on or prior to the start date.
              If no prior data exists, the baseline is marked as <em>insufficient data</em> until the student completes activities.
            </p>
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-stone-100">
            <button
              id="btn-cancel-create-modal"
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-stone-600 hover:text-stone-900 text-sm font-bold rounded-xl transition-all"
            >
              Cancel
            </button>
            <button
              id="btn-create-support-activity-submit"
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 bg-[#1A6B6B] hover:bg-[#155353] text-white text-sm font-bold rounded-xl shadow-2xs transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {submitting ? 'Establishing Baseline...' : 'Create Support Activity'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
