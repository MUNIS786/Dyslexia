import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { testAPI, planAPI } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { Button, ProgressBar, Spinner, Badge, Alert, Card } from '../../components/ui'
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
      <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50/50">
        <Card className="max-w-lg w-full text-center p-6 sm:p-8 space-y-5">
          <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-3xl mx-auto shadow-xs">
            🧠
          </div>
          <div>
            <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold text-slate-900">
              Reading Screening
            </h1>
            <p className="dyslexia-text text-slate-500 text-sm mt-2 leading-relaxed">
              This quick evaluation helps understand your unique reading patterns, strengths, and optimal learning style.
            </p>
          </div>

          {fetchError && (
            <Alert type="error" className="mt-4 text-left">
              {fetchError}
            </Alert>
          )}

          <Button
            className="w-full mt-4"
            onClick={() => setPhase('test')}
            disabled={questions.length === 0}
          >
            {fetchError
              ? 'Retry'
              : questions.length === 0
              ? 'Loading questions…'
              : 'Start Screening →'}
          </Button>
        </Card>
      </div>
    )
  }

  // ✅ TEST SCREEN
  if (phase === 'test' && currentQ) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50/50">
        <div className="max-w-2xl w-full space-y-4">
          <div className="flex items-center justify-between text-sm font-bold text-slate-700 dyslexia-text">
            <span>
              Question {currentIdx + 1} of {questions.length}
            </span>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold ${
                timeLeft <= 5 ? 'bg-rose-100 text-rose-700 animate-pulse' : 'bg-slate-100 text-slate-700'
              }`}
            >
              ⏱ {timeLeft}s
            </span>
          </div>

          <ProgressBar value={currentIdx + 1} max={questions.length} color="indigo" showValue={false} />

          <Card className="p-6 sm:p-8 space-y-6">
            <h2 className="dyslexia-text text-xl sm:text-2xl font-bold text-slate-900 leading-relaxed">
              {currentQ.question}
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              {currentQ.options?.map((opt, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => recordAnswer(opt)}
                  className="w-full text-left p-4 rounded-xl border-2 border-slate-200 hover:border-indigo-600 hover:bg-indigo-50/50 active:scale-[0.99] transition-all font-semibold text-slate-800 dyslexia-text min-h-[52px] flex items-center justify-between group shadow-2xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
                >
                  <span className="leading-snug">{opt}</span>
                  <span className="w-6 h-6 rounded-full border border-slate-300 text-xs flex items-center justify-center text-slate-400 group-hover:border-indigo-600 group-hover:text-indigo-600 group-hover:bg-white shrink-0 ml-2 font-mono">
                    {String.fromCharCode(65 + i)}
                  </span>
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    )
  }

  // ✅ LOADING
  if (phase === 'generating' || (phase === 'results' && loading)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <Spinner size="lg" color="primary" />
          <p className="dyslexia-text font-bold text-slate-700">Analyzing responses & building profile…</p>
        </div>
      </div>
    )
  }

  // ✅ RESULTS
  if (phase === 'results' && results) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50/50">
        <Card className="max-w-lg w-full text-center p-6 sm:p-8 space-y-6">
          <div className="text-5xl">
            {LEVEL_EMOJI[results.level] || '🎉'}
          </div>
          <div>
            <h2 className="dyslexia-text text-2xl font-extrabold text-slate-900">Screening Complete!</h2>
            <p className="dyslexia-text text-slate-500 text-sm mt-1">
              {results.recommendation || 'Your personal reading profile is ready.'}
            </p>
          </div>
          <div className="flex justify-center gap-2">
            <Badge color={LEVEL_COLORS[results.level] || 'teal'}>
              Support Level: {results.level || 'Standard'}
            </Badge>
          </div>
          <div className="pt-2 flex flex-col sm:flex-row gap-3">
            <Button className="flex-1" onClick={handleGeneratePlan}>
              Generate AI Learning Plan →
            </Button>
            <Button variant="outline" onClick={() => navigate('/student')}>
              Go to Dashboard
            </Button>
          </div>
        </Card>
      </div>
    )
  }

  return null
}