/**
 * frontend/src/features/reading/DifficultWords.jsx
 *
 * Child-friendly interactive popup when a learner clicks or taps any word.
 * Displays syllable breakdown, simple definition, example sentence,
 * and audio pronunciation via browser SpeechSynthesis.
 */
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui'

export default function DifficultWords({
  wordInfo,
  onClose,
  onPracticeAudio,
  ttsSupported = true,
  passageId = null,
}) {
  const navigate = useNavigate()
  if (!wordInfo) return null

  const { word, definition, phonetic, exampleSentence, syllables } = wordInfo

  const handleAskTutor = () => {
    onClose()
    const query = new URLSearchParams()
    if (word) query.set('word', word)
    if (passageId) query.set('passageId', passageId)
    navigate(`/student/tutor?${query.toString()}`)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl border border-slate-200 space-y-4"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="word-title"
      >
        {/* Header with audio button */}
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">🔍</span>
            <div>
              <h3 id="word-title" className="dyslexia-text text-xl sm:text-2xl font-extrabold text-slate-900 capitalize">
                {word}
              </h3>
              {phonetic && (
                <span className="text-xs text-slate-500 font-medium">/{phonetic}/</span>
              )}
            </div>
          </div>

          {ttsSupported && (
            <button
              type="button"
              onClick={() => onPracticeAudio(word)}
              className="p-2.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-xl border border-indigo-200 transition-all flex items-center gap-1.5 text-xs font-bold cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
              title="Listen to pronunciation"
              aria-label={`Listen to pronunciation of ${word}`}
            >
              <span aria-hidden="true">🔊</span>
              <span>Listen</span>
            </button>
          )}
        </div>

        {/* Syllable Breakdown */}
        {syllables && syllables.length > 0 && (
          <div className="bg-amber-50 rounded-2xl p-3 border border-amber-200">
            <span className="text-xs font-bold text-amber-900 uppercase block mb-1">
              Syllables:
            </span>
            <div className="flex flex-wrap items-center gap-1.5">
              {syllables.map((syl, i) => (
                <span
                  key={i}
                  className="bg-white px-2.5 py-1 rounded-xl text-sm font-extrabold text-amber-900 border border-amber-300 shadow-2xs font-mono"
                >
                  {syl}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Meaning / Definition */}
        <div className="space-y-1">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
            Meaning:
          </span>
          <p className="dyslexia-text text-sm sm:text-base text-slate-800 font-medium leading-relaxed bg-slate-50 p-3.5 rounded-2xl border border-slate-200">
            {definition}
          </p>
        </div>

        {/* Example Sentence */}
        {exampleSentence && (
          <div className="space-y-1">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
              Example in a sentence:
            </span>
            <p className="dyslexia-text text-xs sm:text-sm text-slate-700 italic bg-indigo-50/50 p-3 rounded-2xl border border-indigo-100">
              &ldquo;{exampleSentence}&rdquo;
            </p>
          </div>
        )}

        {/* Actions: Ask Tutor + Close */}
        <div className="flex items-center gap-2 pt-2">
          <Button
            variant="accent"
            onClick={handleAskTutor}
            className="flex-1 text-xs sm:text-sm"
            title="Ask Personal AI Tutor to explain more"
          >
            <span>🤖</span>
            <span>Ask AI Tutor</span>
          </Button>
          <Button
            variant="primary"
            onClick={onClose}
            className="flex-1 text-xs sm:text-sm"
          >
            Got It! 👍
          </Button>
        </div>
      </div>
    </div>
  )
}
