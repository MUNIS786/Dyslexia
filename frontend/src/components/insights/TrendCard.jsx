/**
 * frontend/src/components/insights/TrendCard.jsx
 *
 * Accessible metric trend card.
 * Does not depend solely on color (uses explicit text labels, icons, and ARIA attributes).
 */
import React from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function TrendCard({
  title,
  subtitle,
  icon = '📈',
  trend,
  currentValue,
  unit = '',
  loading = false,
}) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <div className="bg-white rounded-3xl p-5 border border-stone-200 shadow-2xs animate-pulse space-y-3">
        <div className="h-4 bg-stone-200 rounded w-1/2" />
        <div className="h-8 bg-stone-200 rounded w-1/3" />
        <div className="h-4 bg-stone-100 rounded w-3/4" />
      </div>
    )
  }

  const direction = trend?.direction || 'insufficient_data'

  // Visual cues with text, icon, and colors
  const trendConfig = {
    improving: {
      symbol: '↑',
      iconText: 'Positive Trend',
      badgeClass: 'bg-emerald-100 text-emerald-900 border-emerald-300',
      borderClass: 'border-emerald-200',
      indicatorLabel: t('insights.trendImproving', 'Improving'),
    },
    stable: {
      symbol: '→',
      iconText: 'Steady Trend',
      badgeClass: 'bg-blue-100 text-blue-900 border-blue-300',
      borderClass: 'border-blue-200',
      indicatorLabel: t('insights.trendStable', 'Steady'),
    },
    needs_attention: {
      symbol: '⚠️',
      iconText: 'Needs Extra Practice',
      badgeClass: 'bg-amber-100 text-amber-900 border-amber-300',
      borderClass: 'border-amber-200',
      indicatorLabel: t('insights.trendNeedsAttention', 'Needs Practice'),
    },
    insufficient_data: {
      symbol: 'ℹ️',
      iconText: 'Building History',
      badgeClass: 'bg-stone-100 text-stone-800 border-stone-300',
      borderClass: 'border-stone-200',
      indicatorLabel: t('insights.trendInsufficient', 'Building Habit'),
    },
  }[direction] || {
    symbol: '•',
    iconText: 'No Data',
    badgeClass: 'bg-stone-100 text-stone-700 border-stone-200',
    borderClass: 'border-stone-200',
    indicatorLabel: t('insights.trendInsufficient', 'Building Habit'),
  }

  const displayVal =
    currentValue !== undefined && currentValue !== null
      ? `${currentValue}${unit}`
      : trend?.currentValue !== undefined && trend?.currentValue !== null
      ? `${trend.currentValue}${unit}`
      : '—'

  return (
    <div
      className={`bg-white rounded-3xl p-5 border ${trendConfig.borderClass} shadow-2xs flex flex-col justify-between transition-all hover:shadow-xs`}
    >
      <div>
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-bold text-stone-500 uppercase tracking-wider flex items-center gap-1.5">
            <span aria-hidden="true">{icon}</span>
            {title}
          </span>
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-extrabold border ${trendConfig.badgeClass}`}
            role="status"
            aria-label={`${title}: ${trendConfig.indicatorLabel}`}
          >
            <span aria-hidden="true" className="font-bold">{trendConfig.symbol}</span>
            <span>{trendConfig.indicatorLabel}</span>
          </span>
        </div>

        {/* Current Metric Display */}
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-black text-stone-900 tracking-tight">
            {displayVal}
          </span>
          {trend?.change !== undefined && trend?.change !== null && (
            <span className="text-xs font-semibold text-stone-500">
              ({trend.change > 0 ? `+${trend.change}` : trend.change}{unit} vs prior)
            </span>
          )}
        </div>

        {/* Explanatory Message */}
        {trend?.message && (
          <p className="mt-2 text-xs text-stone-600 leading-relaxed">
            {trend.message}
          </p>
        )}
      </div>

      {subtitle && (
        <div className="mt-3 pt-3 border-t border-stone-100 text-[11px] text-stone-400">
          {subtitle}
        </div>
      )}
    </div>
  )
}
