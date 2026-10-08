/**
 * frontend/src/components/insights/PeriodSelector.jsx
 *
 * Accessible reporting period selector (7d, 30d, 90d).
 * Supports keyboard navigation, aria-pressed, and multi-language translations.
 */
import React from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function PeriodSelector({ selectedPeriod = '30d', onSelectPeriod, disabled = false }) {
  const { t } = useTranslation()

  const periods = [
    { id: '7d', label: t('insights.period7d', 'Last 7 Days'), short: '7D' },
    { id: '30d', label: t('insights.period30d', 'Last 30 Days'), short: '30D' },
    { id: '90d', label: t('insights.period90d', 'Last 90 Days'), short: '90D' },
  ]

  return (
    <nav
      aria-label={t('insights.selectPeriod', 'Reporting Period')}
      className="inline-flex p-1 bg-stone-100 rounded-2xl border border-stone-200"
    >
      {periods.map((p) => {
        const isSelected = selectedPeriod === p.id
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onSelectPeriod && onSelectPeriod(p.id)}
            disabled={disabled}
            aria-pressed={isSelected}
            className={`px-3 py-1.5 sm:px-4 sm:py-2 rounded-xl text-xs sm:text-sm font-bold transition-all focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] focus:ring-offset-1 disabled:opacity-50 ${
              isSelected
                ? 'bg-[#1A6B6B] text-white shadow-xs'
                : 'text-stone-600 hover:text-stone-900 hover:bg-stone-200/60'
            }`}
          >
            <span className="hidden sm:inline">{p.label}</span>
            <span className="sm:hidden">{p.short}</span>
          </button>
        )
      })}
    </nav>
  )
}
