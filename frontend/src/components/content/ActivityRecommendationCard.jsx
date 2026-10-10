/**
 * frontend/src/components/content/ActivityRecommendationCard.jsx
 *
 * Full-featured personalized learning activity card.
 * Clearly articulates the activity type, level, estimated duration, rationale, and action.
 * Logs launch telemetry upon clicking without artificially marking completion.
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from '../../i18n/I18nContext'
import { personalizedContentV2API } from '../../api/v2/client'
import ActivityReason from './ActivityReason'

const TYPE_CONFIG = {
  GUIDED_READING: {
    labelKey: 'personalizedContent.activityTypeGuided',
    defaultLabel: 'Guided Reading',
    icon: '📖',
    badgeClass: 'bg-teal-50 text-teal-800 border-teal-200',
  },
  DIFFICULT_WORD_PRACTICE: {
    labelKey: 'personalizedContent.activityTypeWords',
    defaultLabel: 'Tricky Words Quest',
    icon: '🎯',
    badgeClass: 'bg-amber-50 text-amber-900 border-amber-200',
  },
  READING_COMPREHENSION: {
    labelKey: 'personalizedContent.activityTypeComp',
    defaultLabel: 'Reading Comprehension',
    icon: '🧩',
    badgeClass: 'bg-blue-50 text-blue-900 border-blue-200',
  },
  VOCABULARY_PRACTICE: {
    labelKey: 'personalizedContent.activityTypeVocab',
    defaultLabel: 'Vocabulary Explorer',
    icon: '🔍',
    badgeClass: 'bg-indigo-50 text-indigo-900 border-indigo-200',
  },
  ORAL_READING_SPEECH: {
    labelKey: 'personalizedContent.activityTypeOral',
    defaultLabel: 'Read Aloud Voice Practice',
    icon: '🎤',
    badgeClass: 'bg-purple-50 text-purple-900 border-purple-200',
  },
  SKILL_REVIEW: {
    labelKey: 'personalizedContent.activityTypeReview',
    defaultLabel: 'Skill Review',
    icon: '🔄',
    badgeClass: 'bg-emerald-50 text-emerald-900 border-emerald-200',
  },
}

export default function ActivityRecommendationCard({
  activity,
  isHero = false,
  onLaunch = null,
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  if (!activity) return null

  const {
    activityId,
    activityType,
    title,
    description,
    language = 'en',
    difficultyTier = 1,
    tierName = 'Foundation',
    estimatedDurationMinutes = 5,
    reason,
    detailedRationale,
    targetSkills = [],
    targetWords = [],
    actionUrl = '/student/reading-coach',
    actionLabel,
    completed = false,
  } = activity

  const typeMeta = TYPE_CONFIG[activityType] || {
    labelKey: 'common.practice',
    defaultLabel: 'Practice',
    icon: '✨',
    badgeClass: 'bg-stone-50 text-stone-800 border-stone-200',
  }

  const handleStartActivity = async (e) => {
    e.preventDefault()
    try {
      // Log launch telemetry asynchronously without blocking navigation
      personalizedContentV2API
        .launchActivity({
          activityId,
          activityType,
          recommendationId: activity.recommendationId || null,
          language,
        })
        .catch(() => {})
    } catch {
      // Ignored non-critical telemetry failure
    }

    if (onLaunch) {
      onLaunch(activity)
    }

    // Navigate to actual destination
    navigate(actionUrl)
  }

  return (
    <article
      className={`bg-white rounded-3xl p-5 sm:p-6 border transition-all flex flex-col justify-between gap-5 shadow-2xs hover:shadow-xs ${
        completed
          ? 'border-emerald-300 bg-emerald-50/20'
          : isHero
          ? 'border-teal-400/80 ring-2 ring-teal-500/20'
          : 'border-stone-200/90'
      }`}
      aria-labelledby={`act-title-${activityId}`}
    >
      <div className="space-y-4">
        {/* Badges Row */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${typeMeta.badgeClass}`}
            >
              <span aria-hidden="true">{typeMeta.icon}</span>
              <span>{t(typeMeta.labelKey, typeMeta.defaultLabel)}</span>
            </span>

            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-stone-100 text-stone-700 border border-stone-200 uppercase">
              {language}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs font-semibold text-stone-500">
            <span className="inline-flex items-center gap-1">
              <span aria-hidden="true">🎯</span>
              <span>
                {t('personalizedContent.level', 'Level')} {difficultyTier}: {tierName}
              </span>
            </span>
            <span>•</span>
            <span className="inline-flex items-center gap-1">
              <span aria-hidden="true">⏱️</span>
              <span>
                {estimatedDurationMinutes} {t('personalizedContent.duration', 'mins')}
              </span>
            </span>
            {completed && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 text-xs font-extrabold">
                <span aria-hidden="true">✓</span>
                <span>{t('personalizedContent.completedBadge', 'Completed')}</span>
              </span>
            )}
          </div>
        </div>

        {/* Title & Description */}
        <div className="space-y-1.5">
          <h3
            id={`act-title-${activityId}`}
            className="text-lg sm:text-xl font-black text-stone-900 tracking-tight"
          >
            {title}
          </h3>
          {description && (
            <p className="text-xs sm:text-sm text-stone-600 leading-relaxed">
              {description}
            </p>
          )}
        </div>

        {/* Words in Focus (if any) */}
        {targetWords && targetWords.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[11px] font-bold text-stone-500 block uppercase tracking-wider">
              {t('personalizedContent.targetWordsTitle', 'Focus Words:')}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {targetWords.map((word, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-0.5 rounded-xl bg-amber-50 text-amber-950 border border-amber-200 text-xs font-bold"
                >
                  {word}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Child-friendly Reason */}
        <ActivityReason
          reason={reason}
          detailedRationale={detailedRationale}
          targetSkills={targetSkills}
        />
      </div>

      {/* Action Footer */}
      <div className="pt-3 border-t border-stone-100 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleStartActivity}
          className={`inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-offset-2 ${
            completed
              ? 'bg-stone-100 text-stone-800 hover:bg-stone-200 focus:ring-stone-400'
              : 'bg-[#1A6B6B] text-white hover:bg-[#155555] focus:ring-[#1A6B6B]'
          }`}
        >
          <span aria-hidden="true">🚀</span>
          <span>
            {completed
              ? t('personalizedContent.practiceAgain', 'Practice Again')
              : (actionLabel || t('personalizedContent.startActivity', 'Start Activity'))}
          </span>
        </button>

        <span className="text-[11px] text-stone-400 italic">
          {t(
            'personalizedContent.launchNotice',
            'Opens reading session with your accessibility preferences.'
          )}
        </span>
      </div>
    </article>
  )
}
