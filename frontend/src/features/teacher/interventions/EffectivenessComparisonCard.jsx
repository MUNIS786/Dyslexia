/**
 * frontend/src/features/teacher/interventions/EffectivenessComparisonCard.jsx
 *
 * Displays a single metric before-and-after comparison with:
 * - Baseline value, observation count, and data source
 * - Follow-up value, observation count, and data source
 * - Absolute and relative changes
 * - Material change threshold badge (e.g. improved_on_measure, no_material_change)
 * - Explicit neutral, non-clinical interpretation
 */
import React from 'react'

export default function EffectivenessComparisonCard({ comparison }) {
  if (!comparison) return null

  const {
    metricName,
    metricDisplayName,
    targetDomain,
    unit,
    scale,
    direction,
    baselineValue,
    baselineObservations,
    baselinePeriod,
    baselineStatus,
    followUpValue,
    followUpObservations,
    followUpPeriod,
    followUpStatus,
    absoluteChange,
    relativeChangePercent,
    status,
    thresholdUsed,
    interpretation,
  } = comparison

  // Status badge config
  const statusConfig = {
    improved_on_measure: {
      bg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      icon: '📈',
      label: 'Observed Progress',
    },
    declined_on_measure: {
      bg: 'bg-amber-50 text-amber-800 border-amber-200',
      icon: '📉',
      label: 'Observed Decline',
    },
    no_material_change: {
      bg: 'bg-sky-50 text-sky-800 border-sky-200',
      icon: '⚖️',
      label: 'Stable / No Material Change',
    },
    insufficient_data: {
      bg: 'bg-stone-100 text-stone-700 border-stone-300',
      icon: '⏳',
      label: 'Insufficient Data',
    },
    not_comparable: {
      bg: 'bg-purple-50 text-purple-800 border-purple-200',
      icon: '⚠️',
      label: 'Not Comparable',
    },
  }[status] || {
    bg: 'bg-stone-100 text-stone-700 border-stone-300',
    icon: '📊',
    label: status,
  }

  const sign = absoluteChange !== null && absoluteChange > 0 ? '+' : ''

  return (
    <div className="bg-white rounded-2xl border border-stone-200 p-5 shadow-2xs space-y-4">
      {/* Metric Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-100 pb-3">
        <div>
          <h3 className="font-bold text-stone-900 text-base">{metricDisplayName}</h3>
          <p className="text-xs text-stone-500">
            Target Domain: <span className="font-medium capitalize">{targetDomain.replace('_', ' ')}</span> • Scale: {scale}
          </p>
        </div>
        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${statusConfig.bg}`}>
          <span>{statusConfig.icon}</span>
          <span>{statusConfig.label}</span>
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Baseline Card */}
        <div className="p-3 bg-stone-50 rounded-xl border border-stone-100">
          <p className="text-xs text-stone-500 font-semibold uppercase tracking-wider mb-1">Pre-Support Baseline</p>
          {baselineValue !== null && baselineStatus === 'sufficient' ? (
            <div>
              <p className="text-2xl font-black text-stone-900">
                {baselineValue} <span className="text-sm font-normal text-stone-500">{unit}</span>
              </p>
              <p className="text-xs text-stone-500 mt-1">
                {baselineObservations} session(s) recorded
              </p>
            </div>
          ) : (
            <div className="text-xs text-stone-500 italic py-1">
              <span className="font-medium text-amber-700">No baseline data recorded.</span>
              <p className="text-[11px] text-stone-400 mt-0.5">Missing data is not treated as zero.</p>
            </div>
          )}
        </div>

        {/* Follow-Up Card */}
        <div className="p-3 bg-stone-50 rounded-xl border border-stone-100">
          <p className="text-xs text-stone-500 font-semibold uppercase tracking-wider mb-1">Follow-Up Practice</p>
          {followUpValue !== null && followUpStatus === 'sufficient' ? (
            <div>
              <p className="text-2xl font-black text-stone-900">
                {followUpValue} <span className="text-sm font-normal text-stone-500">{unit}</span>
              </p>
              <p className="text-xs text-stone-500 mt-1">
                {followUpObservations} session(s) recorded
              </p>
            </div>
          ) : (
            <div className="text-xs text-stone-500 italic py-1">
              <span className="font-medium text-stone-600">Pending student sessions.</span>
              <p className="text-[11px] text-stone-400 mt-0.5">Awaiting practice activity completion.</p>
            </div>
          )}
        </div>

        {/* Observed Change Card */}
        <div className="p-3 bg-stone-50 rounded-xl border border-stone-100">
          <p className="text-xs text-stone-500 font-semibold uppercase tracking-wider mb-1">Observed Change</p>
          {absoluteChange !== null ? (
            <div>
              <div className="flex items-baseline gap-2">
                <p className={`text-2xl font-black ${
                  absoluteChange > 0 ? 'text-emerald-700' : absoluteChange < 0 ? 'text-amber-700' : 'text-stone-700'
                }`}>
                  {sign}{absoluteChange} <span className="text-sm font-normal text-stone-500">{unit}</span>
                </p>
                {relativeChangePercent !== null && (
                  <span className="text-xs font-bold text-stone-600">
                    ({sign}{relativeChangePercent}%)
                  </span>
                )}
              </div>
              <p className="text-[11px] text-stone-400 mt-1">
                Threshold: ±{thresholdUsed} {unit}
              </p>
            </div>
          ) : (
            <div className="text-xs text-stone-400 italic py-1">
              Change undefined (requires both baseline & follow-up).
            </div>
          )}
        </div>
      </div>

      {/* Neutral Interpretation Banner */}
      <div className="p-3 bg-teal-50/50 rounded-xl border border-teal-100/60 text-xs text-stone-700 space-y-1">
        <p className="font-semibold text-teal-900 flex items-center gap-1.5">
          <span>🔍</span> Educational Observation Note:
        </p>
        <p className="leading-relaxed text-stone-600">{interpretation}</p>
      </div>
    </div>
  )
}
