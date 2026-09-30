/**
 * frontend/src/features/reading/ComprehensionQuestion.jsx
 *
 * Child-friendly comprehension quiz player:
 * - One question at a time with large readable touch targets
 * - Instant encouraging feedback with educational explanation
 * - Non-punitive language ("You got it!" / "Nice try! Let's check this part again.")
 * - Step progress indicator (e.g. Question 2 of 3)
 */
import React from 'react'

export default function ComprehensionQuestion({
  questions = [],
  currentIndex = 0,
  userAnswers = {},
  questionFeedback = {},
  onSelectAnswer,
  onNextQuestion,
  onFinish,
  submitting = false,
}) {
  if (!questions || questions.length === 0) return null

  const currentQ = questions[currentIndex]
  if (!currentQ) return null

  const total = questions.length
  const qId = currentQ.questionId
  const selectedAnswer = userAnswers[qId]
  const feedback = questionFeedback[qId]
  const isAnswered = selectedAnswer !== undefined
  const isLast = currentIndex === total - 1

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-stone-200 space-y-6">
      {/* Top Header: Progress & Type */}
      <div className="flex items-center justify-between gap-3 border-b border-stone-100 pb-4">
        <span className="text-xs font-bold text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1 rounded-full">
          Question {currentIndex + 1} of {total}
        </span>
        <span className="text-xs font-semibold text-stone-500 capitalize">
          {currentQ.questionType?.replace(/_/g, ' ') || 'Comprehension'}
        </span>
      </div>

      {/* Question Prompt */}
      <h2 className="text-xl sm:text-2xl font-bold text-stone-900 leading-snug">
        {currentQ.question}
      </h2>

      {/* Option Buttons */}
      <div className="space-y-3">
        {currentQ.options.map((optionText, idx) => {
          const isSelected = selectedAnswer === idx

          let buttonStyle = 'bg-stone-50 border-stone-200 hover:bg-stone-100 text-stone-800'
          if (isAnswered) {
            const isCorrectOption =
              typeof currentQ.correctAnswer === 'number'
                ? idx === currentQ.correctAnswer
                : optionText.toLowerCase() === String(currentQ.correctAnswer).toLowerCase()

            if (isSelected) {
              buttonStyle = isCorrectOption
                ? 'bg-emerald-100 border-emerald-500 text-emerald-950 font-bold shadow-xs'
                : 'bg-amber-100 border-amber-500 text-amber-950 font-bold shadow-xs'
            } else if (isCorrectOption) {
              // Highlight the correct answer gently after selection
              buttonStyle = 'bg-emerald-50 border-emerald-300 text-emerald-900'
            } else {
              buttonStyle = 'opacity-50 bg-stone-50 border-stone-200 text-stone-400'
            }
          }

          return (
            <button
              key={idx}
              onClick={() => onSelectAnswer(qId, idx)}
              disabled={isAnswered}
              className={`w-full text-left p-4 rounded-2xl border-2 transition-all flex items-center justify-between text-base sm:text-lg cursor-pointer ${buttonStyle}`}
            >
              <div className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-full bg-white/80 border border-stone-300 text-stone-600 flex items-center justify-center text-xs font-bold shrink-0">
                  {String.fromCharCode(65 + idx)}
                </span>
                <span>{optionText}</span>
              </div>

              {isAnswered && isSelected && (
                <span className="text-xl">
                  {feedback?.isCorrect ? '✅' : '💡'}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Feedback Message Card */}
      {isAnswered && feedback && (
        <div
          className={`p-4 sm:p-5 rounded-2xl border-2 animate-fade-in ${
            feedback.isCorrect
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
              : 'bg-amber-50 border-amber-300 text-amber-950'
          }`}
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl shrink-0">
              {feedback.isCorrect ? '🎉' : '🌱'}
            </span>
            <div>
              <p className="font-extrabold text-sm sm:text-base mb-1">
                {feedback.isCorrect ? 'You got it!' : "Nice try! Let's look at this part:"}
              </p>
              <p className="text-xs sm:text-sm font-medium leading-relaxed">
                {feedback.explanation}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Next or Finish Button */}
      {isAnswered && (
        <div className="pt-2 flex justify-end">
          {isLast ? (
            <button
              onClick={onFinish}
              disabled={submitting}
              className="px-6 py-3.5 bg-[#1A6B6B] hover:bg-[#145555] active:scale-[0.98] text-white font-bold rounded-2xl text-base shadow-sm transition-all flex items-center gap-2 cursor-pointer"
            >
              <span>{submitting ? 'Finishing...' : 'View Results'}</span>
              <span>🏆</span>
            </button>
          ) : (
            <button
              onClick={onNextQuestion}
              className="px-6 py-3.5 bg-[#1A6B6B] hover:bg-[#145555] active:scale-[0.98] text-white font-bold rounded-2xl text-base shadow-sm transition-all flex items-center gap-2 cursor-pointer"
            >
              <span>Next Question</span>
              <span>→</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}
