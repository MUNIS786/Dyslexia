/**
 * frontend/src/features/reading/ReadingSessionResult.jsx
 *
 * Child-friendly result celebration screen:
 * - What you did (passage, words, time, practiced words)
 * - How it went (encouraging feedback, celebration badges)
 * - What's next (explainable adaptive progression update)
 * - Action: Try Next Reading or Back to Home
 */
import { Card, Button, Badge } from '../../components/ui'

export default function ReadingSessionResult({
  result,
  activePassage,
  onTryNextReading,
  onGoHome,
}) {
  if (!result) return null

  const {
    correctCount = 0,
    totalQuestions = 0,
    wordsRead = 0,
    durationSeconds = 0,
    practicedWordsCount = 0,
    comprehensionScore = 80,
    adaptation = {},
    nextStepMessage,
  } = result

  const formatMinutes = (secs) => {
    const mins = Math.max(1, Math.round(secs / 60))
    return `${mins} min${mins > 1 ? 's' : ''}`
  }

  // Encouraging summary based on comprehension accuracy
  let performancePraise = 'Great reading! You understood the story really well.'
  let praiseEmoji = '🌟'
  if (comprehensionScore >= 90) {
    performancePraise = 'Outstanding reading superstar! You understood every detail.'
    praiseEmoji = '🏆'
  } else if (comprehensionScore < 60) {
    performancePraise = 'Good effort! Every story you read builds your reading brain.'
    praiseEmoji = '🌱'
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Celebration Header Card */}
      <Card className="p-6 sm:p-8 text-center shadow-card border-slate-200 space-y-3">
        <div className="w-20 h-20 mx-auto mb-2 bg-amber-100 rounded-3xl flex items-center justify-center text-4xl shadow-inner">
          {praiseEmoji}
        </div>

        <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold text-slate-900">
          {comprehensionScore >= 75 ? 'Super Reading!' : 'Nice Job Finishing!'}
        </h1>
        <p className="dyslexia-text text-base sm:text-lg text-slate-600 font-medium max-w-md mx-auto">
          {performancePraise}
        </p>

        {/* Level Up Banner if Tier Changed */}
        {adaptation?.tierChanged && adaptation.newTier > adaptation.previousTier && (
          <div className="mt-4 p-4 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-emerald-900 font-extrabold text-base flex items-center justify-center gap-2">
            <span>🎉</span>
            <span>LEVEL UP! You unlocked Reading Level {adaptation.newTier}!</span>
          </div>
        )}

        {/* Gamification Points & Badges Reward Callout */}
        {result?.gamification && result.gamification.pointsAwarded > 0 && (
          <div id="reading-gamification-reward" className="mt-4 p-3.5 bg-amber-50 rounded-2xl border border-amber-200 flex items-center justify-between text-xs font-bold text-amber-950 dyslexia-text">
            <div className="flex items-center gap-2">
              <span className="text-xl" aria-hidden="true">🏆</span>
              <span>{result.gamification.celebrationMessage || `+${result.gamification.pointsAwarded} Learning Points Earned!`}</span>
            </div>
            <Badge color="amber">
              Total: {result.gamification.totalPoints} pts
            </Badge>
          </div>
        )}
      </Card>

      {/* What You Did — Stat Cards */}
      <Card className="p-6 sm:p-7 shadow-card border-slate-200">
        <h2 className="dyslexia-text text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
          What You Accomplished
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-center">
            <span className="text-xl block mb-1">📖</span>
            <span className="text-lg sm:text-xl font-extrabold text-slate-900 block">
              {wordsRead}
            </span>
            <span className="text-xs text-slate-500 font-medium dyslexia-text">Words Read</span>
          </div>

          <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-center">
            <span className="text-xl block mb-1">⏱️</span>
            <span className="text-lg sm:text-xl font-extrabold text-slate-900 block">
              {formatMinutes(durationSeconds)}
            </span>
            <span className="text-xs text-slate-500 font-medium dyslexia-text">Reading Time</span>
          </div>

          <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-center">
            <span className="text-xl block mb-1">❓</span>
            <span className="text-lg sm:text-xl font-extrabold text-slate-900 block">
              {correctCount}/{totalQuestions}
            </span>
            <span className="text-xs text-slate-500 font-medium dyslexia-text">Questions</span>
          </div>

          <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-center">
            <span className="text-xl block mb-1">💡</span>
            <span className="text-lg sm:text-xl font-extrabold text-slate-900 block">
              {practicedWordsCount}
            </span>
            <span className="text-xs text-slate-500 font-medium dyslexia-text">New Words</span>
          </div>
        </div>
      </Card>

      {/* Voice Reading Practice Badge if Speech Mode was used */}
      {result.speechWordAccuracy !== undefined && (
        <Card className="bg-gradient-to-r from-teal-50 to-emerald-50 p-5 border-teal-200 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🎙️</span>
            <div>
              <h3 className="dyslexia-text text-sm font-extrabold text-slate-900">
                Voice Reading Practice
              </h3>
              <p className="dyslexia-text text-xs text-slate-600 mt-0.5">
                {Math.round(result.speechWordAccuracy)}% words read clearly • {Math.round(result.speechWordsPerMinute || 0)} WPM pace
              </p>
            </div>
          </div>
          <Badge color="teal" className="text-xs font-extrabold">
            Score: {Math.round(result.speechPracticeScore || result.speechWordAccuracy)}/100
          </Badge>
        </Card>
      )}

      {/* What's Next Adaptive Decision */}
      <Card className="bg-amber-50/70 p-6 sm:p-7 border-amber-200">
        <div className="flex items-start gap-3">
          <span className="text-2xl shrink-0">🧭</span>
          <div>
            <h3 className="dyslexia-text text-xs font-bold text-amber-900 uppercase tracking-wider mb-1">
              What We&apos;ll Do Next
            </h3>
            <p className="dyslexia-text text-slate-800 text-sm sm:text-base font-medium leading-relaxed">
              {nextStepMessage || "You're doing great! Let's explore your next reading recommendation."}
            </p>
          </div>
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <Button
          onClick={onTryNextReading}
          size="lg"
          className="w-full sm:flex-1 shadow-md"
        >
          <span>Try Next Reading</span>
          <span>🚀</span>
        </Button>

        <Button
          variant="outline"
          onClick={onGoHome}
          size="lg"
          className="w-full sm:w-auto"
        >
          Back to Home
        </Button>
      </div>
    </div>
  )
}
