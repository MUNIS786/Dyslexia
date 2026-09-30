/**
 * frontend/src/features/reading/ReadingPassage.jsx
 *
 * Dyslexia-friendly accessible text display:
 * - Standard mode (paragraph view)
 * - Focus mode (one sentence / chunk at a time to reduce visual clutter)
 * - Guided reading mode (active sentence focus with dimmed surroundings)
 * - Listen mode (browser Web Speech API audio with live playback highlighting)
 * - Interactive word tap for definitions, phonetic respelling, and audio pronunciation
 */
import React, { useMemo } from 'react'
import SpeechListeningIndicator from './SpeechListeningIndicator'
import SpeechReadingResult from './SpeechReadingResult'

export default function ReadingPassage({
  passage,
  readingMode = 'standard',
  font = 'OpenDyslexic',
  fontSize = 20,
  lineSpacing = 2.0,
  letterSpacing = 0.1,
  readingWidth = 'normal',
  bgColor = '#FFF8F0',
  currentSegmentIndex = 0,
  setCurrentSegmentIndex,
  onWordClick,
  onFinishReading,
  // TTS props
  speaking = false,
  ttsSupported = true,
  onPlayTTS,
  onStopTTS,
  // Speech Read Aloud props
  speechState = 'ready',
  speakingSeconds = 0,
  detectedWordCount = 0,
  interimTranscript = '',
  speechAnalysis = null,
  isSpeechSupported = true,
  speechErrorMessage = null,
  onStartSpeech,
  onStopSpeech,
  onResetSpeech,
  onProceedFromSpeech,
}) {
  if (!passage || !passage.text) return null

  // Predefined vocabulary lookup
  const vocabMap = useMemo(() => {
    const map = new Set()
    ;(passage.vocabulary || []).forEach((v) => {
      map.add(v.word.toLowerCase())
    })
    return map
  }, [passage])

  // Split into sentences for Guided & Focus modes
  const sentences = useMemo(() => {
    return passage.text
      .replace(/([.?!])\s*(?=[A-Z])/g, '$1|')
      .split('|')
      .map((s) => s.trim())
      .filter(Boolean)
  }, [passage.text])

  // Split text into paragraphs for Standard mode
  const paragraphs = useMemo(() => {
    return passage.text.split('\n\n').filter(Boolean)
  }, [passage.text])

  // Width container class
  const widthClass = {
    narrow: 'max-w-xl',
    normal: 'max-w-3xl',
    wide: 'max-w-4xl',
  }[readingWidth] || 'max-w-3xl'

  // Render individual words as interactive clickable spans
  const renderInteractiveWords = (textSegment) => {
    const tokens = textSegment.split(/(\s+)/)
    return tokens.map((token, i) => {
      if (/^\s+$/.test(token)) {
        return <span key={i}>{token}</span>
      }
      const clean = token.replace(/[^\w]/g, '').toLowerCase()
      const isVocabulary = vocabMap.has(clean)

      return (
        <span
          key={i}
          onClick={() => onWordClick(token)}
          className={`inline-block px-0.5 rounded-sm transition-all cursor-pointer select-text hover:bg-amber-200/70 hover:scale-105 active:bg-amber-300 ${
            isVocabulary
              ? 'border-b-2 border-dashed border-teal-600 font-semibold text-teal-950'
              : 'hover:text-teal-900'
          }`}
          title="Click to see definition and pronunciation"
        >
          {token}
        </span>
      )
    })
  }

  return (
    <div className={`mx-auto ${widthClass} space-y-6`}>
      {/* Listen Mode Audio Control Banner */}
      {readingMode === 'listen' && ttsSupported && (
        <div className="bg-teal-50 border border-teal-200 rounded-2xl p-4 flex items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🔊</span>
            <span className="text-xs sm:text-sm font-bold text-teal-900">
              {speaking ? 'Reading aloud...' : 'Listen to story'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {speaking ? (
              <button
                onClick={onStopTTS}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer flex items-center gap-1.5"
              >
                <span>⏹️</span>
                <span>Pause</span>
              </button>
            ) : (
              <button
                onClick={() => onPlayTTS(passage.text)}
                className="px-4 py-2 bg-[#1A6B6B] hover:bg-[#145555] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer flex items-center gap-1.5"
              >
                <span>▶️</span>
                <span>Play Aloud</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Read Aloud Speech Practice Mode Banner & Live Indicator */}
      {readingMode === 'speech' && (
        <SpeechListeningIndicator
          speechState={speechState}
          speakingSeconds={speakingSeconds}
          detectedWordCount={detectedWordCount}
          interimTranscript={interimTranscript}
          onStart={onStartSpeech}
          onStop={onStopSpeech}
          onReset={onResetSpeech}
          isSpeechSupported={isSpeechSupported}
          errorMessage={speechErrorMessage}
        />
      )}

      {/* Speech Analysis Result Card (shown when analyzed) */}
      {readingMode === 'speech' && speechAnalysis && (
        <SpeechReadingResult
          analysis={speechAnalysis.analysis}
          feedback={speechAnalysis.childFriendlyFeedback}
          nextAction={speechAnalysis.nextActionSuggestion}
          onProceedToQuestions={onProceedFromSpeech || onFinishReading}
          onReRead={onResetSpeech}
          onReadSilently={() => onFinishReading()}
        />
      )}

      {/* Main Text Container */}
      <div
        className="rounded-3xl border border-stone-200 shadow-sm p-6 sm:p-10 transition-colors"
        style={{
          backgroundColor: bgColor,
          fontFamily: font === 'OpenDyslexic' ? 'OpenDyslexic, Lexend, sans-serif' : font,
          fontSize: `${fontSize}px`,
          lineHeight: lineSpacing,
          letterSpacing: `${letterSpacing}em`,
        }}
      >
        <h2 className="text-2xl sm:text-3xl font-extrabold text-stone-900 mb-6 border-b border-stone-200/60 pb-3">
          {passage.title}
        </h2>

        {/* 1. FOCUS MODE: One sentence/chunk at a time */}
        {readingMode === 'focus' ? (
          <div className="space-y-8 min-h-[180px] flex flex-col justify-between">
            <div className="p-6 bg-white rounded-2xl border-2 border-teal-400 shadow-sm text-stone-900">
              {renderInteractiveWords(sentences[currentSegmentIndex] || sentences[0])}
            </div>

            {/* Stepper Buttons */}
            <div className="flex items-center justify-between gap-3 pt-4 border-t border-stone-200/60 text-sm">
              <button
                onClick={() => setCurrentSegmentIndex((prev) => Math.max(0, prev - 1))}
                disabled={currentSegmentIndex === 0}
                className="px-4 py-2 bg-white border border-stone-300 rounded-xl font-bold disabled:opacity-30 cursor-pointer"
              >
                ← Previous
              </button>
              <span className="text-xs font-bold text-stone-500">
                Part {currentSegmentIndex + 1} of {sentences.length}
              </span>
              <button
                onClick={() =>
                  setCurrentSegmentIndex((prev) =>
                    Math.min(sentences.length - 1, prev + 1)
                  )
                }
                disabled={currentSegmentIndex === sentences.length - 1}
                className="px-4 py-2 bg-[#1A6B6B] text-white rounded-xl font-bold disabled:opacity-30 cursor-pointer"
              >
                Next →
              </button>
            </div>
          </div>
        ) : readingMode === 'guided' ? (
          /* 2. GUIDED READING: Highlights current sentence, dims others */
          <div className="space-y-3">
            {sentences.map((sent, i) => {
              const isCurrent = i === currentSegmentIndex
              return (
                <div
                  key={i}
                  onClick={() => setCurrentSegmentIndex(i)}
                  className={`p-3 rounded-2xl transition-all cursor-pointer ${
                    isCurrent
                      ? 'bg-amber-100/80 border-2 border-amber-400 font-medium text-stone-950 shadow-xs'
                      : 'opacity-40 hover:opacity-80 text-stone-700'
                  }`}
                >
                  {renderInteractiveWords(sent)}
                </div>
              )
            })}
          </div>
        ) : (
          /* 3. STANDARD / LISTEN MODE: Paragraph view */
          <div className="space-y-6 text-stone-800 font-normal">
            {paragraphs.map((p, idx) => (
              <p key={idx}>{renderInteractiveWords(p)}</p>
            ))}
          </div>
        )}
      </div>

      {/* Done Reading Button */}
      <div className="flex justify-end pt-2">
        <button
          onClick={onFinishReading}
          className="w-full sm:w-auto px-8 py-4 bg-[#1A6B6B] hover:bg-[#145555] active:scale-[0.98] text-white font-bold text-lg rounded-2xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>I'm Done Reading</span>
          <span>→</span>
        </button>
      </div>
    </div>
  )
}
