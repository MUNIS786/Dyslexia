/**
 * frontend/src/components/recommendations/RecommendationCard.jsx
 *
 * Accessible, encouraging recommendation card.
 * Clearly articulates the activity, reason, target words, and primary action.
 * Includes optional 'Ask AI Tutor' integration.
 */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from '../../i18n/I18nContext'
import RecommendationReason from './RecommendationReason'

export default function RecommendationCard({
  recommendation,
  onLaunch,
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  if (!recommendation) return null

  const {
    category,
    title,
    reason,
    detailedExplanation,
    actionUrl = '/student/reading-coach',
    actionLabel = 'Start Practice',
    estimatedDurationMinutes = 5,
    priority = 1,
    targetWords = [],
    completed = false,
    evidenceSignals = [],
  } = recommendation

  const categoryConfig = {
    READING_PRACTICE: {
      label: 'Reading Practice',
      icon: '📖',
      badgeClass: 'bg-teal-50 text-teal-800 border-teal-200',
    },
    DIFFICULT_WORD_PRACTICE: {
      label: 'Tricky Words',
      icon: '🎯',
      badgeClass: 'bg-amber-50 text-amber-900 border-amber-200',
    },
    SPEECH_PRACTICE: {
      label: 'Read Aloud',
      icon: '🎤',
      badgeClass: 'bg-purple-50 text-purple-900 border-purple-200',
    },
    REVIEW: {
      label: 'Skill Review',
      icon: '🔄',
      badgeClass: 'bg-blue-50 text-blue-900 border-blue-200',
    },
    STRETCH: {
      label: 'Explorer Challenge',
      icon: '🚀',
      badgeClass: 'bg-emerald-50 text-emerald-900 border-emerald-200',
    },
    CONSISTENCY: {
      label: 'Daily Habit',
      icon: '🔥',
      badgeClass: 'bg-orange-50 text-orange-900 border-orange-200',
    },
  }[category] || {
    label: 'Practice',
    icon: '✨',
    badgeClass: 'bg-stone-50 text-stone-800 border-stone-200',
  }

  const handleAskTutor = () => {
    const promptText = `I am working on: "${title}". Can you give me friendly tips on how to practice this?`
    navigate(`/student/tutor?prompt=${encodeURIComponent(promptText)}`)
  }

  return (
    <article
      className={`bg-white rounded-3xl p-5 sm:p-6 border transition-all shadow-2xs hover:shadow-xs flex flex-col justify-between gap-5 ${
        completed ? 'border-emerald-300/80 bg-emerald-50/20' : 'border-stone-200'
      }`}
      aria-labelledby={`rec-title-${recommendation.id}`}
    >
      <div className="space-y-4">
        {/* Header Badges */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-stone-900 text-white text-xs font-black"
              aria-label={`Priority ${priority}`}
            >
              {priority}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${categoryConfig.badgeClass}`}
            >
              <span aria-hidden="true">{categoryConfig.icon}</span>
              <span>{categoryConfig.label}</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-stone-500">
              <span aria-hidden="true">⏱️</span>
              <span>{estimatedDurationMinutes} mins</span>
            </span>
            {completed && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 text-xs font-extrabold">
                <span aria-hidden="true">✓</span>
                <span>{t('recommendations.completed', 'Completed')}</span>
              </span>
            )}
          </div>
        </div>

        {/* Title */}
        <h3
          id={`rec-title-${recommendation.id}`}
          className="text-base sm:text-lg font-black text-stone-900 tracking-tight"
        >
          {title}
        </h3>

        {/* Tricky Words Chips (if any) */}
        {targetWords && targetWords.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[11px] font-bold text-stone-500 block uppercase tracking-wider">
              {t('recommendations.targetWords', 'Words in Focus:')}
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

        {/* Reason Block */}
        <RecommendationReason
          reason={reason}
          detailedExplanation={detailedExplanation}
          evidenceSignals={evidenceSignals}
        />
      </div>

      {/* Action Buttons */}
      <div className="pt-2 border-t border-stone-100 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Direct Launch */}
          <Link
            to={actionUrl}
            onClick={onLaunch}
            className={`inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              completed
                ? 'bg-stone-100 text-stone-800 hover:bg-stone-200 focus:ring-stone-400'
                : 'bg-[#1A6B6B] text-white hover:bg-[#155555] focus:ring-[#1A6B6B]'
            }`}
          >
            <span aria-hidden="true">🚀</span>
            <span>
              {completed ? 'Practice Again' : (actionLabel || t('recommendations.startPractice', 'Start Practice'))}
            </span>
          </Link>

          {/* Activity Hub Details */}
          <Link
            to={`/student/activity?recommendationId=${encodeURIComponent(recommendation.id)}`}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-2xl text-xs font-bold text-teal-800 bg-teal-50 hover:bg-teal-100 transition-all border border-teal-200"
            title="View activity instructions and steps"
          >
            <span aria-hidden="true">✨</span>
            <span>{t('personalizedContent.exploreActivity', 'Details')}</span>
          </Link>
        </div>

        {/* AI Tutor Integration */}
        <button
          type="button"
          onClick={handleAskTutor}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-2xl text-xs font-bold text-stone-600 bg-stone-100 hover:bg-stone-200/80 hover:text-stone-900 transition-all focus:outline-none focus:ring-2 focus:ring-[#1A6B6B]"
          title="Ask the AI Tutor for tips on this activity"
        >
          <span aria-hidden="true">🤖</span>
          <span>{t('recommendations.askTutor', 'Ask AI Tutor')}</span>
        </button>
      </div>
    </article>
  )
}
