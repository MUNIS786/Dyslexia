import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { testAPI, planAPI } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { Button, ProgressBar, Spinner, Badge, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

const LEVEL_COLORS = { mild: 'green', moderate: 'amber', severe: 'red', none: 'teal' }
const LEVEL_EMOJI = { mild: '😊', moderate: '🙂', severe: '💪', none: '🌟' }

export default function ScreeningTest() {
  const { updateUser } = useAuth()
  const navigate = useNavigate()

  const [phase, setPhase] = useState('intro')
  const [questions, setQuestions] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState([])
  const [timeLeft, setTimeLeft] = useState(0)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState('')

  const timerRef = useRef(null)
  const startTimeRef = useRef(null)

 useEffect(() => {
  const loadQuestions = async () => {
    try {
      const d = await testAPI.questions()

      console.log("FULL API RESPONSE:", JSON.stringify(d, null, 2)) // 👈 important

      let parsed = []

      if (Array.isArray(d)) {
        parsed = d
      } else if (Array.isArray(d?.questions)) {
        parsed = d.questions
      } else if (Array.isArray(d?.data)) {
        parsed = d.data
      } else if (Array.isArray(d?.data?.questions)) {
        parsed = d.data.questions
      } else if (d?.sections) {
  parsed = Object.values(d.sections).flat()   // 🔥 THIS IS THE FIX
}

      console.log("PARSED QUESTIONS:", parsed)

      if (!parsed.length) {
        throw new Error("No questions found")
      }

      setQuestions(parsed)

    } catch (err) {
      console.error("LOAD ERROR:", err)
      setFetchError('Could not load questions. Please refresh.')
    }
  }

  loadQuestions()
}, [])

  const currentQ = questions[currentIdx]

  const clearTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const startTimer = useCallback((limit) => {
    clearTimer()
    setTimeLeft(limit)
    startTimeRef.current = Date.now()

    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current)
          return 0
        }
        return t - 1
      })
    }, 1000)
  }, [])

  useEffect(() => {
    if (phase !== 'test' || timeLeft !== 0 || !currentQ) return
    const timeTaken = currentQ.time_limit_seconds || 30
    recordAnswer(null, true, timeTaken)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft, phase, currentQ])

  useEffect(() => {
    if (phase === 'test' && currentQ) {
      startTimer(currentQ.time_limit_seconds || 30)
    }
    return clearTimer
  }, [currentIdx, phase, currentQ, startTimer])

  function recordAnswer(givenAnswer, autoFail = false, overrideTime = null) {
    clearTimer()

    const timeTaken = overrideTime ?? Math.round((Date.now() - startTimeRef.current) / 1000)
    const limit = currentQ.time_limit_seconds || 30

    const answer = {
      question_id: currentQ.id,
      question_type: currentQ.type || currentQ.question_type || 'unknown',
      given_answer: givenAnswer ?? '',
      correct: autoFail ? false : givenAnswer === currentQ.correct_answer,
      slow_response: timeTaken > limit,
      time_taken_seconds: timeTaken,
    }

    const newAnswers = [...answers, answer]
    setAnswers(newAnswers)

    if (currentIdx + 1 < questions.length) {
      setCurrentIdx((i) => i + 1)
    } else {
      submitTest(newAnswers)
    }
  }

  async function submitTest(finalAnswers) {
    setPhase('results')
    setLoading(true)

    try {
      const res = await testAPI.submit({
        answers: finalAnswers,
        method: 'combined',
        student_age: null,
        language: 'en',
      })

      setResults(res)
      updateUser({
        readingProfile: {
          type: res.type,
          level: res.level,
          recommendation: res.recommendation,
        },
      })
    } catch {
      toast.error('Could not submit test. Please try again.')
      setPhase('test')
    } finally {
      setLoading(false)
    }
  }

  async function handleGeneratePlan() {
    setPhase('generating')

    try {
      await planAPI.generate()
      toast.success('🎉 Your AI learning plan is ready!')
      navigate('/student/plan')
    } catch {
      toast.error('Could not generate plan.')
      navigate('/student')
    }
  }

  // ✅ INTRO SCREEN
  if (phase === 'intro') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-lg w-full text-center">

          <h1 className="text-3xl font-bold">Reading Screening</h1>

          {fetchError && (
            <Alert type="error" className="mt-4">
              {fetchError}
            </Alert>
          )}

          <Button
            className="w-full mt-6"
            onClick={() => setPhase('test')}
            disabled={questions.length === 0}
          >
            {fetchError
              ? 'Retry'
              : questions.length === 0
              ? 'Loading questions…'
              : 'Start Screening →'}
          </Button>
        </div>
      </div>
    )
  }

  // ✅ TEST SCREEN
  if (phase === 'test' && currentQ) {
    return (
      <div className="p-6">
        <h2>{currentQ.question}</h2>

        {currentQ.options?.map((opt, i) => (
          <button key={i} onClick={() => recordAnswer(opt)}>
            {opt}
          </button>
        ))}
      </div>
    )
  }

  // ✅ LOADING
  if (phase === 'generating' || (phase === 'results' && loading)) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spinner />
      </div>
    )
  }

  // ✅ RESULTS
  if (phase === 'results' && results) {
    return (
      <div className="p-6 text-center">
        <h2>Done!</h2>
        <Button onClick={handleGeneratePlan}>
          Generate Plan
        </Button>
      </div>
    )
  }

  return null
}