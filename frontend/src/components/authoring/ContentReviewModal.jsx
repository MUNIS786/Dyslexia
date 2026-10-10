import React, { useState } from 'react'
import ContentPreview from './ContentPreview'
import ContentValidationPanel from './ContentValidationPanel'

export default function ContentReviewModal({
  item,
  currentUserId,
  onClose,
  onSubmitDecision,
  isSubmitting = false,
}) {
  const [feedback, setFeedback] = useState('')
  const [activeTab, setActiveTab] = useState('preview') // 'preview' | 'validation'

  if (!item) return null

  const isSelf = currentUserId && item.authorId === currentUserId

  const handleApprove = () => {
    onSubmitDecision({
      decision: 'APPROVE',
      feedback: feedback.trim() || 'Content approved after review.',
    })
  }

  const handleRequestChanges = () => {
    if (!feedback.trim()) {
      alert('Please provide actionable feedback explaining the changes needed.')
      return
    }
    onSubmitDecision({
      decision: 'REQUEST_CHANGES',
      feedback: feedback.trim(),
    })
  }

  const handleReject = () => {
    if (!feedback.trim()) {
      alert('Please provide feedback explaining the reason for rejection.')
      return
    }
    onSubmitDecision({
      decision: 'REJECT',
      feedback: feedback.trim(),
    })
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-xl border border-gray-200 max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-fadeIn">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/80">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-800">
                In Review
              </span>
              <span className="text-xs text-gray-500">Author: {item.authorName || 'Teacher'}</span>
            </div>
            <h3 className="text-lg font-bold text-gray-900 mt-1">{item.title}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 font-bold p-1 text-lg"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Tab switcher */}
        <div className="px-6 border-b border-gray-100 flex gap-4 text-xs font-bold text-gray-500 bg-white">
          <button
            type="button"
            onClick={() => setActiveTab('preview')}
            className={`py-3 border-b-2 transition-colors ${
              activeTab === 'preview'
                ? 'border-[#1A6B6B] text-[#1A6B6B]'
                : 'border-transparent hover:text-gray-700'
            }`}
          >
            Passage Preview & Questions
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('validation')}
            className={`py-3 border-b-2 transition-colors ${
              activeTab === 'validation'
                ? 'border-[#1A6B6B] text-[#1A6B6B]'
                : 'border-transparent hover:text-gray-700'
            }`}
          >
            Quality & Diagnostics Report
          </button>
        </div>

        {/* Body scroll area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isSelf && (
            <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-xs text-amber-800 space-y-1">
              <p className="font-bold">⚠️ Separation of Duties Rule</p>
              <p>
                You authored this content. DyslexAid policy requires an independent peer educator or administrator to evaluate and approve drafts. You cannot approve your own submission.
              </p>
            </div>
          )}

          {activeTab === 'preview' ? (
            <ContentPreview content={item} />
          ) : (
            <ContentValidationPanel validationResult={item.validationResult} />
          )}

          {/* Feedback Textarea */}
          <div className="space-y-1.5 pt-4 border-t border-gray-100">
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
              Reviewer Notes & Actionable Feedback
            </label>
            <textarea
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Provide constructive, supportive feedback for the author. (Required when requesting changes or rejecting)..."
              className="w-full p-3 text-xs rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-gray-900 font-medium"
            />
          </div>
        </div>

        {/* Footer actions */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold rounded-xl text-gray-600 hover:text-gray-900 border border-gray-200 bg-white"
          >
            Cancel
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-bold rounded-xl bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition-colors disabled:opacity-50"
            >
              Reject
            </button>

            <button
              type="button"
              onClick={handleRequestChanges}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-bold rounded-xl bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition-colors disabled:opacity-50"
            >
              Request Changes
            </button>

            <button
              type="button"
              onClick={handleApprove}
              disabled={isSubmitting || isSelf}
              className={`px-5 py-2 text-xs font-bold rounded-xl transition-colors shadow-sm ${
                isSelf
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50'
              }`}
            >
              {isSubmitting ? 'Approving...' : '✓ Approve Content'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
