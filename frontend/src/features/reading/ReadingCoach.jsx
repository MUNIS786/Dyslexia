/**
 * frontend/src/features/reading/ReadingCoach.jsx
 *
 * Main DyslexAid V2 Adaptive Reading Coach Orchestrator.
 * Seamlessly manages the complete adaptive practice lifecycle:
 * Recommendation -> Reading Ergonomics -> Word Support -> Comprehension -> Adaptive Progression
 */
import React from 'react'
import { useReadingCoach } from '../../hooks/v2/useReadingCoach'
import ReadingRecommendation from './ReadingRecommendation'
import ReadingControls from './ReadingControls'
import ReadingProgress from './ReadingProgress'
import ReadingPassage from './ReadingPassage'
import DifficultWords from './DifficultWords'
import ComprehensionQuestion from './ComprehensionQuestion'
import ReadingSessionResult from './ReadingSessionResult'
import { Spinner } from '../../components/ui'
import { useNavigate } from 'react-router-dom'

export default function ReadingCoach() {
  const navigate = useNavigate()
  const {
    loading,
    error,
    recommendation,
    allPassages,
    activePassage,
    setActivePassage,
    sessionResult,
    submitting,
    step,
    setStep,

    // Controls
    readingMode,
    setReadingMode,
    font,
    setFont,
    fontSize,
    setFontSize,
    lineSpacing,
    setLineSpacing,
    letterSpacing,
    setLetterSpacing,
    readingWidth,
    setReadingWidth,
    bgColor,
    setBgColor,

    // Segment & Words
    currentSegmentIndex,
    setCurrentSegmentIndex,
    difficultWords,
    practicedWords,
    activeWordInfo,
    setActiveWordInfo,
    handleWordClick,
    practiceWordAudio,

    // Timer & Telemetry
    durationSeconds,

    // TTS
    speaking,
    ttsSupported,
    playPassageTTS,
    stopPassageTTS,

    // Comprehension
    currentQuestionIndex,
    setCurrentQuestionIndex,
    userAnswers,
    questionFeedback,
    selectComprehensionAnswer,
    finishReadingGoToComprehension,

    // Actions
    startReading,
    completeSession,
    resetToNextReading,
    refetchRecommendation,
  } = useReadingCoach()

  if (loading && !activePassage) {
    return (
      <div className="min-h-[400px] flex flex-col items-center justify-center gap-3">
        <Spinner size="lg" />
        <p className="text-sm font-bold text-stone-600">
          Preparing your personalized reading story...
        </p>
      </div>
    )
  }

  if (error && !activePassage) {
    return (
      <div className="max-w-md mx-auto text-center p-8 bg-white rounded-3xl border border-stone-200 space-y-4">
        <span className="text-4xl block">📖</span>
        <h3 className="text-lg font-bold text-stone-900">Reading Coach Ready</h3>
        <p className="text-xs text-stone-600">{error}</p>
        <button
          onClick={refetchRecommendation}
          className="px-5 py-2.5 bg-[#1A6B6B] text-white rounded-xl font-bold text-sm cursor-pointer"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Active Word Support Modal (Clickable Difficult Words) */}
      {activeWordInfo && (
        <DifficultWords
          wordInfo={activeWordInfo}
          onClose={() => setActiveWordInfo(null)}
          onPracticeAudio={practiceWordAudio}
          ttsSupported={ttsSupported}
        />
      )}

      {/* STAGE 1: Recommendation Preview */}
      {step === 'preview' && (
        <ReadingRecommendation
          recommendation={recommendation}
          activePassage={activePassage}
          allPassages={allPassages}
          onSelectPassage={(p) => setActivePassage(p)}
          onStartReading={startReading}
          loading={loading}
        />
      )}

      {/* STAGE 2: Active Reading Passage */}
      {step === 'reading' && (
        <div>
          <ReadingProgress
            step={step}
            durationSeconds={durationSeconds}
            wordCount={activePassage?.wordCount || 0}
            difficultWordsCount={difficultWords.length}
            practicedWordsCount={practicedWords.length}
          />

          <ReadingControls
            readingMode={readingMode}
            setReadingMode={setReadingMode}
            font={font}
            setFont={setFont}
            fontSize={fontSize}
            setFontSize={setFontSize}
            lineSpacing={lineSpacing}
            setLineSpacing={setLineSpacing}
            letterSpacing={letterSpacing}
            setLetterSpacing={setLetterSpacing}
            readingWidth={readingWidth}
            setReadingWidth={setReadingWidth}
            bgColor={bgColor}
            setBgColor={setBgColor}
            ttsSupported={ttsSupported}
          />

          <ReadingPassage
            passage={activePassage}
            readingMode={readingMode}
            font={font}
            fontSize={fontSize}
            lineSpacing={lineSpacing}
            letterSpacing={letterSpacing}
            readingWidth={readingWidth}
            bgColor={bgColor}
            currentSegmentIndex={currentSegmentIndex}
            setCurrentSegmentIndex={setCurrentSegmentIndex}
            onWordClick={handleWordClick}
            onFinishReading={finishReadingGoToComprehension}
            speaking={speaking}
            ttsSupported={ttsSupported}
            onPlayTTS={playPassageTTS}
            onStopTTS={stopPassageTTS}
          />
        </div>
      )}

      {/* STAGE 3: Comprehension Questions */}
      {step === 'comprehension' && (
        <div>
          <ReadingProgress
            step={step}
            durationSeconds={durationSeconds}
            wordCount={activePassage?.wordCount || 0}
            difficultWordsCount={difficultWords.length}
            practicedWordsCount={practicedWords.length}
          />

          <ComprehensionQuestion
            questions={activePassage?.questions || []}
            currentIndex={currentQuestionIndex}
            userAnswers={userAnswers}
            questionFeedback={questionFeedback}
            onSelectAnswer={selectComprehensionAnswer}
            onNextQuestion={() => setCurrentQuestionIndex((prev) => prev + 1)}
            onFinish={completeSession}
            submitting={submitting}
          />
        </div>
      )}

      {/* STAGE 4: Celebratory Results & Adaptive Decision */}
      {step === 'result' && (
        <div>
          <ReadingProgress
            step={step}
            durationSeconds={durationSeconds}
            wordCount={activePassage?.wordCount || 0}
            difficultWordsCount={difficultWords.length}
            practicedWordsCount={practicedWords.length}
          />

          <ReadingSessionResult
            result={sessionResult}
            activePassage={activePassage}
            onTryNextReading={resetToNextReading}
            onGoHome={() => navigate('/student')}
          />
        </div>
      )}
    </div>
  )
}
