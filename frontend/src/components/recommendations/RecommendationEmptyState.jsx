/**
 * frontend/src/components/recommendations/RecommendationEmptyState.jsx
 *
 * Warm, encouraging empty state for learners with no or insufficient data.
 * Explains that recommendations will personalize as they practice, and provides
 * a direct CTA to start reading.
 */
import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from '../../i18n/I18nContext'

export default function RecommendationEmptyState({
  message,
  actionUrl = '/student/reading-coach',
}) {
  const { t } = useTranslation()

  return (
    <div
      role="status"
      className="bg-white rounded-3xl p-8 sm:p-12 border border-stone-200/90 shadow-2xs text-center max-w-xl mx-auto space-y-5"
    >
      <div className="w-16 h-16 mx-auto rounded-3xl bg-teal-50 border border-teal-200 flex items-center justify-center text-3xl">
        🌱
      </div>

      <div className="space-y-2">
        <h3 className="text-lg sm:text-xl font-black text-stone-900 tracking-tight">
          {t('recommendations.noDataTitle', "We're Getting to Know You!")}
        </h3>
        <p className="text-xs sm:text-sm text-stone-600 leading-relaxed max-w-md mx-auto">
          {message ||
            t(
              'recommendations.noDataMsg',
              'Start with a short reading activity. As you read, DyslexAid will suggest personalized practice steps just for you!'
            )}
        </p>
      </div>

      <div className="pt-2">
        <Link
          to={actionUrl}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[#1A6B6B] text-white text-xs sm:text-sm font-bold rounded-2xl hover:bg-[#155555] focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] focus:ring-offset-2 transition-all shadow-xs"
        >
          <span>📖</span>
          <span>{t('recommendations.startReadingBtn', 'Start Reading')}</span>
        </Link>
      </div>
    </div>
  )
}
