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
  2: 'teal',
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
        <p className="dyslexia-text text-gray-500">
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
        const tierColor = TIER_COLORS[tier] || 'teal'
        const isStrength = rec.matchType === 'strength_reinforcement'

        return (
          <Card
            key={rec.id || act.id}
            className="flex flex-col justify-between hover:shadow-md transition-shadow border-2 border-transparent hover:border-[#1A6B6B]/20"
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
              <h3 className="dyslexia-text font-bold text-lg text-[#1A2A2A] mb-1">
                {act.title}
              </h3>
              <p className="dyslexia-text text-xs text-gray-500 mb-3">
                ⏱ ~{Math.round((act.durationSecondsExpected || 90) / 60)} min •{' '}
                {act.domain ? act.domain.replace('_', ' ').toUpperCase() : 'SKILL PRACTICE'}
              </p>

              {/* Pedagogical Rationale */}
              <div className="bg-[#F0F8FF] border border-[#D0E8FF] rounded-xl p-3 mb-4">
                <p className="dyslexia-text text-xs text-gray-700 leading-relaxed flex items-start gap-1.5">
                  <span className="text-sm">💡</span>
                  <span>
                    <strong className="text-[#1A6B6B]">Why recommended:</strong> {rec.rationale}
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
