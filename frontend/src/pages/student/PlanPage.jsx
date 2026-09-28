import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { planAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, Spinner, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

export default function PlanPage() {
  const navigate = useNavigate()
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [openWeek, setOpenWeek] = useState(null)
  const [showParent, setShowParent] = useState(false)
  const [showTeacher, setShowTeacher] = useState(false)

  useEffect(() => {
    planAPI.get().then(setPlan).catch(() => toast.error('Could not load plan.')).finally(() => setLoading(false))
  }, [])

  const handleCheckAdapt = async () => {
    setChecking(true)
    try {
      const res = await planAPI.checkAdapt()
      if (res.adapted) {
        toast.success('🔄 Your plan has been updated!')
        const updated = await planAPI.get()
        setPlan(updated)
      } else {
        toast.success('✅ Your plan is up to date.')
      }
    } catch {
      toast.error('Could not check for updates.')
    } finally {
      setChecking(false)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )

  if (!plan?.hasPlan) {
    return (
      <div className="flex flex-col gap-5">
        <PageHeader icon="🧠" title="My Learning Plan" />
        <Alert type="warning">
          <p className="dyslexia-text font-semibold">You need to complete the screening test first.</p>
          <p className="dyslexia-text text-sm mt-1">After screening, we will create your personal plan.</p>
        </Alert>
        <Button onClick={() => navigate('/student/screening')}>Start Screening →</Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon="🧠"
        title="My Learning Plan"
        subtitle="Your personal roadmap to better reading."
        action={
          <Button variant="ghost" onClick={handleCheckAdapt} loading={checking} size="sm">
            🔄 Check for Updates
          </Button>
        }
      />

      {/* Summary card */}
      <div className="bg-gradient-to-br from-[#1A6B6B] to-[#2A8B8B] rounded-2xl p-5 text-white">
        <p className="dyslexia-text text-white/80 text-sm mb-1">Your plan summary</p>
        <p className="dyslexia-text text-lg font-semibold">
          {plan.summary || 'A personalised learning journey just for you.'}
        </p>
      </div>

      {/* Latest suggestion */}
      {plan.latestSuggestion && (
        <Alert type="info">
          <p className="dyslexia-text font-semibold">💡 Latest Suggestion</p>
          <p className="dyslexia-text text-sm mt-1">{plan.latestSuggestion}</p>
        </Alert>
      )}

      {/* Weekly goals */}
      {(plan.weeklyGoals || []).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-3">🎯 Weekly Goals</h2>
          <div className="flex flex-col gap-2">
            {plan.weeklyGoals.map((g, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="text-[#1A6B6B] font-bold shrink-0">{i + 1}.</span>
                <p className="dyslexia-text text-sm">{g}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 4-week plan accordion */}
      {(plan.plan || []).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-4">📅 4-Week Plan</h2>
          <div className="flex flex-col gap-2">
            {plan.plan.map((week) => (
              <div key={week.week} className="border border-[#E5E0D8] rounded-xl overflow-hidden">
                <button
                  onClick={() => setOpenWeek(openWeek === week.week ? null : week.week)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left
                    hover:bg-[#E0F2F2] transition-colors"
                >
                  <span className="dyslexia-text font-bold">
                    Week {week.week}: {week.focus}
                  </span>
                  <span className="text-[#1A6B6B]">{openWeek === week.week ? '▲' : '▼'}</span>
                </button>
                {openWeek === week.week && (
                  <div className="px-4 pb-4 bg-[#FFF8F0]">
                    <p className="dyslexia-text font-semibold text-sm text-[#1A6B6B] mb-2">
                      🎯 Goal: {week.goal}
                    </p>
                    <div className="flex flex-col gap-1.5">
                      {(week.activities || []).map((act, i) => (
                        <div key={i} className="flex gap-2">
                          <span className="dyslexia-text text-[#E8A020] shrink-0">•</span>
                          <p className="dyslexia-text text-sm">{act}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Accommodations */}
      {(plan.accommodations || []).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-3">♿ Accommodations</h2>
          <div className="flex flex-col gap-2">
            {plan.accommodations.map((a, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-green-500 shrink-0">✓</span>
                <p className="dyslexia-text text-sm">{a}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Parent tips toggle */}
      {(plan.parentTips || []).length > 0 && (
        <Card>
          <button
            onClick={() => setShowParent(!showParent)}
            className="w-full flex items-center justify-between dyslexia-text font-bold text-lg"
          >
            <span>👨‍👩‍👧 Parent Tips</span>
            <span className="text-[#1A6B6B]">{showParent ? '▲' : '▼'}</span>
          </button>
          {showParent && (
            <div className="mt-3 flex flex-col gap-2">
              {plan.parentTips.map((t, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-[#1A6B6B] shrink-0">•</span>
                  <p className="dyslexia-text text-sm">{t}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Teacher tips toggle */}
      {(plan.teacherTips || []).length > 0 && (
        <Card>
          <button
            onClick={() => setShowTeacher(!showTeacher)}
            className="w-full flex items-center justify-between dyslexia-text font-bold text-lg"
          >
            <span>👩‍🏫 Teacher Tips</span>
            <span className="text-[#1A6B6B]">{showTeacher ? '▲' : '▼'}</span>
          </button>
          {showTeacher && (
            <div className="mt-3 flex flex-col gap-2">
              {plan.teacherTips.map((t, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-[#1A6B6B] shrink-0">•</span>
                  <p className="dyslexia-text text-sm">{t}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
