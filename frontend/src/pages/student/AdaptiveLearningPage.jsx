/**
 * frontend/src/pages/student/AdaptiveLearningPage.jsx — Dedicated V2 Adaptive Learning Page.
 * Dynamic difficulty calibration, micro-tasks player, and ZPD progression tracking.
 */
import React from 'react'
import { useAuth } from '../../context/AuthContext'
import { useAdaptiveEngine } from '../../hooks/v2/useAdaptiveEngine'
import {
  AdaptiveTaskCarousel,
  InteractiveTaskPlayer,
  TierProgressionCard,
  AdaptiveEmptyState,
} from '../../features/learning'
import { Spinner, Button, Card } from '../../components/ui'

export default function AdaptiveLearningPage() {
  const { user } = useAuth()
  const {
    loading,
    error,
    recommendations,
    learningState,
    tierCalibration,
    activeActivity,
    submitting,
    startActivity,
    cancelActivity,
    submitAttempt,
    refresh,
  } = useAdaptiveEngine(4)

  const hasScreening = Boolean(user?.readingProfile?.type || user?.readingProfile?.score)

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Spinner size="lg" />
        <p className="dyslexia-text text-gray-500 font-semibold animate-pulse">
          Calibrating your adaptive reading practice...
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-10 px-4 text-center">
        <Card className="border-red-200 bg-red-50 p-6">
          <p className="text-2xl mb-2">⚠️</p>
          <h2 className="dyslexia-text font-bold text-lg text-red-800 mb-2">
            Adaptive Practice Unavailable
          </h2>
          <p className="dyslexia-text text-sm text-red-600 mb-4">{error}</p>
          <Button onClick={refresh} className="mx-auto">
            Try Again
          </Button>
        </Card>
      </div>
    )
  }

  if (!hasScreening && recommendations.length === 0) {
    return (
      <div className="py-6 px-4 max-w-4xl mx-auto">
        <AdaptiveEmptyState hasScreening={false} />
      </div>
    )
  }

  return (
    <div className="py-6 px-4 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="dyslexia-text font-extrabold text-2xl sm:text-3xl text-[#1A2A2A] flex items-center gap-2">
            <span>Adaptive Practice</span>
            <span className="text-2xl">🎯</span>
          </h1>
          <p className="dyslexia-text text-sm text-gray-500 mt-1">
            Personalized micro-tasks that automatically adjust to your optimal reading sweet spot.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={refresh} className="self-start sm:self-auto">
          ↻ Refresh Tasks
        </Button>
      </div>

      {/* Tier Progression Card */}
      <TierProgressionCard
        learningState={learningState}
        tierCalibration={tierCalibration}
      />

      {/* Recommended Tasks Carousel */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="dyslexia-text font-bold text-xl text-[#1A2A2A] flex items-center gap-2">
            <span>Today's Adaptive Challenges</span>
            <span className="text-lg">✨</span>
          </h2>
          <span className="dyslexia-text text-xs text-gray-500">
            {recommendations.length} challenges ready
          </span>
        </div>

        <AdaptiveTaskCarousel
          recommendations={recommendations}
          onStartActivity={startActivity}
          disabled={submitting}
        />
      </div>

      {/* Educational Information Note */}
      <div className="bg-[#FFF8F0] border border-[#E5E0D8] rounded-2xl p-4 text-xs text-gray-600 dyslexia-text leading-relaxed">
        <p className="font-semibold text-gray-700 mb-1 flex items-center gap-1.5">
          <span>ℹ️</span>
          <span>How the Adaptive Learning Engine works:</span>
        </p>
        <p>
          DyslexAid continuously analyzes your challenge accuracy, hesitations, and hint requests.
          When you demonstrate steady mastery over consecutive sessions, the engine gently advances your
          level. If you ever feel stuck, it provides extra scaffolding so learning always feels encouraging and achievable!
        </p>
      </div>

      {/* Interactive Micro-Task Player Modal */}
      {activeActivity && (
        <InteractiveTaskPlayer
          activity={activeActivity}
          onClose={cancelActivity}
          onSubmitAttempt={submitAttempt}
          submitting={submitting}
        />
      )}
    </div>
  )
}
