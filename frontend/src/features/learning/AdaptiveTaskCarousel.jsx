/**
 * frontend/src/features/learning/AdaptiveTaskCarousel.jsx — Adaptive Task Carousel.
 * Displays tailored micro-tasks with domain badges, tier indicators, and explainable rationale.
 */
import React from 'react'
import { Card, Badge, Button } from '../../components/ui'

const DOMAIN_ICONS = {
  phonological_awareness: '🔤',
  phonological_memory: '🧠',
  rapid_naming: '⚡',
  reading_fluency: '📖',
  orthographic_spelling: '✍️',
  reading_comprehension: '📚',
  visual_processing: '👀',
  visual_attention: '🎯',
  working_memory: '🧩',
  letter_reversal: '🔄',
  language_processing: '💬',
}

const TIER_COLORS = {
  1: 'blue',
  2: 'indigo',
  3: 'green',
  4: 'amber',
  5: 'red',
}

export default function AdaptiveTaskCarousel({
  recommendations = [],
  onStartActivity,
  disabled = false,
}) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="dyslexia-text text-slate-500">
          No new activities scheduled right now. Check back soon or view your full library!
        </p>
      </Card>
    )
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {recommendations.map((rec) => {
        const act = rec.activity || {}
        const domainIcon = DOMAIN_ICONS[act.domain] || '⭐'
        const tier = act.difficultyTier || rec.difficultyTier || 1
        const tierColor = TIER_COLORS[tier] || 'indigo'
        const isStrength = rec.matchType === 'strength_reinforcement'

        return (
          <Card
            key={rec.id || act.id}
            className="flex flex-col justify-between border border-slate-200 hover:border-indigo-400 hover:shadow-card-hover transition-all"
          >
            <div>
              {/* Header tags */}
              <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className="text-2xl" role="img" aria-label="activity icon">
                    {domainIcon}
                  </span>
                  <Badge color={tierColor}>Level {tier}</Badge>
                </div>
                {isStrength ? (
                  <Badge color="green">⭐ Strength Booster</Badge>
                ) : (
                  <Badge color="amber">🎯 Practice Focus</Badge>
                )}
              </div>

              {/* Title & Duration */}
              <h3 className="dyslexia-text font-bold text-lg text-slate-900 mb-1">
                {act.title}
              </h3>
              <p className="dyslexia-text text-xs text-slate-500 mb-3">
                ⏱ ~{Math.round((act.durationSecondsExpected || 90) / 60)} min •{' '}
                {act.domain ? act.domain.replace('_', ' ').toUpperCase() : 'SKILL PRACTICE'}
              </p>

              {/* Pedagogical Rationale */}
              <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-3 mb-4">
                <p className="dyslexia-text text-xs text-slate-700 leading-relaxed flex items-start gap-1.5">
                  <span className="text-sm">💡</span>
                  <span>
                    <strong className="text-indigo-900">Why recommended:</strong> {rec.rationale}
                  </span>
                </p>
              </div>
            </div>

            {/* Action button */}
            <Button
              className="w-full flex items-center justify-center gap-2"
              onClick={() => onStartActivity && onStartActivity(act)}
              disabled={disabled}
            >
              <span>Play Challenge</span>
              <span>→</span>
            </Button>
          </Card>
        )
      })}
    </div>
  )
}
