/**
 * frontend/src/components/insights/DataSufficiencyBanner.jsx
 *
 * Transparent, encouraging communication when historical practice data
 * is insufficient to compute statistical trends.
 * Never manufactures a trend from insufficient data.
 */
import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from '../../i18n/I18nContext'

export default function DataSufficiencyBanner({
  dataSufficiency = 'no_data',
  message = '',
  actionUrl = '/student/reading-coach',
}) {
  const { t } = useTranslation()

  if (dataSufficiency === 'sufficient_data') {
    return null
  }

  const isNoData = dataSufficiency === 'no_data'

  return (
    <div
      role="status"
      className={`rounded-3xl p-5 border flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all ${
        isNoData
          ? 'bg-amber-50/80 border-amber-200 text-amber-900'
          : 'bg-teal-50/80 border-teal-200 text-teal-900'
      }`}
    >
      <div className="flex items-start gap-3.5">
        <span className="text-2xl shrink-0 mt-0.5" aria-hidden="true">
          {isNoData ? '📖' : '🌱'}
        </span>
        <div className="space-y-1">
          <h4 className="text-sm font-extrabold tracking-tight">
            {isNoData
              ? t('insights.noDataTitle', 'No Learning Activity Recorded Yet')
              : t('insights.insufficientDataTitle', 'Building Your Practice History')}
          </h4>
          <p className="text-xs text-stone-600 leading-relaxed max-w-2xl">
            {message ||
              (isNoData
                ? t(
                    'insights.noDataMsg',
                    'Complete a story or reading activity in the Reading Coach to begin building your progress history and insights!'
                  )
                : t(
                    'insights.insufficientDataMsg',
                    'Great start on your reading journey! Complete a few more sessions to reveal clear progress trends.'
                  ))}
          </p>
        </div>
      </div>

      <Link
        to={actionUrl}
        className="shrink-0 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1A6B6B] text-white text-xs font-bold rounded-2xl hover:bg-[#155555] focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] focus:ring-offset-2 transition-all shadow-xs"
      >
        <span>🚀</span>
        <span>{t('insights.startReadingBtn', 'Start Reading Practice')}</span>
      </Link>
    </div>
  )
}
