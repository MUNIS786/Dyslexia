import React, { useState } from 'react'

const TIER_DESCRIPTIONS = {
  1: 'Tier 1: Foundation (CVC words, short sentences, phonics)',
  2: 'Tier 2: Early Phonics (Digraphs, blends, decodable text)',
  3: 'Tier 3: Guided Fluency (Multisyllabic words, story rhythm)',
  4: 'Tier 4: Confident Reader (Longer paragraphs, descriptive vocabulary)',
  5: 'Tier 5: Advanced Comprehension (Complex vocabulary, inference)',
}

export default function ContentEditor({
  initialContent = {},
  onSaveDraft,
  onSubmitReview,
  onValidate,
  isSaving = false,
  isSubmitting = false,
}) {
  const [title, setTitle] = useState(initialContent.title || '')
  const [text, setText] = useState(initialContent.text || '')
  const [language, setLanguage] = useState(initialContent.language || 'en')
  const [difficulty, setDifficulty] = useState(initialContent.difficulty || 1)
  const [domain, setDomain] = useState(initialContent.domain || 'reading_comprehension')
  const [gradeBand, setGradeBand] = useState(initialContent.gradeBand || 'Grade 1-2')
  const [topicsStr, setTopicsStr] = useState((initialContent.topics || []).join(', '))
  const [estimatedMinutes, setEstimatedMinutes] = useState(initialContent.estimatedMinutes || '')

  // Vocabulary list
  const [vocabulary, setVocabulary] = useState(initialContent.vocabulary || [])

  // Comprehension questions list
  const [questions, setQuestions] = useState(initialContent.questions || [])

  // Word count & estimate calculations
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const autoEstMins = Math.max(1, Math.round(wordCount / 65))

  const handleAddWord = () => {
    setVocabulary([
      ...vocabulary,
      { word: '', definition: '', phonetic: '', exampleSentence: '', syllables: [] },
    ])
  }

  const handleUpdateWord = (index, field, value) => {
    const updated = [...vocabulary]
    updated[index] = { ...updated[index], [field]: value }
    setVocabulary(updated)
  }

  const handleRemoveWord = (index) => {
    setVocabulary(vocabulary.filter((_, idx) => idx !== index))
  }

  const handleAddQuestion = () => {
    setQuestions([
      ...questions,
      {
        questionId: `q-${questions.length + 1}`,
        question: '',
        options: ['', '', ''],
        correctAnswer: 0,
        explanation: '',
        questionType: 'detail',
      },
    ])
  }

  const handleUpdateQuestion = (qIdx, field, value) => {
    const updated = [...questions]
    updated[qIdx] = { ...updated[qIdx], [field]: value }
    setQuestions(updated)
  }

  const handleUpdateOption = (qIdx, optIdx, value) => {
    const updated = [...questions]
    const opts = [...(updated[qIdx].options || [])]
    opts[optIdx] = value
    updated[qIdx] = { ...updated[qIdx], options: opts }
    setQuestions(updated)
  }

  const handleAddOption = (qIdx) => {
    const updated = [...questions]
    const opts = [...(updated[qIdx].options || []), '']
    updated[qIdx] = { ...updated[qIdx], options: opts }
    setQuestions(updated)
  }

  const handleRemoveOption = (qIdx, optIdx) => {
    const updated = [...questions]
    const opts = (updated[qIdx].options || []).filter((_, i) => i !== optIdx)
    let currentAns = updated[qIdx].correctAnswer
    if (typeof currentAns === 'number' && currentAns >= opts.length) {
      currentAns = Math.max(0, opts.length - 1)
    }
    updated[qIdx] = { ...updated[qIdx], options: opts, correctAnswer: currentAns }
    setQuestions(updated)
  }

  const handleRemoveQuestion = (qIdx) => {
    setQuestions(questions.filter((_, idx) => idx !== qIdx))
  }

  const buildPayload = () => {
    const topics = topicsStr
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
    return {
      title: title.trim(),
      text: text.trim(),
      language,
      difficulty: parseInt(difficulty, 10),
      domain,
      gradeBand: gradeBand.trim(),
      topics,
      estimatedMinutes: estimatedMinutes ? parseInt(estimatedMinutes, 10) : autoEstMins,
      vocabulary: vocabulary.map((v) => ({
        ...v,
        word: (v.word || '').trim(),
        definition: (v.definition || '').trim(),
        phonetic: (v.phonetic || '').trim() || null,
        exampleSentence: (v.exampleSentence || '').trim() || null,
      })),
      questions: questions.map((q) => ({
        ...q,
        question: (q.question || '').trim(),
        options: (q.options || []).map((o) => o.trim()).filter(Boolean),
        correctAnswer: parseInt(q.correctAnswer, 10) || 0,
        explanation: (q.explanation || '').trim(),
      })),
    }
  }

  const onSave = (e) => {
    e.preventDefault()
    onSaveDraft(buildPayload())
  }

  const onSubmit = (e) => {
    e.preventDefault()
    onSubmitReview(buildPayload())
  }

  const onCheckValidation = (e) => {
    e.preventDefault()
    if (onValidate) {
      onValidate(buildPayload())
    }
  }

  return (
    <form className="space-y-6 bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
      {/* Title & Metadata Row */}
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            Passage Title <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Sam the Orange Cat"
            className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-gray-900 font-medium"
            required
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              Language <span className="text-rose-500">*</span>
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-gray-900 text-sm font-medium bg-white"
            >
              <option value="en">English (en)</option>
              <option value="hi">Hindi (हिन्दी - hi)</option>
              <option value="mr">Marathi (मराठी - mr)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              Difficulty Tier <span className="text-rose-500">*</span>
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(parseInt(e.target.value, 10))}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-gray-900 text-sm font-medium bg-white"
            >
              <option value={1}>Tier 1 - Foundation</option>
              <option value={2}>Tier 2 - Early Phonics</option>
              <option value={3}>Tier 3 - Guided Fluency</option>
              <option value={4}>Tier 4 - Confident Reader</option>
              <option value={5}>Tier 5 - Advanced</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
              Grade Band
            </label>
            <input
              type="text"
              value={gradeBand}
              onChange={(e) => setGradeBand(e.target.value)}
              placeholder="e.g. Grade 1-2"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-gray-900 text-sm"
            />
          </div>
        </div>

        <p className="text-xs text-gray-500 italic">
          💡 {TIER_DESCRIPTIONS[difficulty]}
        </p>
      </div>

      {/* Story Text Body */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
            Story / Passage Body Text <span className="text-rose-500">*</span>
          </label>
          <div className="text-xs text-gray-500 space-x-3">
            <span>
              <strong>{wordCount}</strong> words
            </span>
            <span>
              ~<strong>{estimatedMinutes || autoEstMins}</strong> min read
            </span>
          </div>
        </div>
        <textarea
          rows={7}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write or paste your dyslexia-friendly passage here. Use simple sentences, clear rhythm, and phonetic clarity..."
          className="w-full p-4 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-gray-900 font-normal leading-relaxed"
          style={{ fontFamily: 'OpenDyslexic, Lexend, sans-serif' }}
          required
        />
        {language !== 'en' && (
          <p className="text-xs text-amber-600 mt-1">
            Note: Devanagari script is verified automatically for Hindi and Marathi content.
          </p>
        )}
      </div>

      {/* Topics and Tags */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            Topics / Themes (comma separated)
          </label>
          <input
            type="text"
            value={topicsStr}
            onChange={(e) => setTopicsStr(e.target.value)}
            placeholder="animals, pets, nature, friendship"
            className="w-full px-3 py-2.5 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-sm text-gray-900"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
            Override Estimated Minutes (optional)
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={estimatedMinutes}
            onChange={(e) => setEstimatedMinutes(e.target.value)}
            placeholder={`Auto: ${autoEstMins} mins`}
            className="w-full px-3 py-2.5 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1A6B6B] text-sm text-gray-900"
          />
        </div>
      </div>

      {/* Vocabulary Annotations Builder */}
      <div className="border-t border-gray-200 pt-5 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h4 className="font-bold text-gray-900 text-sm">Difficult-Word & Vocabulary Annotations</h4>
            <p className="text-xs text-gray-500">Provide child-friendly definitions and syllable phonetics.</p>
          </div>
          <button
            type="button"
            onClick={handleAddWord}
            className="text-xs font-bold px-3 py-1.5 rounded-lg bg-teal-50 text-[#1A6B6B] border border-teal-200 hover:bg-teal-100 transition-colors"
          >
            + Add Word
          </button>
        </div>

        {vocabulary.length === 0 && (
          <p className="text-xs text-gray-400 italic bg-gray-50 p-3 rounded-lg text-center">
            No vocabulary words added yet. Adding 1–3 target words helps build decoding stamina.
          </p>
        )}

        {vocabulary.map((vocab, vIdx) => (
          <div key={vIdx} className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-3 relative">
            <button
              type="button"
              onClick={() => handleRemoveWord(vIdx)}
              className="absolute top-2.5 right-2.5 text-xs text-rose-500 hover:text-rose-700 font-bold px-1.5 py-0.5 rounded"
              title="Remove word"
            >
              ✕ Remove
            </button>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-16">
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Word</label>
                <input
                  type="text"
                  value={vocab.word}
                  onChange={(e) => handleUpdateWord(vIdx, 'word', e.target.value)}
                  placeholder="e.g. purrs"
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 bg-white text-gray-900 font-bold"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Phonetic / Syllables</label>
                <input
                  type="text"
                  value={vocab.phonetic || ''}
                  onChange={(e) => handleUpdateWord(vIdx, 'phonetic', e.target.value)}
                  placeholder="e.g. purz"
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 bg-white text-gray-900"
                />
              </div>
            </div>
            <div>
              <label className="block text-[11px] font-bold text-gray-600 mb-1">Simple Definition</label>
              <input
                type="text"
                value={vocab.definition}
                onChange={(e) => handleUpdateWord(vIdx, 'definition', e.target.value)}
                placeholder="Child-friendly explanation..."
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 bg-white text-gray-900"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Comprehension Questions Builder */}
      <div className="border-t border-gray-200 pt-5 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h4 className="font-bold text-gray-900 text-sm">Comprehension Questions</h4>
            <p className="text-xs text-gray-500">Add multiple-choice questions to assess recall and understanding.</p>
          </div>
          <button
            type="button"
            onClick={handleAddQuestion}
            className="text-xs font-bold px-3 py-1.5 rounded-lg bg-teal-50 text-[#1A6B6B] border border-teal-200 hover:bg-teal-100 transition-colors"
          >
            + Add Question
          </button>
        </div>

        {questions.length === 0 && (
          <p className="text-xs text-gray-400 italic bg-gray-50 p-3 rounded-lg text-center">
            No comprehension questions added yet. Adding 1–2 questions is recommended.
          </p>
        )}

        {questions.map((q, qIdx) => (
          <div key={qIdx} className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 relative">
            <button
              type="button"
              onClick={() => handleRemoveQuestion(qIdx)}
              className="absolute top-2.5 right-2.5 text-xs text-rose-500 hover:text-rose-700 font-bold px-1.5 py-0.5 rounded"
              title="Remove question"
            >
              ✕ Remove
            </button>
            <div className="pr-16">
              <label className="block text-[11px] font-bold text-gray-600 mb-1">Question #{qIdx + 1}</label>
              <input
                type="text"
                value={q.question}
                onChange={(e) => handleUpdateQuestion(qIdx, 'question', e.target.value)}
                placeholder="e.g. What color is Sam the cat?"
                className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 bg-white text-gray-900 font-semibold"
              />
            </div>

            {/* Answer Options */}
            <div className="space-y-2">
              <label className="block text-[11px] font-bold text-gray-600">Answer Options & Correct Choice</label>
              {q.options?.map((opt, optIdx) => (
                <div key={optIdx} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`correct-opt-${qIdx}`}
                    checked={q.correctAnswer === optIdx}
                    onChange={() => handleUpdateQuestion(qIdx, 'correctAnswer', optIdx)}
                    className="h-4 w-4 text-[#1A6B6B] focus:ring-[#1A6B6B]"
                    title="Mark as correct answer"
                  />
                  <input
                    type="text"
                    value={opt}
                    onChange={(e) => handleUpdateOption(qIdx, optIdx, e.target.value)}
                    placeholder={`Option ${optIdx + 1}`}
                    className="flex-1 px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 bg-white text-gray-900"
                  />
                  {q.options.length > 2 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveOption(qIdx, optIdx)}
                      className="text-gray-400 hover:text-rose-500 text-xs px-1"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              {q.options?.length < 5 && (
                <button
                  type="button"
                  onClick={() => handleAddOption(qIdx)}
                  className="text-[11px] text-[#1A6B6B] font-bold hover:underline"
                >
                  + Add another option
                </button>
              )}
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-600 mb-1">Educational Explanation</label>
              <input
                type="text"
                value={q.explanation || ''}
                onChange={(e) => handleUpdateQuestion(qIdx, 'explanation', e.target.value)}
                placeholder="Explain why this answer is correct in encouraging terms..."
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 bg-white text-gray-900"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Form Action Buttons */}
      <div className="pt-4 border-t border-gray-200 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onCheckValidation}
          className="px-4 py-2 text-xs font-bold rounded-xl bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors border border-gray-300"
        >
          🔍 Run Quality Check
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onSave}
            disabled={isSaving}
            className="px-5 py-2.5 text-xs font-bold rounded-xl bg-white text-gray-800 border border-gray-300 hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50"
          >
            {isSaving ? 'Saving Draft...' : '💾 Save Draft'}
          </button>

          <button
            type="button"
            onClick={onSubmit}
            disabled={isSubmitting}
            className="px-6 py-2.5 text-xs font-bold rounded-xl bg-[#1A6B6B] text-white hover:bg-[#145252] transition-colors shadow-sm disabled:opacity-50"
          >
            {isSubmitting ? 'Submitting...' : '🚀 Submit for Review'}
          </button>
        </div>
      </div>
    </form>
  )
}
