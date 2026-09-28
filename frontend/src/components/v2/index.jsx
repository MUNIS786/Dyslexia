/**
 * frontend/src/components/v2/index.jsx — Reusable V2 UI components.
 * Fully accessible, lightweight, and dependency-free.
 */
import React from 'react'

export function V2FeatureBadge({ label = 'V2 Intelligence' }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
      {label}
    </span>
  )
}

export function LearnerDisclaimer() {
  return (
    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 leading-relaxed">
      <strong>Educational Indicator:</strong> This profile reflects educational screening observations and learning preferences to customize reading accommodations. It does not constitute a clinical or medical diagnosis.
    </div>
  )
}

export function DomainBarChart({ domainScores = {} }) {
  const domainLabels = {
    phonological_awareness: 'Phonological Awareness',
    phonological_memory: 'Phonological Memory',
    rapid_naming: 'Rapid Naming (RAN)',
    letter_reversal: 'Letter Reversal',
    reading_fluency: 'Reading Fluency',
    orthographic_spelling: 'Orthographic / Spelling',
    reading_comprehension: 'Reading Comprehension',
    motor_writing: 'Motor / Writing',
    visual_processing: 'Visual Processing',
    processing_speed: 'Processing Speed',
  }

  const entries = Object.entries(domainScores).filter(([key]) => domainLabels[key])

  if (entries.length === 0) {
    return <p className="text-sm text-gray-500 italic">No domain telemetry available yet.</p>
  }

  return (
    <div className="space-y-3">
      {entries.map(([key, score]) => {
        const val = Math.min(100, Math.max(0, Math.round(score || 0)))
        const barColor =
          val > 70 ? 'bg-emerald-500' : val > 40 ? 'bg-blue-500' : 'bg-amber-500'

        return (
          <div key={key} className="space-y-1">
            <div className="flex justify-between text-xs font-medium text-gray-700">
              <span>{domainLabels[key] || key}</span>
              <span className="font-semibold text-gray-900">{val}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                style={{ width: `${val}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function LearnerStrengthCard({ strengths = [], focusAreas = [] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
        <h4 className="text-sm font-bold text-emerald-900 mb-2 flex items-center gap-1.5">
          <span>✨</span> Identified Strengths
        </h4>
        {strengths.length > 0 ? (
          <ul className="list-disc list-inside space-y-1 text-xs text-emerald-800">
            {strengths.map((s, idx) => (
              <li key={idx}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-emerald-700 italic">Strengths will populate after screening.</p>
        )}
      </div>

      <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <h4 className="text-sm font-bold text-blue-900 mb-2 flex items-center gap-1.5">
          <span>🎯</span> Priority Focus Areas
        </h4>
        {focusAreas.length > 0 ? (
          <ul className="list-disc list-inside space-y-1 text-xs text-blue-800">
            {focusAreas.map((f, idx) => (
              <li key={idx}>{f}</li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-blue-700 italic">Focus areas will populate after screening.</p>
        )}
      </div>
    </div>
  )
}
