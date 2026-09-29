/**
 * frontend/src/features/learning/InteractiveTaskPlayer.jsx — Accessible Interactive Micro-Task Player.
 * Supports phoneme blending, rapid naming, sight word building, comprehension, and reversal discrimination.
 * Tracks latency, hesitations, and hints, with Web Speech API read-aloud support.
 */
import React, { useState, useEffect, useRef } from 'react'
import { Card, Button, Badge } from '../../components/ui'

export default function InteractiveTaskPlayer({
  activity,
  onClose,
  onSubmitAttempt,
  submitting = false,
}) {
  const payload = activity?.contentPayload || {}
  const [selectedOption, setSelectedOption] = useState(null)
  const [isAnswered, setIsAnswered] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [showHint, setShowHint] = useState(false)
  const [hintsUsed, setHintsUsed] = useState(0)
  const [hesitations, setHesitations] = useState(0)
  const [secondsElapsed, setSecondsElapsed] = useState(0)
  const [isFinished, setIsFinished] = useState(false)
  const [scorePercent, setScorePercent] = useState(0)

  // Timer & Hesitation Tracking
  const lastInteractionRef = useRef(Date.now())
  const timerRef = useRef(null)

  useEffect(() => {
    lastInteractionRef.current = Date.now()
    timerRef.current = setInterval(() => {
      setSecondsElapsed((prev) => prev + 1)

      // Hesitation detection: if no interaction for > 8 seconds, count as hesitation
      const idle = (Date.now() - lastInteractionRef.current) / 1000
      if (idle >= 8.0 && !isAnswered) {
        setHesitations((h) => h + 1)
        lastInteractionRef.current = Date.now() // reset window
      }
    }, 1000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isAnswered])

  // Reset interaction timer on clicks
  const registerInteraction = () => {
    lastInteractionRef.current = Date.now()
  }

  // Audio TTS helper
  const speakText = (text) => {
    registerInteraction()
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 0.85
    utterance.lang = 'en-US'
    window.speechSynthesis.speak(utterance)
  }

  const handleRequestHint = () => {
    registerInteraction()
    if (!showHint) {
      setShowHint(true)
      setHintsUsed((h) => h + 1)
    }
  }

  const handleSelectOption = (opt) => {
    if (isAnswered) return
    registerInteraction()
    setSelectedOption(opt.id)
    setIsAnswered(true)

    const correct = Boolean(opt.isCorrect)
    setIsCorrect(correct)

    // Calculate score: 100 base, -15 if hint used
    let score = correct ? 100.0 : 40.0
    if (showHint && correct) {
      score = Math.max(70.0, score - 15.0)
    }
    setScorePercent(score)
    setIsFinished(true)

    if (correct) {
      speakText('Correct! ' + (payload.explanation || 'Great job!'))
    } else {
      speakText('Keep trying! ' + (payload.hint || 'Take a close look!'))
    }
  }

  const handleCompleteSpeedNaming = () => {
    registerInteraction()
    setIsAnswered(true)
    setIsCorrect(true)
    const score = hesitations > 2 ? 80.0 : 100.0
    setScorePercent(score)
    setIsFinished(true)
  }

  const handleFinalSubmit = () => {
    if (onSubmitAttempt) {
      onSubmitAttempt({
        activityId: activity.id,
        scorePercent: scorePercent,
        durationSeconds: Math.max(1, secondsElapsed),
        hesitationCount: hesitations,
        hintsRequested: hintsUsed,
        completed: true,
      })
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto flex flex-col justify-between border-2 border-[#1A6B6B]/30 shadow-2xl animate-fade-in">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-gray-200 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎯</span>
            <div>
              <h2 className="dyslexia-text font-bold text-lg text-[#1A2A2A]">
                {activity.title}
              </h2>
              <p className="dyslexia-text text-xs text-gray-500">
                Level {activity.difficultyTier} • {activity.domain?.replace('_', ' ')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge color="teal">⏱ {secondsElapsed}s</Badge>
            <button
              onClick={onClose}
              disabled={submitting}
              className="text-gray-400 hover:text-gray-600 text-xl font-bold px-2 py-1 rounded"
              aria-label="Close task"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Challenge Body */}
        <div className="flex-1 my-2">
          {/* Audio Prompt button & Instruction */}
          <div className="bg-[#FFF8F0] border border-[#E5E0D8] rounded-2xl p-4 mb-4 flex items-start gap-3">
            <button
              onClick={() => speakText(payload.audioPrompt || payload.instruction || activity.title)}
              className="w-12 h-12 bg-[#1A6B6B] hover:bg-[#155555] text-white rounded-xl flex items-center justify-center text-xl shadow flex-shrink-0"
              title="Listen to instruction"
              aria-label="Listen out loud"
            >
              🔊
            </button>
            <div className="flex-1">
              <p className="dyslexia-text text-sm font-semibold text-gray-800">
                {payload.instruction || 'Follow the instructions below:'}
              </p>
              {payload.passage && (
                <div className="mt-3 p-3 bg-white rounded-xl border border-gray-200 text-base leading-relaxed text-gray-800 dyslexia-text">
                  {payload.passage}
                </div>
              )}
              {payload.question && (
                <p className="dyslexia-text text-base font-bold text-[#1A6B6B] mt-3">
                  {payload.question}
                </p>
              )}
            </div>
          </div>

          {/* Speed Naming Grid (special interactive payload) */}
          {payload.type === 'speed_naming' && payload.items && (
            <div className="mb-4">
              <p className="dyslexia-text text-xs text-gray-500 mb-2 text-center">
                Read through each item from left to right as fast as you can:
              </p>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-4">
                {payload.items.map((item, idx) => (
                  <div
                    key={item.id || idx}
                    className="p-4 rounded-xl flex flex-col items-center justify-center border-2 border-gray-200 font-bold text-lg shadow-sm"
                    style={{ backgroundColor: item.color || '#FFF' }}
                  >
                    <span className="text-[#1A2A2A]">{item.label}</span>
                  </div>
                ))}
              </div>
              {!isFinished && (
                <Button
                  onClick={handleCompleteSpeedNaming}
                  className="w-full py-3 text-lg"
                  size="lg"
                >
                  ✓ I finished naming them!
                </Button>
              )}
            </div>
          )}

          {/* Standard Multiple Choice / Phoneme / Visual Options */}
          {payload.options && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              {payload.options.map((opt) => {
                const isThisSelected = selectedOption === opt.id
                let btnStyle = 'bg-white hover:bg-gray-50 border-gray-200'

                if (isAnswered) {
                  if (opt.isCorrect) {
                    btnStyle = 'bg-green-100 border-green-500 text-green-900 font-bold'
                  } else if (isThisSelected && !opt.isCorrect) {
                    btnStyle = 'bg-red-100 border-red-500 text-red-900'
                  } else {
                    btnStyle = 'opacity-40 border-gray-200'
                  }
                }

                return (
                  <button
                    key={opt.id}
                    onClick={() => handleSelectOption(opt)}
                    disabled={isAnswered}
                    className={`p-4 rounded-2xl border-2 text-left transition-all flex items-center gap-3 dyslexia-text text-base ${btnStyle}`}
                  >
                    {opt.icon && <span className="text-3xl">{opt.icon}</span>}
                    {opt.shape && <span className="text-3xl">{opt.shape}</span>}
                    <span className="font-semibold text-lg flex-1">
                      {opt.text || opt.label}
                    </span>
                    {isAnswered && opt.isCorrect && (
                      <span className="text-green-600 text-xl font-bold">✓</span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Hint Area */}
          {payload.hint && (
            <div className="mb-3">
              {!showHint ? (
                <button
                  onClick={handleRequestHint}
                  className="text-xs text-[#1A6B6B] hover:underline font-semibold flex items-center gap-1"
                >
                  💡 Need a hint?
                </button>
              ) : (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 dyslexia-text">
                  <strong>Hint:</strong> {payload.hint}
                </div>
              )}
            </div>
          )}

          {/* Feedback & Explanation */}
          {isAnswered && (
            <div
              className={`p-4 rounded-2xl border mb-3 animate-fade-in ${
                isCorrect ? 'bg-green-50 border-green-300' : 'bg-amber-50 border-amber-300'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl">{isCorrect ? '🎉' : '🌱'}</span>
                <p className="dyslexia-text font-bold text-base">
                  {isCorrect ? 'Awesome job!' : 'Good try!'}
                </p>
              </div>
              <p className="dyslexia-text text-sm text-gray-700">
                {payload.explanation || 'You completed this micro-challenge!'}
              </p>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t border-gray-200 pt-3 flex items-center justify-between gap-2">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>

          {isFinished && (
            <Button
              onClick={handleFinalSubmit}
              disabled={submitting}
              className="px-6 py-2 bg-[#E8A020] hover:bg-[#d4901a] text-white font-bold"
            >
              {submitting ? 'Saving...' : 'Finish & Save Progress →'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
