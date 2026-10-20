import React, { useEffect } from 'react'

const ACTION_BADGES = {
  CREATED: 'bg-blue-100 text-blue-800',
  UPDATED: 'bg-slate-100 text-slate-800',
  SUBMITTED: 'bg-amber-100 text-amber-800',
  APPROVED: 'bg-emerald-100 text-emerald-800',
  CHANGES_REQUESTED: 'bg-orange-100 text-orange-800',
  REJECTED: 'bg-rose-100 text-rose-800',
  PUBLISHED: 'bg-indigo-100 text-indigo-800',
  ARCHIVED: 'bg-slate-100 text-slate-800',
  REVISED: 'bg-purple-100 text-purple-800',
}

export default function ContentVersionHistoryModal({
  historyData,
  loading = false,
  onClose,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!historyData && !loading) return null

  const { contentId, currentVersion = 1, history = [] } = historyData || {}

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="history-modal-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
    >
      <div className="bg-white rounded-3xl shadow-xl border border-slate-200 max-w-2xl w-full max-h-[85vh] max-w-[calc(100vw-2rem)] flex flex-col overflow-hidden animate-fadeIn">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                Version {currentVersion}
              </span>
              <span className="text-xs text-slate-400 font-mono">{contentId}</span>
            </div>
            <h3 id="history-modal-title" className="text-base font-bold text-slate-900 mt-0.5">Audit & Lifecycle History</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 font-bold p-1 text-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Timeline Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading ? (
            <div className="py-12 text-center text-slate-400">Loading audit history...</div>
          ) : history.length === 0 ? (
            <div className="py-12 text-center text-slate-400 italic">No history events recorded yet.</div>
          ) : (
            <div className="relative border-l-2 border-slate-200 ml-3 space-y-6">
              {history.map((event, idx) => {
                const badge = ACTION_BADGES[event.action] || 'bg-slate-100 text-slate-700'
                const dt = event.timestamp ? new Date(event.timestamp * 1000).toLocaleString() : 'N/A'
                return (
                  <div key={event.id || idx} className="relative pl-6">
                    {/* Timeline dot */}
                    <div className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-indigo-600 border-2 border-white ring-2 ring-indigo-200" />

                    <div className="bg-gray-50/80 border border-gray-200 rounded-xl p-3.5 space-y-1.5">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${badge}`}>
                          {event.action}
                        </span>
                        <span className="text-[11px] text-gray-400 font-medium">{dt}</span>
                      </div>

                      <div className="text-xs text-gray-700">
                        <span className="font-semibold text-gray-900">{event.actorName || 'Educator'}</span>
                        <span className="text-gray-400 mx-1">({event.actorRole})</span>
                        {event.fromState && event.toState && (
                          <span className="text-gray-500">
                            transitioned state from <strong>{event.fromState}</strong> to <strong>{event.toState}</strong>
                          </span>
                        )}
                      </div>

                      {event.feedback && (
                        <div className="mt-1 bg-white p-2.5 rounded-lg border border-gray-100 text-xs text-gray-600 italic">
                          "{event.feedback}"
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-right">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-bold rounded-xl bg-white border border-gray-300 text-gray-700 hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
