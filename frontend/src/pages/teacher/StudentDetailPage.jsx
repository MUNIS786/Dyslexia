import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { teacherAPI, assignmentsAPI } from '../../api/client'
import { learnerV2API } from '../../api/v2/client'
import { Card, Button, Badge, PageHeader, ProgressBar, StatCard, Spinner, Modal } from '../../components/ui'
import toast from 'react-hot-toast'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function StudentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [v2Profile, setV2Profile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [gradeModal, setGradeModal] = useState(null)
  const [gradeForm, setGradeForm] = useState({ score: '', feedback: '' })
  const [grading, setGrading] = useState(false)
  const [lessonModal, setLessonModal] = useState(false)
  const [lessonForm, setLessonForm] = useState({ subject: '', language: 'en' })
  const [lessonResult, setLessonResult] = useState(null)
  const [generatingLesson, setGeneratingLesson] = useState(false)

  useEffect(() => {
    Promise.allSettled([
      teacherAPI.studentDetail(id),
      learnerV2API.getStudentProfile(id),
    ]).then(([detailRes, profRes]) => {
      if (detailRes.status === 'fulfilled') {
        setData(detailRes.value)
      } else {
        toast.error('Could not load student.')
      }
      if (profRes.status === 'fulfilled' && profRes.value?.status === 'ok') {
        setV2Profile(profRes.value.profile)
      }
    }).finally(() => setLoading(false))
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

      {/* V2 Learner Intelligence Profile */}
      {v2Profile && (
        <Card className="border border-teal-200 bg-gradient-to-b from-teal-50/40 to-white">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-2xl bg-[#1A6B6B] text-white flex items-center justify-center text-xl shadow-sm">
                🌟
              </div>
              <div>
                <h2 className="dyslexia-text font-bold text-lg text-gray-900 flex items-center gap-2">
                  Learner Intelligence Profile (V2)
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold border border-emerald-300">
                    Active
                  </span>
                </h2>
                <p className="text-xs text-gray-500">
                  Multidimensional cognitive telemetry & educational accommodation profile
                </p>
              </div>
            </div>

            {v2Profile.learning_level && (
              <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-teal-200 shadow-sm">
                <span className="text-xs font-bold text-teal-800">
                  Level {v2Profile.learning_level.level}: {v2Profile.learning_level.name}
                </span>
                {v2Profile.confidence?.overall != null && (
                  <span className="text-[11px] text-gray-500 border-l border-gray-200 pl-2">
                    {Math.round(v2Profile.confidence.overall * 100)}% Confidence
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="p-3.5 bg-white rounded-2xl border border-gray-200/80 mb-5 text-xs text-gray-700 leading-relaxed">
            <strong className="text-gray-900">Level Summary:</strong> {v2Profile.learning_level?.description || 'Foundational reading stage.'}
            {v2Profile.learning_level?.inputs?.composite_score != null && (
              <span className="block mt-1 text-gray-500">
                Composite Educational Score: {Math.round(v2Profile.learning_level.inputs.composite_score)}/100 &bull; Evaluated over {v2Profile.learning_level.inputs.domains_evaluated || 10} domains
              </span>
            )}
          </div>

          {/* Strengths & Practice Areas Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            {/* Strengths */}
            <div className="bg-emerald-50/60 rounded-2xl p-4 border border-emerald-200">
              <h3 className="font-bold text-sm text-emerald-950 flex items-center gap-1.5 mb-2.5">
                <span>⭐</span> Identified Strengths ({v2Profile.strengths?.length || 0})
              </h3>
              {v2Profile.strengths && v2Profile.strengths.length > 0 ? (
                <div className="space-y-2">
                  {v2Profile.strengths.map((s, idx) => (
                    <div key={idx} className="bg-white p-2.5 rounded-xl border border-emerald-100 text-xs shadow-2xs">
                      <div className="flex justify-between font-bold text-gray-900 mb-0.5">
                        <span>{s.friendly_name || s.domain}</span>
                        <span className="text-emerald-700">{Math.round(s.score)}%</span>
                      </div>
                      <p className="text-gray-600 text-[11px] leading-snug">{s.description}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-emerald-700 italic">Strengths will populate upon screening.</p>
              )}
            </div>

            {/* Areas to Practice */}
            <div className="bg-blue-50/60 rounded-2xl p-4 border border-blue-200">
              <h3 className="font-bold text-sm text-blue-950 flex items-center gap-1.5 mb-2.5">
                <span>🎯</span> Recommended Practice Areas ({v2Profile.areas_for_practice?.length || 0})
              </h3>
              {v2Profile.areas_for_practice && v2Profile.areas_for_practice.length > 0 ? (
                <div className="space-y-2">
                  {v2Profile.areas_for_practice.map((a, idx) => (
                    <div key={idx} className="bg-white p-2.5 rounded-xl border border-blue-100 text-xs shadow-2xs">
                      <div className="flex justify-between font-bold text-gray-900 mb-0.5">
                        <span>{a.friendly_name || a.domain}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                          a.priority === 'high' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {a.priority} priority
                        </span>
                      </div>
                      <p className="text-gray-600 text-[11px] leading-snug">{a.description}</p>
                      {a.suggested_activity_type && (
                        <p className="text-[10px] text-teal-700 mt-1 font-semibold">
                          Recommended activity: {a.suggested_activity_type.replace(/_/g, ' ')}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-blue-700 italic">Practice areas will populate upon screening.</p>
              )}
            </div>
          </div>

          {/* 12-Domain Breakdown */}
          {v2Profile.domain_scores && Object.keys(v2Profile.domain_scores).length > 0 && (
            <div className="bg-white rounded-2xl p-4 border border-gray-200 mb-5">
              <h3 className="font-bold text-sm text-gray-900 mb-3 flex items-center justify-between">
                <span>📊 12-Domain Educational Telemetry</span>
                <span className="text-xs font-normal text-gray-500">0–100 Normalized Educational Scale</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(v2Profile.domain_scores).map(([dKey, dScore]) => {
                  const interp = v2Profile.domain_interpretations?.[dKey] || {}
                  const scoreVal = Math.round(dScore || 0)
                  const label = interp.label || (scoreVal >= 75 ? 'Strength' : scoreVal >= 60 ? 'Progressing' : scoreVal >= 40 ? 'Developing' : 'Needs Practice')
                  const color = scoreVal >= 75 ? 'bg-teal-500' : scoreVal >= 60 ? 'bg-blue-500' : scoreVal >= 40 ? 'bg-amber-500' : 'bg-rose-500'

                  return (
                    <div key={dKey} className="p-2.5 rounded-xl bg-gray-50/80 border border-gray-100 space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-gray-800 truncate" title={dKey}>
                          {interp.technical_name || dKey.replace(/_/g, ' ')}
                        </span>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span className="text-[10px] font-bold text-gray-600">{label}</span>
                          <span className="font-extrabold text-gray-900 w-8 text-right">{scoreVal}%</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                        <div className={`h-full rounded-full ${color}`} style={{ width: `${scoreVal}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Cognitive Indicators & Goals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            {v2Profile.cognitive_indicators && (
              <div className="bg-white p-3.5 rounded-2xl border border-gray-200 text-xs space-y-1.5">
                <p className="font-bold text-gray-900 mb-1">Cognitive Indicators</p>
                <div className="flex justify-between text-gray-600">
                  <span>Working Memory:</span>
                  <span className="font-semibold text-gray-900 capitalize">{v2Profile.cognitive_indicators.working_memory?.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Visual Processing:</span>
                  <span className="font-semibold text-gray-900 capitalize">{v2Profile.cognitive_indicators.visual_processing?.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Auditory Processing:</span>
                  <span className="font-semibold text-gray-900 capitalize">{v2Profile.cognitive_indicators.auditory_processing?.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex justify-between text-gray-600">
                  <span>Processing Speed:</span>
                  <span className="font-semibold text-gray-900 capitalize">{v2Profile.cognitive_indicators.processing_speed?.replace(/_/g, ' ')}</span>
                </div>
              </div>
            )}

            {v2Profile.goals && v2Profile.goals.length > 0 && (
              <div className="bg-white p-3.5 rounded-2xl border border-gray-200 text-xs space-y-2">
                <p className="font-bold text-gray-900">Current Student Goals</p>
                <div className="space-y-1.5">
                  {v2Profile.goals.map((g, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-gray-700">
                      <span className={`w-4 h-4 rounded flex items-center justify-center text-[10px] ${g.completed ? 'bg-emerald-500 text-white font-bold' : 'border border-gray-300'}`}>
                        {g.completed ? '✓' : ''}
                      </span>
                      <span className={g.completed ? 'line-through text-gray-400' : 'text-gray-800 font-medium'}>
                        {g.title}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="p-3 bg-amber-50/70 border border-amber-200/80 rounded-xl text-[11px] text-amber-900 leading-relaxed">
            <strong>Educational Indicator Note:</strong> This intelligence profile is intended to assist educators with personalized reading instruction and accommodations. It does not represent a medical or clinical diagnosis.
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
