/**
 * frontend/src/features/learner/DomainScoreChart.jsx
 * Interactive, accessible learning map showing normalized educational scores.
 */
import React, { useState } from 'react'

const DOMAIN_INFO = {
  phonological_awareness: {
    friendly: 'Sound & Word Practice',
    technical: 'Phonological Awareness',
    icon: '🔊',
  },
  phonological_memory: {
    friendly: 'Memory for Sounds',
    technical: 'Phonological Memory',
    icon: '🎶',
  },
  rapid_naming: {
    friendly: 'Quick Naming',
    technical: 'Rapid Automatized Naming',
    icon: '⚡',
  },
  reading_fluency: {
    friendly: 'Smooth Reading Flow',
    technical: 'Reading Fluency',
    icon: '📖',
  },
  orthographic_spelling: {
    friendly: 'Spelling & Word Patterns',
    technical: 'Orthographic / Spelling',
    icon: '✏️',
  },
  reading_comprehension: {
    friendly: 'Story & Text Understanding',
    technical: 'Reading Comprehension',
    icon: '💡',
  },
  visual_processing: {
    friendly: 'Visual Pattern Finding',
    technical: 'Visual Processing',
    icon: '👀',
  },
  visual_attention: {
    friendly: 'Focus on Letters & Words',
    technical: 'Visual Attention',
    icon: '🎯',
  },
  language_processing: {
    friendly: 'Word Meaning & Sentences',
    technical: 'Language Processing',
    icon: '💬',
  },
  working_memory: {
    friendly: 'Thinking Memory',
    technical: 'Working Memory',
    icon: '🧠',
  },
  letter_reversal: {
    friendly: 'Letter Direction & Shape',
    technical: 'Letter Orientation',
    icon: '🔄',
  },
  processing_speed: {
    friendly: 'Pacing & Speed',
    technical: 'Processing Speed',
    icon: '⏱️',
  },
}

function getScoreStyling(score) {
  if (score >= 90) {
    return {
      label: 'Strong',
      barColor: 'bg-emerald-500',
      textColor: 'text-emerald-800',
      badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    }
  } else if (score >= 75) {
    return {
      label: 'Strength',
      barColor: 'bg-teal-500',
      textColor: 'text-teal-800',
      badgeBg: 'bg-teal-100 text-teal-800 border-teal-300',
    }
  } else if (score >= 60) {
    return {
      label: 'Progressing',
      barColor: 'bg-blue-500',
      textColor: 'text-blue-800',
      badgeBg: 'bg-blue-100 text-blue-800 border-blue-300',
    }
  } else if (score >= 40) {
    return {
      label: 'Developing',
      barColor: 'bg-amber-500',
      textColor: 'text-amber-800',
      badgeBg: 'bg-amber-100 text-amber-800 border-amber-300',
    }
  } else {
    return {
      label: 'Needs Practice',
      barColor: 'bg-rose-500',
      textColor: 'text-rose-800',
      badgeBg: 'bg-rose-100 text-rose-800 border-rose-300',
    }
  }
}

export default function DomainScoreChart({ domainScores = {}, domainInterpretations = {} }) {
  const [showTechnical, setShowTechnical] = useState(false)

  const entries = Object.entries(domainScores).filter(([k]) => DOMAIN_INFO[k])

  if (entries.length === 0) {
    return (
      <div className="bg-white rounded-3xl border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2 dyslexia-text">
          <span>🗺️</span> YOUR LEARNING MAP
        </h3>
        <p className="text-sm text-gray-500 italic">
          No domain scores recorded yet. Complete your learning check to generate your map.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-7 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2 dyslexia-text">
            <span>🗺️</span> YOUR LEARNING MAP
          </h3>
          <p className="text-xs text-gray-500">
            A complete view of all 12 educational learning areas on a 0–100 scale
          </p>
        </div>

        {/* View Toggle */}
        <button
          onClick={() => setShowTechnical(!showTechnical)}
          aria-pressed={showTechnical}
          className="self-start sm:self-center px-3 py-1.5 rounded-xl text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors border border-gray-200"
        >
          {showTechnical ? 'Show Friendly Names' : 'Show Technical Names'}
        </button>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 p-3 bg-gray-50 rounded-2xl mb-6 text-xs text-gray-600">
        <span className="font-semibold text-gray-700">Guide:</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span>Strong (90+)</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-teal-500" />
          <span>Strength (75–89)</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
          <span>Progressing (60–74)</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span>Developing (40–59)</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <span>Needs Practice (0–39)</span>
        </span>
      </div>

      {/* Bars Grid */}
      <div className="space-y-4">
        {entries.map(([key, score]) => {
          const val = Math.min(100, Math.max(0, Math.round(score || 0)))
          const styling = getScoreStyling(val)
          const info = DOMAIN_INFO[key]
          const displayName = showTechnical ? info.technical : info.friendly

          return (
            <div key={key} className="space-y-1.5">
              <div className="flex items-center justify-between gap-2 text-xs sm:text-sm">
                <div className="flex items-center gap-2 truncate">
                  <span className="text-base select-none" aria-hidden="true">{info.icon}</span>
                  <span className="font-semibold text-gray-900 truncate dyslexia-text">
                    {displayName}
                  </span>
                  {showTechnical && (
                    <span className="text-[11px] text-gray-400 hidden md:inline">
                      ({info.friendly})
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${styling.badgeBg}`}
                  >
                    {styling.label}
                  </span>
                  <span className="font-extrabold text-gray-900 w-10 text-right">
                    {val}%
                  </span>
                </div>
              </div>

              <div
                className="w-full bg-gray-100 rounded-full h-3 overflow-hidden p-0.5 shadow-inner"
                role="progressbar"
                aria-valuenow={val}
                aria-valuemin="0"
                aria-valuemax="100"
                aria-label={`${displayName}: ${val}% (${styling.label})`}
              >
                <div
                  className={`h-full rounded-full transition-all duration-700 ${styling.barColor}`}
                  style={{ width: `${val}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
