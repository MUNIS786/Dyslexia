import React from 'react'

export default function ContentReviewQueue({
  items = [],
  loading = false,
  onReviewItem,
  onRefresh,
}) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-10 text-center border border-gray-200">
        <div className="w-8 h-8 border-4 border-[#1A6B6B] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-500 font-medium">Loading review queue...</p>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-12 text-center border border-gray-200 space-y-3">
        <div className="w-14 h-14 bg-teal-50 text-[#1A6B6B] rounded-2xl flex items-center justify-center text-2xl mx-auto font-bold">
          ✓
        </div>
        <h4 className="text-base font-bold text-gray-900">Review Queue is Clear!</h4>
        <p className="text-xs text-gray-500 max-w-md mx-auto">
          There are no content passages currently waiting for peer evaluation. When fellow educators submit drafts, they will appear here.
        </p>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="text-xs font-bold text-[#1A6B6B] hover:underline pt-2"
          >
            ↻ Refresh Queue
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider">
          Items Awaiting Review ({items.length})
        </h3>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="text-xs font-bold text-gray-600 hover:text-gray-900"
          >
            ↻ Refresh
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map((item) => {
          const score = item.validationResult?.completenessScore ?? 80
          return (
            <div
              key={item.contentId}
              className="bg-white rounded-2xl border border-gray-200 hover:border-teal-300 p-5 shadow-sm space-y-3 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-800 border border-teal-200">
                      Tier {item.difficulty}
                    </span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 uppercase">
                      {item.language}
                    </span>
                  </div>
                  <span className="text-[11px] text-gray-400">v{item.version}</span>
                </div>

                <h4 className="font-bold text-gray-900 text-base leading-snug">{item.title}</h4>
                <p className="text-xs text-gray-500 line-clamp-2 mt-1 leading-relaxed">
                  {item.text}
                </p>

                <div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-500 mt-3 pt-3 border-t border-gray-100">
                  <span>Author: <strong>{item.authorName || 'Educator'}</strong></span>
                  <span>Words: <strong>{item.wordCount}</strong></span>
                  <span>
                    Quality:{' '}
                    <strong className={score >= 80 ? 'text-emerald-600' : 'text-amber-600'}>
                      {score}%
                    </strong>
                  </span>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between">
                <span className="text-[11px] text-gray-400">
                  {item.updatedAt ? new Date(item.updatedAt * 1000).toLocaleDateString() : 'Recent'}
                </span>
                <button
                  type="button"
                  onClick={() => onReviewItem(item)}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-[#1A6B6B] text-white hover:bg-[#145252] transition-colors shadow-sm"
                >
                  Evaluate & Review →
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
