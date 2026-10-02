/**
 * frontend/src/hooks/v2/useReadingCoach.js — React Hook for DyslexAid Reading Coach.
 *
 * Coordinates:
 * - Adaptive passage recommendations & catalog fetching
 * - Session initiation, live reading timer, words read tracking
 * - Reading ergonomics: font, size, line-spacing, letter-spacing, width, theme
 * - Display modes: Standard, Focus (chunk-by-chunk), Guided (sentence focus), Listen (browser TTS)
 * - Clickable difficult-word interaction with pronunciation and child-friendly definitions
 * - Step-by-step comprehension questions with encouraging immediate feedback
 * - Server-side session completion and Phase 3 adaptive ZPD progression
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { readingV2API } from '../../api/v2/client'
import { useSpeechReading } from './useSpeechReading'
import toast from 'react-hot-toast'

export function useReadingCoach() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [allPassages, setAllPassages] = useState([])
  const [activePassage, setActivePassage] = useState(null)
  const [session, setSession] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [sessionResult, setSessionResult] = useState(null)

  // Speech Reading Hook
  const speech = useSpeechReading()

  // Reading coach stage: 'preview' | 'reading' | 'comprehension' | 'result'
  const [step, setStep] = useState('preview')

  // Reading ergonomics & accessibility controls
  const [readingMode, setReadingMode] = useState('standard') // 'standard' | 'focus' | 'guided' | 'listen' | 'speech'
  const [font, setFont] = useState('OpenDyslexic')
  const [fontSize, setFontSize] = useState(20)
  const [lineSpacing, setLineSpacing] = useState(2.0)
  const [letterSpacing, setLetterSpacing] = useState(0.1)
  const [paragraphSpacing, setParagraphSpacing] = useState(1.8)
  const [readingWidth, setReadingWidth] = useState('normal') // 'narrow' | 'normal' | 'wide'
  const [bgColor, setBgColor] = useState('#FFF8F0')

  // Interactive Difficult Words
  const [difficultWords, setDifficultWords] = useState([])
  const [practicedWords, setPracticedWords] = useState([])
  const [activeWordInfo, setActiveWordInfo] = useState(null)

  // Guided / Focus mode segment tracking
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0)

  // Timer & words tracking
  const [durationSeconds, setDurationSeconds] = useState(0)
  const timerRef = useRef(null)

  // Comprehension state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [userAnswers, setUserAnswers] = useState({})
  const [questionFeedback, setQuestionFeedback] = useState({})
  const [hintsUsed, setHintsUsed] = useState(0)
  const [replaysUsed, setReplaysUsed] = useState(0)

  // TTS audio playback state
  const [speaking, setSpeaking] = useState(false)
  const [currentTTSWordIndex, setCurrentTTSWordIndex] = useState(-1)
  const utterRef = useRef(null)
  const ttsSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

  // Fetch initial recommendation and available passages
  const fetchInitialData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [recRes, passagesRes] = await Promise.all([
        readingV2API.getRecommendation().catch((err) => {
          console.warn('Could not fetch recommendation:', err)
          return null
        }),
        readingV2API.getPassages().catch(() => ({ passages: [] })),
      ])

      if (recRes && recRes.recommendedPassage) {
        setRecommendation(recRes)
        setActivePassage(recRes.recommendedPassage)
      } else if (passagesRes && passagesRes.passages && passagesRes.passages.length > 0) {
        const first = passagesRes.passages[0]
        setRecommendation({
          recommendedPassage: first,
          difficulty: first.difficulty || 1,
          domain: first.domain || 'reading_comprehension',
          reason: "Here is a wonderful story tailored for your reading practice!",
          confidence: 0.85,
        })
        setActivePassage(first)
      }
      setAllPassages(passagesRes?.passages || [])
    } catch (err) {
      console.error('Error in useReadingCoach init:', err)
      setError(err?.response?.data?.detail || 'Could not load reading passages.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInitialData()
  }, [fetchInitialData])

  // Timer management during active reading
  useEffect(() => {
    if (step === 'reading' || step === 'comprehension') {
      timerRef.current = setInterval(() => {
        setDurationSeconds((prev) => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [step])

  // Stop browser speech on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  // Start reading session
  const startReading = useCallback(async (passageToRead = null) => {
    const targetPassage = passageToRead || activePassage
    if (!targetPassage) return

    setLoading(true)
    try {
      const res = await readingV2API.startSession({
        passageId: targetPassage.passageId,
        readingMode,
        language: targetPassage.language || 'en',
      })
      setSession(res.session)
      setActivePassage(targetPassage)
      setStep('reading')
      setDurationSeconds(0)
      setDifficultWords([])
      setPracticedWords([])
      setUserAnswers({})
      setQuestionFeedback({})
      setCurrentQuestionIndex(0)
      setCurrentSegmentIndex(0)
      setHintsUsed(0)
      setReplaysUsed(0)
    } catch (err) {
      console.error('Failed to start session:', err)
      // Offline fallback: allow local reading practice without crashing
      setSession({
        sessionId: `offline-${Date.now()}`,
        passageId: targetPassage.passageId,
        difficulty: targetPassage.difficulty || 1,
        startedAt: Math.floor(Date.now() / 1000),
      })
      setActivePassage(targetPassage)
      setStep('reading')
      setDurationSeconds(0)
      toast('Starting offline reading mode 📖')
    } finally {
      setLoading(false)
    }
  }, [activePassage, readingMode])

  // Word interactions (Definitions & Audio Pronunciation)
  const handleWordClick = useCallback((wordText) => {
    if (!wordText || !activePassage) return
    const cleanWord = wordText.replace(/[^\w\u0900-\u097F]/g, '').toLowerCase()
    if (!cleanWord) return

    setDifficultWords((prev) => (prev.includes(cleanWord) ? prev : [...prev, cleanWord]))

    // Find in predefined passage vocabulary
    const vocabMatch = (activePassage.vocabulary || []).find(
      (v) => (v.word || '').toLowerCase() === cleanWord
    )

    if (vocabMatch) {
      setActiveWordInfo(vocabMatch)
    } else {
      // Safe fallback if not in predefined list
      setActiveWordInfo({
        word: wordText,
        definition: "Tap 'Listen' below to hear how this word sounds!",
        phonetic: null,
        exampleSentence: null,
        syllables: [cleanWord],
      })
    }
  }, [activePassage])

  const practiceWordAudio = useCallback((wordText) => {
    if (!ttsSupported || !wordText) return
    const cleanWord = wordText.replace(/[^\w\u0900-\u097F]/g, '')
    setPracticedWords((prev) => (prev.includes(cleanWord) ? prev : [...prev, cleanWord]))

    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(cleanWord)
    utter.rate = 0.85
    let ttsLang = 'en-IN'
    if (activePassage?.language === 'mr') ttsLang = 'mr-IN'
    else if (activePassage?.language === 'hi') ttsLang = 'hi-IN'
    utter.lang = ttsLang
    window.speechSynthesis.speak(utter)
  }, [ttsSupported, activePassage])

  // Browser TTS for Passage (Listen Mode)
  const playPassageTTS = useCallback((textToSpeak) => {
    if (!ttsSupported || !textToSpeak) {
      toast('Speech synthesis is not available on this browser.')
      return
    }
    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(textToSpeak)
    utter.rate = 0.85
    let ttsLang = 'en-IN'
    if (activePassage?.language === 'mr') ttsLang = 'mr-IN'
    else if (activePassage?.language === 'hi') ttsLang = 'hi-IN'
    utter.lang = ttsLang

    utter.onboundary = (e) => {
      if (e.name === 'word') {
        setCurrentTTSWordIndex((prev) => prev + 1)
      }
    }
    utter.onend = () => {
      setSpeaking(false)
      setCurrentTTSWordIndex(-1)
    }
    utter.onerror = () => {
      setSpeaking(false)
      setCurrentTTSWordIndex(-1)
    }

    setSpeaking(true)
    setReplaysUsed((prev) => prev + 1)
    utterRef.current = utter
    window.speechSynthesis.speak(utter)
  }, [ttsSupported, activePassage])

  const stopPassageTTS = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    setSpeaking(false)
    setCurrentTTSWordIndex(-1)
  }, [])

  // Transition from reading to comprehension questions
  const finishReadingGoToComprehension = useCallback(() => {
    stopPassageTTS()
    if (activePassage?.questions && activePassage.questions.length > 0) {
      setStep('comprehension')
      setCurrentQuestionIndex(0)
    } else {
      // No questions on passage: finish immediately
      completeSession()
    }
  }, [activePassage, stopPassageTTS])

  // Answer comprehension question
  const selectComprehensionAnswer = useCallback((questionId, optionIndex) => {
    if (userAnswers[questionId] !== undefined) return // already answered

    const question = activePassage?.questions?.find((q) => q.questionId === questionId)
    if (!question) return

    const correct =
      typeof question.correctAnswer === 'number'
        ? optionIndex === question.correctAnswer
        : String(optionIndex) === String(question.correctAnswer) ||
          question.options[optionIndex]?.toLowerCase() === String(question.correctAnswer).toLowerCase()

    setUserAnswers((prev) => ({ ...prev, [questionId]: optionIndex }))
    setQuestionFeedback((prev) => ({
      ...prev,
      [questionId]: {
        isCorrect: correct,
        explanation: question.explanation || (correct ? "Great job!" : "Let's review this together."),
      },
    }))
  }, [activePassage, userAnswers])

  // Complete session and calculate server-side performance
  const completeSession = useCallback(async () => {
    if (!session || !activePassage) return
    setSubmitting(true)
    stopPassageTTS()

    const payload = {
      sessionId: session.sessionId,
      durationSeconds,
      readingMode,
      wordsRead: activePassage.wordCount || 50,
      comprehensionAnswers: userAnswers,
      difficultWords,
      practicedWords,
      hintsUsed,
      replaysUsed,
      completed: true,
      skipped: false,
    }

    try {
      const res = await readingV2API.completeSession(payload)
      setSessionResult(res)
      setStep('result')
      if (res.adaptation?.tierChanged) {
        if (res.adaptation.newTier > res.adaptation.previousTier) {
          toast.success(`🎉 Level Up! You're now reading at Level ${res.adaptation.newTier}!`)
        }
      } else {
        toast.success('Reading completed! Great work! 🌟')
      }
    } catch (err) {
      console.warn('Backend completion failed, calculating offline score:', err)
      // Client-side fallback computation for offline mode
      const totalQ = activePassage.questions?.length || 1
      let correctQ = 0
      Object.entries(questionFeedback).forEach(([_, f]) => {
        if (f.isCorrect) correctQ++
      })
      const compAcc = Math.round((correctQ / totalQ) * 100)
      const offlineRes = {
        status: 'ok',
        sessionId: session.sessionId,
        readingScore: 85.0,
        comprehensionScore: compAcc,
        overallScore: Math.round(0.6 * compAcc + 30.0),
        correctCount: correctQ,
        totalQuestions: totalQ,
        wordsRead: activePassage.wordCount || 50,
        durationSeconds,
        practicedWordsCount: practicedWords.length,
        nextStepMessage: compAcc >= 70 ? "Great job! You're ready for your next reading!" : "Good practice! Every reading makes your brain stronger!",
        currentTier: activePassage.difficulty || 1,
        streak: 1,
      }
      setSessionResult(offlineRes)
      setStep('result')
    } finally {
      setSubmitting(false)
    }
  }, [session, activePassage, durationSeconds, readingMode, userAnswers, difficultWords, practicedWords, hintsUsed, replaysUsed, stopPassageTTS, questionFeedback])

  // Speech Recognition Callbacks
  const handleStartSpeech = useCallback(() => {
    speech.startListening(activePassage?.language || 'en-US')
  }, [speech, activePassage])

  const handleStopSpeech = useCallback(async () => {
    if (!session || !activePassage) return null
    return await speech.stopListeningAndAnalyze({
      sessionId: session.sessionId,
      passageId: activePassage.passageId,
    })
  }, [session, activePassage, speech])

  const handleResetSpeech = useCallback(() => {
    speech.resetSpeech()
  }, [speech])

  // Reset to preview next reading recommendation
  const resetToNextReading = useCallback(async () => {
    setStep('preview')
    setSession(null)
    setSessionResult(null)
    speech.resetSpeech()
    await fetchInitialData()
  }, [fetchInitialData, speech])

  return {
    loading,
    error,
    recommendation,
    allPassages,
    activePassage,
    setActivePassage,
    session,
    sessionResult,
    submitting,
    step,
    setStep,

    // Ergonomics & Controls
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
    paragraphSpacing,
    setParagraphSpacing,
    readingWidth,
    setReadingWidth,
    bgColor,
    setBgColor,

    // Guided & Focus segments
    currentSegmentIndex,
    setCurrentSegmentIndex,

    // Word support
    difficultWords,
    practicedWords,
    activeWordInfo,
    setActiveWordInfo,
    handleWordClick,
    practiceWordAudio,

    // Timer & Telemetry
    durationSeconds,
    hintsUsed,
    setHintsUsed,
    replaysUsed,

    // TTS Audio
    speaking,
    currentTTSWordIndex,
    ttsSupported,
    playPassageTTS,
    stopPassageTTS,

    // Speech Read Aloud (Phase 5)
    isSpeechSupported: speech.isSpeechSupported,
    speechState: speech.speechState,
    speechTranscript: speech.transcript,
    speechInterimTranscript: speech.interimTranscript,
    speechSpeakingSeconds: speech.speakingSeconds,
    speechDetectedWordCount: speech.detectedWordCount,
    speechAnalysis: speech.analysisResult,
    speechErrorMessage: speech.errorMessage,
    onStartSpeech: handleStartSpeech,
    onStopSpeech: handleStopSpeech,
    onResetSpeech: handleResetSpeech,

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
    refetchRecommendation: fetchInitialData,
  }
}

