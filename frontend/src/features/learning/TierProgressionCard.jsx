/**
 * frontend/src/features/learning/TierProgressionCard.jsx — ZPD Progression Card.
 * Displays current difficulty tier (1-5), streak, tasks completed today, and ZPD zone details.
 */
import React from 'react'
import { Card, Badge } from '../../components/ui'

const TIERS = [
  { level: 1, name: 'Foundation', icon: '🌱' },
  { level: 2, name: 'Developing', icon: '🌿' },
  { level: 3, name: 'Progressing', icon: '🌳' },
  { level: 4, name: 'Independent', icon: '🚀' },
  { level: 5, name: 'Advanced', icon: '⭐' },
]

export default function TierProgressionCard({
  learningState,
  tierCalibration,
}) {
  const currentTier =
    learningState?.activeDifficultyTier ||
    learningState?.active_difficulty_tier ||
    1
  const streak =
    learningState?.currentStreak || learningState?.current_streak || 0
  const tasksCompleted =
    learningState?.todayTasksCompleted ||
    learningState?.today_tasks_completed ||
    0
  const tasksAssigned =
    learningState?.todayTasksAssigned ||
    learningState?.today_tasks_assigned ||
    4

  const activeTierMeta =
    TIERS.find((t) => t.level === currentTier) || TIERS[0]

  return (
    <Card className="mb-6 bg-gradient-to-br from-[#F0F8FF] to-[#FFF8F0] border-2 border-[#1A6B6B]/20">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Tier Info & Badge */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-3xl" role="img" aria-label="tier icon">
              {activeTierMeta.icon}
            </span>
            <div>
              <p className="dyslexia-text text-xs text-gray-500 uppercase font-semibold">
                Your Learning Level (ZPD)
              </p>
              <h2 className="dyslexia-text font-bold text-xl text-[#1A2A2A]">
                Level {currentTier} — {activeTierMeta.name}
              </h2>
            </div>
          </div>
          <p className="dyslexia-text text-xs text-gray-600 mt-1 max-w-lg leading-relaxed">
            {tierCalibration?.description ||
              'Content pacing is calibrated to provide optimal challenge without frustration.'}
          </p>
        </div>

        {/* Quick Stats: Streak & Tasks */}
        <div className="flex items-center gap-3">
          <div className="bg-white/80 backdrop-blur rounded-2xl px-4 py-2 border border-amber-200 text-center shadow-sm">
            <p className="text-xl">🔥 {streak}</p>
            <p className="dyslexia-text text-[11px] text-gray-500 font-semibold">
              Day Streak
            </p>
          </div>
          <div className="bg-white/80 backdrop-blur rounded-2xl px-4 py-2 border border-teal-200 text-center shadow-sm">
            <p className="text-xl font-bold text-[#1A6B6B]">
              {tasksCompleted}/{tasksAssigned}
            </p>
            <p className="dyslexia-text text-[11px] text-gray-500 font-semibold">
              Today's Tasks
            </p>
          </div>
        </div>
      </div>

      {/* 5-Step Visual Progression Track */}
      <div className="mt-5 pt-4 border-t border-gray-200/70">
        <p className="dyslexia-text text-xs text-gray-500 mb-2 font-semibold">
          Progress Track:
        </p>
        <div className="grid grid-cols-5 gap-2">
          {TIERS.map((t) => {
            const isCurrent = t.level === currentTier
            const isPast = t.level < currentTier

            return (
              <div
                key={t.level}
                className={`p-2.5 rounded-xl text-center border transition-all ${
                  isCurrent
                    ? 'bg-[#1A6B6B] text-white font-bold border-[#1A6B6B] shadow-md ring-2 ring-[#E8A020]'
                    : isPast
                    ? 'bg-green-50 border-green-200 text-green-800'
                    : 'bg-white/60 border-gray-200 text-gray-400'
                }`}
              >
                <p className="text-base mb-0.5">{t.icon}</p>
                <p className="dyslexia-text text-xs font-semibold truncate">
                  Lvl {t.level}
                </p>
                <p className="dyslexia-text text-[10px] hidden sm:block truncate">
                  {t.name}
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}
