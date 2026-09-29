/**
 * frontend/src/features/learner/LearningLevelCard.jsx
 * Displays student's educational learning level with explainable metrics.
 */
import React from 'react'

const LEVEL_CONFIG = {
  1: {
    name: 'Foundation',
    badge: '🌱 Step 1: Foundation',
    color: 'from-amber-500 to-orange-500',
    lightBg: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-900',
  },
  2: {
    name: 'Developing',
    badge: '🌿 Step 2: Developing',
    color: 'from-blue-500 to-indigo-500',
    lightBg: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-900',
  },
  3: {
    name: 'Progressing',
    badge: '🚀 Step 3: Progressing',
    color: 'from-teal-500 to-emerald-500',
    lightBg: 'bg-teal-50',
    borderColor: 'border-teal-200',
    textColor: 'text-teal-900',
  },
  4: {
    name: 'Independent',
    badge: '⭐ Step 4: Independent',
    color: 'from-emerald-600 to-teal-600',
    lightBg: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    textColor: 'text-emerald-900',
  },
  5: {
    name: 'Advanced',
    badge: '🏆 Step 5: Advanced',
    color: 'from-purple-600 to-indigo-600',
    lightBg: 'bg-purple-50',
    borderColor: 'border-purple-200',
    textColor: 'text-purple-900',
  },
}

export default function LearningLevelCard({ learningLevel }) {
  const levelNum = Math.min(5, Math.max(1, Number(learningLevel?.level || 1)))
  const config = LEVEL_CONFIG[levelNum] || LEVEL_CONFIG[1]
  const levelName = learningLevel?.name || config.name
  const levelDesc = learningLevel?.description || 'Growing your reading superpowers step by step.'
  const inputs = learningLevel?.inputs || {}

  const steps = [
    { num: 1, label: 'Foundation' },
    { num: 2, label: 'Developing' },
    { num: 3, label: 'Progressing' },
    { num: 4, label: 'Independent' },
    { num: 5, label: 'Advanced' },
  ]

  return (
    <div
      className={`rounded-3xl border ${config.borderColor} ${config.lightBg} p-6 sm:p-7 shadow-sm transition-all duration-300 relative overflow-hidden`}
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-gray-500 block mb-1">
            YOUR LEARNING LEVEL
          </span>
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${config.color} text-white flex items-center justify-center text-xl font-black shadow-md`}>
              {levelNum}
            </div>
            <div>
              <h2 className={`text-xl sm:text-2xl font-bold ${config.textColor} dyslexia-text`}>
                Level {levelNum} — {levelName}
              </h2>
              <p className="text-xs text-gray-500">
                Educational Learning Stage
              </p>
            </div>
          </div>
        </div>

        <span className="self-start md:self-center px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-gray-800 shadow-sm border border-gray-200/80">
          {config.badge}
        </span>
      </div>

      <p className="text-sm sm:text-base text-gray-700 leading-relaxed dyslexia-text mb-6">
        {levelDesc}
      </p>

      {/* 5-Step Visual Progression Track */}
      <div className="space-y-2 mb-4">
        <div className="flex justify-between items-center text-xs font-semibold text-gray-600 px-1">
          <span>Starting Steps</span>
          <span>Reading Milestone Path</span>
          <span>Advanced Independence</span>
        </div>

        <div className="grid grid-cols-5 gap-2" role="progressbar" aria-valuenow={levelNum} aria-valuemin="1" aria-valuemax="5" aria-label={`Learning Level ${levelNum} of 5`}>
          {steps.map((step) => {
            const isCompleted = step.num <= levelNum
            const isCurrent = step.num === levelNum
            return (
              <div key={step.num} className="flex flex-col items-center gap-1.5">
                <div
                  className={`w-full h-3 rounded-full transition-all duration-500 ${
                    isCurrent
                      ? `bg-gradient-to-r ${config.color} ring-2 ring-offset-1 ring-teal-500 shadow-sm`
                      : isCompleted
                      ? 'bg-teal-500'
                      : 'bg-gray-200'
                  }`}
                />
                <span
                  className={`text-[11px] font-medium hidden sm:inline ${
                    isCurrent ? 'font-bold text-gray-900' : 'text-gray-500'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Educational Note */}
      {inputs.composite_score != null && (
        <div className="pt-3 border-t border-gray-200/70 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
          <span>
            Based on {inputs.domains_evaluated || 10} evaluated learning areas (Score: {Math.round(inputs.composite_score)}/100)
          </span>
          <span className="italic">
            Educational classification only &bull; Non-diagnostic
          </span>
        </div>
      )}
    </div>
  )
}
