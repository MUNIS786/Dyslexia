/**
 * frontend/src/features/gamification/RewardHistoryList.jsx
 *
 * Transparent, auditable rewards ledger displaying recent points earned.
 */
import React from 'react'

export default function RewardHistoryList({ events = [], loading = false }) {
  const formatDate = (epochSecs) => {
    if (!epochSecs) return ''
    const d = new Date(epochSecs * 1000)
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-stone-200 text-center text-sm text-stone-500">
        Loading rewards history...
      </div>
    )
  }

  if (!events || events.length === 0) {
    return (
      <div
        id="empty-rewards-history"
        className="bg-white rounded-2xl p-8 border border-stone-200 text-center"
      >
        <span className="text-3xl block mb-2" aria-hidden="true">🌱</span>
        <h4 className="text-sm font-bold text-stone-800 mb-1">
          No Reward Events Yet
        </h4>
        <p className="text-xs text-stone-600 max-w-sm mx-auto">
          Complete your first Reading Coach story or adaptive practice activity to earn your first points and badges!
        </p>
      </div>
    )
  }

  return (
    <div
      id="reward-history-ledger"
      className="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-sm"
    >
      <div className="p-4 sm:p-5 border-b border-stone-100 flex items-center justify-between">
        <h4 className="text-sm font-bold text-stone-900 flex items-center gap-2">
          <span>📜</span> Recent Points & Rewards Ledger
        </h4>
        <span className="text-xs text-stone-500 font-semibold">
          {events.length} {events.length === 1 ? 'event' : 'events'} recorded
        </span>
      </div>

      <div className="divide-y divide-stone-100">
        {events.map((ev, idx) => (
          <div
            key={ev.eventId || idx}
            className="p-4 sm:px-5 flex items-center justify-between gap-4 hover:bg-stone-50/60 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 flex items-center justify-center text-base shrink-0 font-bold"
                aria-hidden="true"
              >
                +{ev.points}
              </div>
              <div>
                <p className="text-xs sm:text-sm font-semibold text-stone-900 leading-snug">
                  {ev.description || 'Practice activity completed'}
                </p>
                <span className="text-[11px] text-stone-500">
                  {formatDate(ev.createdAt)}
                </span>
              </div>
            </div>

            <div className="text-right shrink-0">
              <span className="text-xs font-bold text-teal-800 bg-teal-50 px-2.5 py-1 rounded-full border border-teal-200">
                +{ev.points} pts
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
