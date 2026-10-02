/**
 * frontend/src/features/gamification/MilestoneTracker.jsx
 *
 * Visual, child-friendly milestone progress tracker.
 * Highlights upcoming reachable targets with encouraging progress bars.
 */
import React from 'react'

export default function MilestoneTracker({ milestones = [] }) {
  if (!milestones || milestones.length === 0) {
    return null
  }

  return (
    <div id="milestones-tracker-section" className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-stone-900 flex items-center gap-2">
          <span>🎯</span> Next Practice Goals & Milestones
        </h3>
        <span className="text-xs font-semibold text-stone-500">
          Personal Milestones
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {milestones.map((m) => (
          <div
            key={m.milestoneId}
            id={`milestone-card-${m.milestoneId}`}
            className="bg-white rounded-2xl p-5 border border-stone-200 shadow-sm flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center gap-3 mb-2.5">
                <span className="text-2xl" aria-hidden="true">{m.icon}</span>
                <h4 className="text-sm font-bold text-stone-900">
                  {m.title}
                </h4>
              </div>
              <p className="text-xs text-stone-600 mb-3 leading-relaxed">
                {m.description}
              </p>
            </div>

            <div>
              <div className="flex justify-between items-center text-xs font-semibold text-stone-700 mb-1.5">
                <span>{m.completed ? 'Goal Achieved!' : 'Progress'}</span>
                <span>{m.current} / {m.target}</span>
              </div>
              <div
                className="w-full h-3 bg-stone-100 rounded-full overflow-hidden border border-stone-200"
                role="progressbar"
                aria-valuenow={m.current}
                aria-valuemin={0}
                aria-valuemax={m.target}
                aria-label={`${m.title} progress`}
              >
                <div
                  className={`h-full rounded-full transition-all duration-300 ${
                    m.completed ? 'bg-emerald-600' : 'bg-teal-600'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, m.progressPercent))}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
