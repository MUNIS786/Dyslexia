/**
 * frontend/src/features/gamification/CelebrationModal.jsx
 *
 * Calm, encouraging celebration popup when a learner earns new badges or milestones.
 * Strictly avoids sensory overload: no flashing lights, no audio autoplay,
 * respects prefers-reduced-motion preferences.
 */
import React from 'react'

export default function CelebrationModal({
  isOpen,
  onClose,
  pointsAwarded = 0,
  newBadges = [],
  celebrationMessage,
}) {
  if (!isOpen) return null

  return (
    <div
      id="celebration-modal-overlay"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="celebration-title"
    >
      <div
        className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full text-center shadow-xl border border-stone-200 transform transition-all animate-scale-up"
      >
        {/* Celebration Icon */}
        <div
          className="w-20 h-20 mx-auto mb-4 bg-amber-100 rounded-3xl flex items-center justify-center text-4xl shadow-inner border border-amber-200"
          aria-hidden="true"
        >
          {newBadges.length > 0 ? '🏆' : '🌟'}
        </div>

        <h2
          id="celebration-title"
          className="text-2xl font-black text-stone-900 mb-2 leading-tight"
        >
          {newBadges.length > 0 ? 'New Badge Unlocked!' : 'Awesome Practice!'}
        </h2>

        <p className="text-sm sm:text-base text-stone-600 mb-6 font-medium">
          {celebrationMessage || `You earned ${pointsAwarded} learning points! Keep up the wonderful work.`}
        </p>

        {/* Display New Badges if any */}
        {newBadges && newBadges.length > 0 && (
          <div className="space-y-3 mb-6">
            {newBadges.map((badge) => (
              <div
                key={badge.badgeId}
                className="bg-amber-50/80 rounded-2xl p-4 border border-amber-200 flex items-center gap-3 text-left"
              >
                <span className="text-3xl shrink-0" aria-hidden="true">
                  {badge.icon}
                </span>
                <div>
                  <h4 className="text-sm font-bold text-amber-950">
                    {badge.title}
                  </h4>
                  <p className="text-xs text-amber-900/80 font-medium">
                    {badge.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          id="btn-close-celebration"
          onClick={onClose}
          className="w-full py-3.5 px-6 rounded-2xl bg-teal-800 hover:bg-teal-900 text-white font-bold text-sm shadow-sm transition-all focus:ring-2 focus:ring-teal-600 focus:outline-none"
        >
          Continue Learning
        </button>
      </div>
    </div>
  )
}
