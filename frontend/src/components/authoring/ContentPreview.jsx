import React, { useState } from 'react'

const TIER_COLORS = {
  1: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  2: 'bg-teal-100 text-teal-800 border-teal-300',
  3: 'bg-blue-100 text-blue-800 border-blue-300',
  4: 'bg-indigo-100 text-indigo-800 border-indigo-300',
  5: 'bg-purple-100 text-purple-800 border-purple-300',
}

const TIER_NAMES = {
  1: 'Foundation',
  2: 'Early Phonics',
  3: 'Guided Fluency',
  4: 'Confident Reader',
  5: 'Advanced Comprehension',
}

export default function ContentPreview({ content }) {
  const [selectedWord, setSelectedWord] = useState(null)

  if (!content) return null

  const {
    title,
    text,
    difficulty = 1,
    language = 'en',
    wordCount,
    estimatedMinutes = 2,
    gradeBand = 'Grade 1-2',
    topics = [],
    vocabulary = [],
    questions = [],
  } = content

  const tierColor = TIER_COLORS[difficulty] || TIER_COLORS[1]
  const tierName = TIER_NAMES[difficulty] || 'Foundation'

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header Bar */}
      <div className="bg-gradient-to-r from-[#1A6B6B] to-[#258585] p-6 text-white">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${tierColor} bg-white/90`}>
              Tier {difficulty}: {tierName}
            </span>
            <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-white/20 text-white uppercase tracking-wider">
              {language}
            </span>
            {gradeBand && (
              <span className="text-xs px-2 py-0.5 rounded bg-white/10 text-white/90">
                {gradeBand}
              </span>
            )}
          </div>
          <div className="text-xs text-white/80 flex items-center gap-3">
            <span>⏱ ~{estimatedMinutes} min read</span>
            <span>📝 {wordCount || text?.split(/\s+/).filter(Boolean).length || 0} words</span>
          </div>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white">{title || 'Untitled Passage'}</h2>
        {topics.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {topics.map((t, idx) => (
              <span key={idx} className="text-[11px] bg-white/15 px-2 py-0.5 rounded-full text-white/90">
                #{t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="p-6 space-y-6">
        {/* Story Body */}
        <div className="p-5 bg-amber-50/40 rounded-xl border border-amber-100">
          <p
            className="text-gray-800 text-lg leading-relaxed whitespace-pre-line font-medium"
            style={{ fontFamily: 'OpenDyslexic, Lexend, sans-serif', letterSpacing: '0.04em' }}
          >
            {text || 'No passage text written yet.'}
          </p>
        </div>

        {/* Vocabulary Support */}
        {vocabulary.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2">
              <span>📚 Difficult-Word & Vocabulary Cards ({vocabulary.length})</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {vocabulary.map((vocab, idx) => {
                const isSelected = selectedWord?.word === vocab.word
                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedWord(isSelected ? null : vocab)}
                    className={`cursor-pointer p-3.5 rounded-xl border transition-all text-left ${
                      isSelected
                        ? 'border-[#1A6B6B] bg-[#1A6B6B]/5 shadow-sm'
                        : 'border-gray-200 hover:border-gray-300 bg-gray-50/70'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-gray-900 text-base">{vocab.word}</span>
                      {vocab.phonetic && (
                        <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-mono">
                          /{vocab.phonetic}/
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">{vocab.definition}</p>
                    {vocab.exampleSentence && (
                      <p className="text-[11px] text-gray-400 italic mt-1.5">
                        "{vocab.exampleSentence}"
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Comprehension Questions */}
        {questions.length > 0 && (
          <div className="space-y-3 pt-3 border-t border-gray-100">
            <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2">
              <span>❓ Comprehension Check ({questions.length})</span>
            </h4>
            <div className="space-y-4">
              {questions.map((q, idx) => (
                <div key={idx} className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2.5">
                  <p className="text-sm font-bold text-gray-900">
                    <span className="text-[#1A6B6B] mr-1.5">Q{idx + 1}.</span>
                    {q.question}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {q.options?.map((opt, optIdx) => {
                      const isCorrect = q.correctAnswer === optIdx || q.correctAnswer === opt
                      return (
                        <div
                          key={optIdx}
                          className={`px-3 py-2 rounded-lg text-xs font-medium border flex items-center justify-between ${
                            isCorrect
                              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                              : 'bg-white border-gray-200 text-gray-700'
                          }`}
                        >
                          <span>{opt}</span>
                          {isCorrect && (
                            <span className="text-[10px] bg-emerald-200 text-emerald-900 px-1.5 py-0.5 rounded font-bold">
                              Correct Answer
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                  {q.explanation && (
                    <p className="text-xs text-gray-500 italic bg-white p-2 rounded border border-gray-100">
                      💡 <strong>Explanation:</strong> {q.explanation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
