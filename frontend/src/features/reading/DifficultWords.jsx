/**
 * frontend/src/features/reading/DifficultWords.jsx
 *
 * Child-friendly interactive popup when a learner clicks or taps any word.
 * Displays syllable breakdown, simple definition, example sentence,
 * and audio pronunciation via browser SpeechSynthesis.
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-fade-in">
      <div
        className="bg-white rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl border-2 border-teal-500 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with audio button */}
        <div className="flex items-center justify-between gap-3 border-b border-stone-100 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🔍</span>
            <div>
              <h3 className="text-xl sm:text-2xl font-extrabold text-stone-900 capitalize">
                {word}
              </h3>
              {phonetic && (
                <span className="text-xs text-stone-500 font-medium">/{phonetic}/</span>
              )}
            </div>
          </div>

          {ttsSupported && (
            <button
              onClick={() => onPracticeAudio(word)}
              className="p-3 bg-teal-50 hover:bg-teal-100 text-teal-800 rounded-2xl border border-teal-200 transition-all flex items-center gap-1.5 text-xs font-bold cursor-pointer"
              title="Listen to pronunciation"
            >
              <span>🔊</span>
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
                  className="bg-white px-2.5 py-1 rounded-xl text-sm font-extrabold text-amber-900 border border-amber-300 shadow-2xs"
                >
                  {syl}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Meaning / Definition */}
        <div className="space-y-1">
          <span className="text-xs font-bold text-stone-500 uppercase tracking-wide">
            Meaning:
          </span>
          <p className="text-sm sm:text-base text-stone-800 font-medium leading-relaxed bg-stone-50 p-3.5 rounded-2xl border border-stone-200">
            {definition}
          </p>
        </div>

        {/* Example Sentence */}
        {exampleSentence && (
          <div className="space-y-1">
            <span className="text-xs font-bold text-stone-500 uppercase tracking-wide">
              Example in a sentence:
            </span>
            <p className="text-xs sm:text-sm text-stone-700 italic bg-teal-50/60 p-3 rounded-2xl border border-teal-100">
              "{exampleSentence}"
            </p>
          </div>
        )}

        {/* Actions: Ask Tutor + Close */}
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={handleAskTutor}
            className="flex-1 py-3 bg-amber-500 hover:bg-amber-600 active:scale-[0.98] text-white font-bold rounded-2xl text-xs sm:text-sm transition-all shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
            title="Ask Personal AI Tutor to explain more"
          >
            <span>🤖</span>
            <span>Ask AI Tutor</span>
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-3 bg-[#1A6B6B] hover:bg-[#145555] active:scale-[0.98] text-white font-bold rounded-2xl text-xs sm:text-sm transition-all shadow-xs cursor-pointer"
          >
            Got It! 👍
          </button>
        </div>
      </div>
    </div>
  )
}

