import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { teacherAPI, assignmentsAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, ProgressBar, StatCard, Spinner, Modal } from '../../components/ui'
import toast from 'react-hot-toast'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function StudentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [gradeModal, setGradeModal] = useState(null)
  const [gradeForm, setGradeForm] = useState({ score: '', feedback: '' })
  const [grading, setGrading] = useState(false)
  const [lessonModal, setLessonModal] = useState(false)
  const [lessonForm, setLessonForm] = useState({ subject: '', language: 'en' })
  const [lessonResult, setLessonResult] = useState(null)
  const [generatingLesson, setGeneratingLesson] = useState(false)

  useEffect(() => {
    teacherAPI.studentDetail(id)
      .then(setData)
      .catch(() => toast.error('Could not load student.'))
      .finally(() => setLoading(false))
  }, [id])

  const handleGrade = async () => {
    if (!gradeForm.score) return
    setGrading(true)
    try {
      await assignmentsAPI.grade({
        submissionId: gradeModal.id,
        score: parseInt(gradeForm.score),
        feedback: gradeForm.feedback,
      })
      toast.success('✅ Grade submitted!')
      setGradeModal(null)
      setGradeForm({ score: '', feedback: '' })
      // Refresh
      const updated = await teacherAPI.studentDetail(id)
      setData(updated)
    } catch {
      toast.error('Could not submit grade.')
    } finally {
      setGrading(false)
    }
  }

  const handleLessonPlan = async () => {
    setGeneratingLesson(true)
    try {
      const res = await teacherAPI.lessonPlan({
        studentName: data.student.name,
        profile: data.student.profile || '',
        subject: lessonForm.subject,
        language: lessonForm.language,
      })
      setLessonResult(res.plan)
    } catch {
      toast.error('Could not generate lesson plan.')
    } finally {
      setGeneratingLesson(false)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )
  if (!data) return null

  const { student, progress, plan, submissions } = data
  const weeklyVals = Object.values(progress?.weeklyActivity || {})
  const maxWeekly = Math.max(...weeklyVals, 1)
  const comprScores = (progress?.comprehensionScores || []).slice(-8)

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon="👤"
        title={student.name}
        subtitle={student.email}
        action={
          <Button variant="ghost" onClick={() => navigate('/teacher/students')}>← Back</Button>
        }
      />

      {/* Profile badges */}
      <div className="flex flex-wrap gap-2">
        {student.profile && <Badge color="teal">{student.profile.replace('_', ' ')}</Badge>}
        {student.profileLevel && <Badge color="amber">{student.profileLevel}</Badge>}
        {student.status && (
          <Badge color={
            student.status === 'on_track' ? 'green'
            : student.status === 'needs_attention' ? 'red'
            : student.status === 'progressing' ? 'amber' : 'gray'
          }>
            {student.status.replace('_', ' ')}
          </Badge>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard icon="🎯" label="Comprehension" value={`${progress?.avgComprehension || 0}%`} color="teal" />
        <StatCard icon="🔥" label="Streak" value={`${student.streak || 0} days`} color="amber" />
        <StatCard icon="📄" label="Docs Scanned" value={progress?.docsScanned || 0} color="teal" />
        <StatCard icon="⭐" label="Words Mastered" value={progress?.wordsMastered || 0} color="green" />
      </div>

      {/* Comprehension trend */}
      {comprScores.length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-4">🎯 Comprehension Trend</h2>
          <div className="flex items-end gap-2 h-24">
            {comprScores.map((score, i) => {
              const color = score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-[#E8A020]' : 'bg-red-400'
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex items-end" style={{ height: '64px' }}>
                    <div
                      className={`w-full rounded-t-lg ${color}`}
                      style={{ height: `${Math.max(score, 4)}%` }}
                      title={`${score}%`}
                    />
                  </div>
                  <p className="dyslexia-text text-xs text-gray-400">{score}%</p>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Weekly activity */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">📅 Weekly Activity</h2>
        <div className="flex items-end gap-2 h-24">
          {DAYS.map((day, i) => {
            const val = weeklyVals[i] || 0
            return (
              <div key={day} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex items-end" style={{ height: '64px' }}>
                  <div
                    className="w-full rounded-t-lg bg-[#1A6B6B]"
                    style={{ height: `${Math.max(Math.round((val / maxWeekly) * 100), val > 0 ? 8 : 2)}%` }}
                    title={`${val}min`}
                  />
                </div>
                <p className="dyslexia-text text-xs text-gray-400">{day}</p>
              </div>
            )
          })}
        </div>
      </Card>

      {/* AI Plan summary */}
      {plan && (
        <Card className="bg-gradient-to-br from-[#1A6B6B]/10 to-[#2A8B8B]/5 border-[#1A6B6B]/20">
          <h2 className="dyslexia-text font-bold text-lg mb-2">🧠 AI Learning Plan</h2>
          <p className="dyslexia-text text-sm text-gray-600">{plan.summary}</p>
          {(plan.weeklyGoals || []).slice(0, 2).map((g, i) => (
            <p key={i} className="dyslexia-text text-sm mt-1">• {g}</p>
          ))}
        </Card>
      )}

      {/* Generate lesson plan */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-3">📋 Generate Lesson Plan</h2>
        <div className="flex flex-col gap-3">
          <input
            className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
              focus:outline-none focus:border-[#1A6B6B]"
            placeholder="Subject (e.g. Reading, Science)"
            value={lessonForm.subject}
            onChange={(e) => setLessonForm((f) => ({ ...f, subject: e.target.value }))}
          />
          <Button
            onClick={() => { setLessonModal(true); if (lessonForm.subject) handleLessonPlan() }}
            disabled={!lessonForm.subject}
          >
            🤖 Generate Lesson Plan
          </Button>
        </div>
      </Card>

      {/* Submissions */}
      {(submissions || []).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-4">📝 Assignment Submissions</h2>
          <div className="flex flex-col gap-3">
            {submissions.map((sub) => (
              <div
                key={sub.id}
                className="p-3 rounded-xl border border-[#E5E0D8] bg-[#FFF8F0]"
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1">
                    <p className="dyslexia-text font-semibold text-sm">{sub.assignmentTitle}</p>
                    <div className="flex gap-2 mt-1 flex-wrap">
                      {sub.score != null && (
                        <Badge color="teal">{sub.score} pts</Badge>
                      )}
                      {sub.graded ? (
                        <Badge color="green">✓ Graded</Badge>
                      ) : (
                        <Badge color="amber">Pending grade</Badge>
                      )}
                      <span className="dyslexia-text text-xs text-gray-400">
                        {new Date(sub.submittedAt || sub.createdAt).toLocaleDateString('en-IN')}
                      </span>
                    </div>
                    {sub.feedback && (
                      <p className="dyslexia-text text-xs text-gray-500 mt-1">💬 {sub.feedback}</p>
                    )}
                  </div>
                  {!sub.graded && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => { setGradeModal(sub); setGradeForm({ score: '', feedback: '' }) }}
                    >
                      Grade
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Grade modal */}
      <Modal open={!!gradeModal} onClose={() => setGradeModal(null)} title="📝 Grade Submission">
        <div className="flex flex-col gap-4">
          <p className="dyslexia-text font-semibold">{gradeModal?.assignmentTitle}</p>
          <input
            type="number"
            className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
              focus:outline-none focus:border-[#1A6B6B]"
            placeholder="Score (e.g. 85)"
            value={gradeForm.score}
            onChange={(e) => setGradeForm((f) => ({ ...f, score: e.target.value }))}
          />
          <textarea
            className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
              focus:outline-none focus:border-[#1A6B6B] resize-none"
            rows={3}
            placeholder="Feedback for student (optional)"
            value={gradeForm.feedback}
            onChange={(e) => setGradeForm((f) => ({ ...f, feedback: e.target.value }))}
          />
          <div className="flex gap-3">
            <Button variant="ghost" onClick={() => setGradeModal(null)} className="flex-1">Cancel</Button>
            <Button onClick={handleGrade} loading={grading} disabled={!gradeForm.score} className="flex-1">
              Submit Grade
            </Button>
          </div>
        </div>
      </Modal>

      {/* Lesson plan modal */}
      <Modal open={lessonModal} onClose={() => { setLessonModal(false); setLessonResult(null) }} title="📋 Lesson Plan">
        {generatingLesson ? (
          <div className="flex flex-col items-center py-8 gap-3">
            <Spinner size="lg" />
            <p className="dyslexia-text text-[#1A6B6B]">Generating personalised lesson plan…</p>
          </div>
        ) : lessonResult ? (
          <div className="flex flex-col gap-3">
            <div className="bg-[#FFF8F0] rounded-xl p-4 max-h-80 overflow-y-auto">
              <pre className="dyslexia-text text-sm whitespace-pre-wrap">{lessonResult}</pre>
            </div>
            <Button onClick={() => { setLessonModal(false); setLessonResult(null) }}>Close</Button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="dyslexia-text text-sm text-gray-500">
              Generating a lesson plan for {student.name} ({lessonForm.subject})…
            </p>
            <Button onClick={handleLessonPlan} loading={generatingLesson}>Generate Now</Button>
          </div>
        )}
      </Modal>
    </div>
  )
}
