/**
 * frontend/src/pages/student/PersonalizedActivityPage.jsx
 *
 * Dedicated student page for Phase 15 Personalized Learning Content & Activity Engine.
 * Allows students to discover, preview, and launch activities curated specifically
 * for their Zone of Proximal Development (ZPD) and language preferences.
 * Connects directly from Phase 14 recommendations.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { personalizedContentV2API } from '../../api/v2/client'
import { useTranslation } from '../../i18n/I18nContext'
import {
  ActivityRecommendationCard,
  ContentAvailabilityState,
} from '../../components/content'
import toast from 'react-hot-toast'

export default function PersonalizedActivityPage() {
  const { t, currentLanguage, setLanguage } = useTranslation()
  const [searchParams] = useSearchParams()
  const recommendationId = searchParams.get('recommendationId')
  const requestedType = searchParams.get('activityType')

  const [heroActivity, setHeroActivity] = useState(null)
  const [catalog, setCatalog] = useState([])
  const [activeTier, setActiveTier] = useState(1)
  const [tierName, setTierName] = useState('Foundation')
  const [status, setStatus] = useState('EXACT_MATCH')
  const [fallbackMessage, setFallbackMessage] = useState(null)
  const [filterType, setFilterType] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadContent = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (recommendationId) {
        // 1. User clicked directly from a Phase 14 recommendation
        const item = await personalizedContentV2API.getContentForRecommendation(
          recommendationId,
          currentLanguage
        )
        setHeroActivity(item)
        setActiveTier(item.difficultyTier)
        setTierName(item.tierName)
        setStatus(item.availabilityStatus)
        setFallbackMessage(item.languageFallbackMessage)

        // Also fetch catalog of other activities
        const listRes = await personalizedContentV2API.getPersonalizedActivities({
          language: currentLanguage,
          tier: item.difficultyTier,
        })
        setCatalog(listRes.activities || [])
      } else {
        // 2. Default flow: fetch next best activity + full personalized catalog
        const nextRes = await personalizedContentV2API.getNextActivity(
          currentLanguage,
          requestedType
        )
        setHeroActivity(nextRes.activity)
        setActiveTier(nextRes.currentAdaptiveTier)
        setTierName(nextRes.currentAdaptiveTierName)
        setStatus(nextRes.status)
        setFallbackMessage(nextRes.message)

        const listRes = await personalizedContentV2API.getPersonalizedActivities({
          language: currentLanguage,
          tier: nextRes.currentAdaptiveTier,
        })
        setCatalog(listRes.activities || [])
      }
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err.message ||
        'Could not load personalized learning activities.'
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [recommendationId, requestedType, currentLanguage])

  useEffect(() => {
    loadContent()
  }, [loadContent])

  const filteredCatalog =
    filterType === 'ALL'
      ? catalog
      : catalog.filter((act) => act.activityType === filterType)

  return (
    <div className="max-w-6xl mx-auto py-6 px-3 sm:px-6 space-y-6">
      {/* Top Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-stone-200/90 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-3xl sm:text-4xl" aria-hidden="true">
              📚
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-stone-900 tracking-tight">
              {t('personalizedContent.pageTitle', 'Personalized Learning Activities')}
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-stone-600 max-w-2xl leading-relaxed">
            {t(
              'personalizedContent.pageSubtitle',
              'Engaging reading and phonics activities chosen for your learning style and active level.'
            )}
          </p>

          {/* Level Badges */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-teal-50 text-teal-900 border border-teal-200">
              <span aria-hidden="true">🎯</span>
              <span>
                {t('personalizedContent.tier', 'Tier')} {activeTier}: {tierName}
              </span>
            </span>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-stone-100 text-stone-800 border border-stone-200">
              <span aria-hidden="true">🌐</span>
              <span className="uppercase">{currentLanguage}</span>
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Back to Recommendations */}
          <Link
            to="/student/recommendations"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold bg-stone-100 text-stone-800 hover:bg-stone-200 transition-all border border-stone-200 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B]"
          >
            <span aria-hidden="true">🧭</span>
            <span>
              {t('personalizedContent.backToRecommendations', 'Back to Next Steps & Plan')}
            </span>
          </Link>

          {/* Language Switcher Quick Buttons */}
          <div className="inline-flex rounded-2xl border border-stone-200 p-1 bg-stone-50 gap-1 text-xs font-bold">
            <button
              type="button"
              onClick={() => setLanguage('en')}
              className={`px-2.5 py-1 rounded-xl transition-all ${
                currentLanguage === 'en'
                  ? 'bg-white text-stone-900 shadow-2xs'
                  : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              EN
            </button>
            <button
              type="button"
              onClick={() => setLanguage('hi')}
              className={`px-2.5 py-1 rounded-xl transition-all ${
                currentLanguage === 'hi'
                  ? 'bg-white text-stone-900 shadow-2xs'
                  : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              हिन्दी
            </button>
            <button
              type="button"
              onClick={() => setLanguage('mr')}
              className={`px-2.5 py-1 rounded-xl transition-all ${
                currentLanguage === 'mr'
                  ? 'bg-white text-stone-900 shadow-2xs'
                  : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              मराठी
            </button>
          </div>
        </div>
      </div>

      {/* Language Fallback Notice (if applicable) */}
      <ContentAvailabilityState
        status={status}
        message={fallbackMessage}
        requestedLanguage={currentLanguage}
        actualLanguage={heroActivity?.language}
      />

      {/* Error Banner */}
      {error && !loading && (
        <div
          role="alert"
          className="rounded-3xl p-6 bg-red-50 border border-red-200 text-red-900 flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl" aria-hidden="true">
              ⚠️
            </span>
            <span className="text-sm font-semibold">{error}</span>
          </div>
          <button
            type="button"
            onClick={loadContent}
            className="px-4 py-2 bg-red-800 text-white text-xs font-bold rounded-xl hover:bg-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-6 animate-pulse">
          <div className="h-64 bg-stone-200/60 rounded-3xl" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-48 bg-stone-200/60 rounded-3xl" />
            <div className="h-48 bg-stone-200/60 rounded-3xl" />
          </div>
        </div>
      )}

      {/* Content View */}
      {!loading && !error && (
        <div className="space-y-8">
          {/* 1. Next Recommended Activity Hero Card */}
          {heroActivity && (
            <section aria-labelledby="hero-activity-heading" className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl" aria-hidden="true">
                  ⭐
                </span>
                <h2
                  id="hero-activity-heading"
                  className="text-lg font-black text-stone-900 tracking-tight"
                >
                  {t('personalizedContent.nextBestActivity', 'Your Recommended Activity')}
                </h2>
              </div>

              <ActivityRecommendationCard activity={heroActivity} isHero={true} />
            </section>
          )}

          {/* 2. Available Activities Catalog */}
          <section aria-labelledby="catalog-heading" className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl" aria-hidden="true">
                  🗂️
                </span>
                <h2
                  id="catalog-heading"
                  className="text-lg font-black text-stone-900 tracking-tight"
                >
                  {t('personalizedContent.catalogTitle', 'Available Activities For You')}
                </h2>
              </div>

              {/* Filter Pills */}
              <div className="flex flex-wrap items-center gap-1.5 text-xs font-bold">
                {[
                  { key: 'ALL', labelKey: 'personalizedContent.filterAll', def: 'All' },
                  { key: 'GUIDED_READING', labelKey: 'personalizedContent.activityTypeGuided', def: 'Reading' },
                  { key: 'DIFFICULT_WORD_PRACTICE', labelKey: 'personalizedContent.activityTypeWords', def: 'Words' },
                  { key: 'READING_COMPREHENSION', labelKey: 'personalizedContent.activityTypeComp', def: 'Comprehension' },
                  { key: 'ORAL_READING_SPEECH', labelKey: 'personalizedContent.activityTypeOral', def: 'Read Aloud' },
                  { key: 'SKILL_REVIEW', labelKey: 'personalizedContent.activityTypeReview', def: 'Review' },
                ].map((pill) => (
                  <button
                    key={pill.key}
                    type="button"
                    onClick={() => setFilterType(pill.key)}
                    className={`px-3 py-1.5 rounded-xl border transition-all ${
                      filterType === pill.key
                        ? 'bg-[#1A6B6B] text-white border-[#1A6B6B] shadow-2xs'
                        : 'bg-white text-stone-600 border-stone-200 hover:bg-stone-50'
                    }`}
                  >
                    {t(pill.labelKey, pill.def)}
                  </button>
                ))}
              </div>
            </div>

            {filteredCatalog.length === 0 ? (
              <div className="bg-stone-50 border border-stone-200 rounded-3xl p-8 text-center text-sm text-stone-500">
                {t('personalizedContent.emptyCatalog', 'No activities currently match this filter.')}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {filteredCatalog.map((act) => (
                  <ActivityRecommendationCard key={act.activityId} activity={act} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* Educational Notice */}
      <footer
        role="contentinfo"
        className="rounded-2xl p-4 bg-stone-100/80 border border-stone-200/80 text-[11px] text-stone-500 leading-relaxed space-y-1"
      >
        <div className="flex items-center gap-1.5 font-bold text-stone-700">
          <span aria-hidden="true">ℹ️</span>
          <span>{t('recommendations.disclaimerTitle', 'Educational Support Notice')}</span>
        </div>
        <p>
          {t(
            'recommendations.disclaimerText',
            'These practice activities are personalized learning exercises based on your reading progress. They do not constitute a medical or clinical diagnosis.'
          )}
        </p>
      </footer>
    </div>
  )
}
