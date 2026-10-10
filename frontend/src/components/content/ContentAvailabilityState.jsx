/**
 * frontend/src/components/content/ContentAvailabilityState.jsx
 *
 * Transparent notice component displayed when exact language translation is unavailable
 * or when an explicit language fallback is offered. Never conceals language substitution.
 */
import React from 'react'
import { useTranslation } from '../../i18n/I18nContext'

export default function ContentAvailabilityState({
  status,
  message,
  requestedLanguage,
  actualLanguage,
}) {
  const { t } = useTranslation()

  if (status === 'EXACT_MATCH' || !message) return null

  const isFallback = status === 'LANGUAGE_FALLBACK_OFFERED'

  return (
    <div
      role="status"
      className={`rounded-2xl p-4 border flex flex-col sm:flex-row items-start sm:items-center gap-3 text-xs sm:text-sm ${
        isFallback
          ? 'bg-amber-50/80 border-amber-300 text-amber-950'
          : 'bg-stone-50 border-stone-200 text-stone-800'
      }`}
    >
      <div className="flex items-center gap-2 font-bold shrink-0">
        <span aria-hidden="true" className="text-xl">
          {isFallback ? '🌐' : 'ℹ️'}
        </span>
        <span>
          {t('personalizedContent.fallbackAlertTitle', 'Language Notice')}:
        </span>
      </div>

      <p className="flex-1 leading-relaxed text-xs sm:text-sm">
        {message}
      </p>

      {requestedLanguage && actualLanguage && requestedLanguage !== actualLanguage && (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-amber-200/60 text-amber-950 text-xs font-bold uppercase tracking-wider shrink-0">
          {requestedLanguage} → {actualLanguage}
        </span>
      )}
    </div>
  )
}
