import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { progressAPI, tasksAPI, planAPI, classroomAPI } from '../../api/client'
import { Card, Button, Badge, StatCard, Spinner, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

const ACTIVITY_ICONS = {
  scan: '📷',
  reading: '📖',
  task: '✅',
  quiz: '🧠',
  word: '⭐',
  assignment: '📝',
}

const TASK_ICONS = {
  reading: '📖',
  phonics: '🔤',
  vocabulary: '⭐',
  quiz: '🧠',
  exercise: '💪',
}

const RISK_COLOR = {
  Low: 'green',
  Mild: 'teal',
  Moderate: 'amber',
  High: 'red',
}

const DOMAIN_SHORT_LABEL = {
  'Visual Processing': 'Visual',
  'Phonological Processing': 'Phonological',
  'Orthographic Processing': 'Orthographic',
  'Reading Fluency': 'Fluency',
  'Reading Accuracy': 'Accuracy',
  'Working Memory': 'Memory',
  'Rapid Automatized Naming (RAN)': 'RAN',
  'Reading Comprehension': 'Comprehension',
  'Processing Speed': 'Speed',
  'Spelling Ability': 'Spelling',
  'Visual Attention': 'Attention',
  'Language Processing': 'Language',
}

// ─── Cognitive Radar Chart (pure SVG, accessible color palette) ───────────

function CognitiveRadarChart({ domains, accent = '#4F46E5', size = 280 }) {
  const entries = Object.values(domains || {}).filter((d) => d && d.label)
  if (entries.length < 3) return null

  const center = size / 2
  const radius = size / 2 - 36
  const angleStep = (2 * Math.PI) / entries.length

  const pointFor = (i, value01) => {
    const angle = -Math.PI / 2 + i * angleStep
    const r = radius * value01
    return [center + r * Math.cos(angle), center + r * Math.sin(angle)]
  }

  // Mastery = 100 - deficit score, framed positively for the student.
  const masteryPoints = entries.map((d, i) => {
    const mastery = d.tested ? Math.max(0, Math.min(100, 100 - d.score)) : 60
    return pointFor(i, mastery / 100)
  })
  const polygon = masteryPoints.map((p) => p.join(',')).join(' ')

  const rings = [0.25, 0.5, 0.75, 1]

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" height={size} className="mx-auto" aria-label="Cognitive domain radar chart">
      {rings.map((r, i) => {
        const pts = entries.map((_, idx) => pointFor(idx, r).join(',')).join(' ')
        return <polygon key={i} points={pts} fill="none" stroke="#E2E8F0" strokeWidth="1" />
      })}
      {entries.map((d, i) => {
        const [x, y] = pointFor(i, 1)
        return <line key={i} x1={center} y1={center} x2={x} y2={y} stroke="#E2E8F0" strokeWidth="1" />
      })}
      <polygon points={polygon} fill={accent} fillOpacity="0.2" stroke={accent} strokeWidth="2" />
      {masteryPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3.5" fill={entries[i].tested ? accent : '#94A3B8'} />
      ))}
      {entries.map((d, i) => {
        const [x, y] = pointFor(i, 1.22)
        return (
          <text
            key={i}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="10.5"
            fontWeight="600"
            fill={d.tested ? '#1E293B' : '#94A3B8'}
            className="dyslexia-text"
          >
            {DOMAIN_SHORT_LABEL[d.label] || d.label}
          </text>
        )
      })}
    </svg>
  )
}

// ─── Small trend/bar charts (pure SVG) ─────────────────────────────────────

function MiniLineChart({ values = [], color = '#4F46E5', height = 70 }) {
  if (!values.length) return <p className="dyslexia-text text-sm text-slate-400">Not enough data yet.</p>
  const w = 260
  const max = Math.max(100, ...values)
  const min = Math.min(0, ...values)
  const range = max - min || 1
  const stepX = values.length > 1 ? w / (values.length - 1) : 0
  const pts = values.map((v, i) => [i * stepX, height - ((v - min) / range) * height])
  const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ')

  return (
    <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} aria-label="Confidence trend line chart">
      <path d={path} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill={color} />
      ))}
    </svg>
  )
}

function WeeklyBarChart({ weeklyActivity = {}, color = '#4F46E5' }) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const values = days.map((d) => weeklyActivity[d] || 0)
  const max = Math.max(1, ...values)
  return (
    <div className="flex items-end justify-between gap-2 h-24" aria-label="Weekly activity bar chart">
      {values.map((v, i) => (
        <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
          <div className="w-full flex items-end justify-center h-16">
            <div
              className="w-full max-w-[26px] rounded-t-lg transition-all"
              style={{
                height: `${(v / max) * 100}%`,
                minHeight: v > 0 ? '6px' : '2px',
                backgroundColor: v > 0 ? color : '#E2E8F0',
              }}
              title={`${days[i]}: ${v} activities`}
            />
          </div>
          <span className="dyslexia-text text-xs font-semibold text-slate-500">{days[i]}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Main Student Dashboard ─────────────────────────────────────────────────

export default function StudentHome() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [progress, setProgress] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [, setPlan] = useState(null)
  const [classroom, setClassroom] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [p, t, pl] = await Promise.all([
          progressAPI.summary(),
          tasksAPI.today(),
          planAPI.get().catch(() => ({ hasPlan: false })),
        ])
        setProgress(p)
        setTasks(t)
        setPlan(pl)
        classroomAPI.info().then(setClassroom).catch(() => {})
      } catch {
        toast.error('Could not load your dashboard.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const completeTask = async (id) => {
    try {
      const res = await tasksAPI.complete(id)
      setTasks((prev) => ({
        ...prev,
        tasks: prev.tasks.map((t) => (t.id === id ? { ...t, completed: true } : t)),
        completed: prev.completed + 1,
      }))
      if (res.allDone) toast.success('🎉 All tasks done for today! Amazing work!')
      else toast.success('✅ Task completed!')
    } catch {
      toast.error('Could not complete task.')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24">
        <Spinner size="lg" color="primary" />
      </div>
    )
  }

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  const profile = user?.readingProfile
  const isV2Profile = !!profile?.cognitiveProfile && Object.keys(profile.cognitiveProfile).length > 0
  const riskLevel =
    profile?.riskLevel ||
    (profile?.level === 'high' ? 'High' : profile?.level === 'moderate' ? 'Moderate' : profile?.level ? 'Low' : null)
  const riskColor = RISK_COLOR[riskLevel] || 'gray'

  // Adaptive UI response
  const ui = profile?.uiSettings || {}
  const accent = '#4F46E5' // Primary brand indigo
  const dashboardStyle = {
    fontSize: ui.font_size === 'large' ? '1.08em' : undefined,
    lineHeight: ui.line_spacing || undefined,
  }
  const maxTasksShown = ui.chunk_length === 'short' ? 2 : 3
  const showExtendedTimeBadge = !!ui.extended_time
  const showTTSBadge = !!ui.tts_default_on

  const strengths = profile?.strengths || []
  const weaknesses = profile?.weaknesses || []
  const learningStyle = profile?.learningStyle
  const interventions = profile?.interventions || []
  const recommendedActivities = profile?.recommendedActivities || []
  const recommendedGames = profile?.recommendedGames || []
  const confidence = profile?.confidence
  const trendValues = progress?.comprehensionScores?.slice(-8) || []

  return (
    <div className="flex flex-col gap-6" style={dashboardStyle}>
      {/* ── Welcome & Primary CTA Banner ── */}
      <Card className="p-5 sm:p-8 bg-gradient-to-br from-indigo-600 via-indigo-700 to-indigo-800 text-white border-0 shadow-lg relative overflow-hidden">
        {/* Soft background ambient glow */}
        <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-white/10 blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 text-white text-xs font-bold dyslexia-text">
              <span>{greeting}</span>
              {progress?.streak > 0 && (
                <>
                  <span>•</span>
                  <span>🔥 {progress.streak} Day Streak</span>
                </>
              )}
            </div>
            <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold text-white leading-tight">
              {user?.name || 'Learner'} 👋
            </h1>
            <p className="dyslexia-text text-sm sm:text-base text-indigo-100 max-w-xl">
              Ready for today&apos;s reading adventure? Your personal coach and tutor are ready whenever you are.
            </p>
          </div>

          {/* Quick Metrics & Next Action */}
          <div className="flex flex-col sm:flex-row md:flex-col items-start md:items-end gap-3 shrink-0">
            <div className="bg-white/10 backdrop-blur-md px-4 py-2 rounded-2xl border border-white/20 text-left md:text-right">
              <span className="text-[11px] uppercase tracking-wider text-indigo-200 block font-bold">
                Avg Comprehension
              </span>
              <span className="text-2xl font-black text-white">
                {progress?.avgComprehension ?? 0}%
              </span>
            </div>
            <Button
              variant="accent"
              size="md"
              onClick={() => navigate('/student/reading-coach')}
              className="shadow-md"
            >
              Start Reading Coach 📖 →
            </Button>
          </div>
        </div>
      </Card>

      {/* ── No Screening Yet Card ── */}
      {!profile ? (
        <Card className="border-2 border-amber-300 bg-amber-50/80 p-6 sm:p-8">
          <div className="flex items-center gap-5 flex-wrap sm:flex-nowrap">
            <div className="w-14 h-14 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center text-3xl shrink-0">
              🧠
            </div>
            <div className="flex-1 space-y-1">
              <h2 className="dyslexia-text font-bold text-lg text-amber-950">
                Take your reading screening evaluation
              </h2>
              <p className="dyslexia-text text-sm text-amber-800">
                Takes just 5 minutes. We&apos;ll discover your strengths and configure your personalized reading tools.
              </p>
            </div>
            <Button onClick={() => navigate('/student/screening')} variant="accent" className="shrink-0">
              Start Screening →
            </Button>
          </div>
        </Card>
      ) : (
        <>
          {/* ── Adaptive Learning Spotlight ── */}
          <Card className="p-5 sm:p-6 border-slate-200 bg-gradient-to-r from-indigo-50/70 to-teal-50/40">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3.5">
                <div className="w-12 h-12 rounded-2xl bg-indigo-100 text-indigo-700 flex items-center justify-center text-2xl shrink-0">
                  🎯
                </div>
                <div>
                  <h2 className="dyslexia-text font-bold text-base text-slate-900">
                    Adaptive Learning Challenges
                  </h2>
                  <p className="dyslexia-text text-xs sm:text-sm text-slate-600 mt-0.5">
                    Bite-sized micro-tasks calibrated to your current reading level and growth areas.
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => navigate('/student/adaptive-learning')}
              >
                Play Adaptive Tasks →
              </Button>
            </div>
          </Card>

          {/* ── Cognitive Profile Section ── */}
          <Card className="p-6 sm:p-8 space-y-5">
            <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🧠</span>
                <h2 className="dyslexia-text font-bold text-lg sm:text-xl text-slate-900">
                  Your Cognitive Profile
                </h2>
              </div>
              <div className="flex gap-2 flex-wrap items-center">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => navigate('/student/profile')}
                  className="text-xs"
                >
                  🌟 Full Profile →
                </Button>
                {riskLevel && <Badge color={riskColor}>{riskLevel} support level</Badge>}
                {typeof confidence === 'number' && <Badge color="gray">{confidence}% confidence</Badge>}
              </div>
            </div>

            {!isV2Profile ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge color={riskColor}>{profile.type}</Badge>
                  <Badge color={riskColor}>{profile.level} level</Badge>
                </div>
                {profile.recommendation && (
                  <p className="dyslexia-text text-sm text-slate-600">{profile.recommendation}</p>
                )}
                <Alert type="info">
                  Retake the screening evaluation to unlock your full cognitive profile — radar chart, strengths, and personalized accommodations.
                </Alert>
              </div>
            ) : (
              <div className="grid md:grid-cols-12 gap-8 items-center">
                <div className="md:col-span-6 lg:col-span-5 text-center">
                  <CognitiveRadarChart domains={profile.cognitiveProfile} accent={accent} />
                  <p className="dyslexia-text text-xs text-slate-400 mt-2">
                    Outer edge = stronger skill • Grey dots = not yet tested
                  </p>
                </div>

                <div className="md:col-span-6 lg:col-span-7 space-y-4">
                  {learningStyle && (
                    <div>
                      <p className="dyslexia-text text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                        Recommended Learning Style
                      </p>
                      <Badge color="indigo" className="text-sm font-bold">
                        {learningStyle}
                      </Badge>
                    </div>
                  )}

                  {strengths.length > 0 && (
                    <div>
                      <p className="dyslexia-text text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                        💪 Confirmed Strengths
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {strengths.map((s) => (
                          <Badge key={s} color="green">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {weaknesses.length > 0 && (
                    <div>
                      <p className="dyslexia-text text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                        🎯 Focus & Practice Areas
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {weaknesses.map((w) => (
                          <Badge key={w} color="amber">
                            {w}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </Card>

          {/* ── AI Recommendations ── */}
          {(interventions.length > 0 || recommendedActivities.length > 0 || recommendedGames.length > 0) && (
            <Card className="p-6 space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-xl">✨</span>
                <h2 className="dyslexia-text font-bold text-lg text-slate-900">
                  AI Learning Suggestions
                </h2>
              </div>

              <div className="space-y-3">
                {interventions.slice(0, 3).map((text, i) => (
                  <div key={i} className="flex items-start gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                    <span className="text-lg shrink-0">💡</span>
                    <p className="dyslexia-text text-sm text-slate-700 leading-relaxed">{text}</p>
                  </div>
                ))}

                {recommendedActivities.length > 0 && (
                  <div className="pt-1">
                    <p className="dyslexia-text text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Suggested Activities
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {recommendedActivities.map((a) => (
                        <Badge key={a} color="teal">
                          {a}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {recommendedGames.length > 0 && (
                  <div className="pt-1">
                    <p className="dyslexia-text text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Suggested Mini-Games
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {recommendedGames.map((g) => (
                        <Badge key={g} color="indigo">
                          🎮 {g}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}
        </>
      )}

      {/* ── Today's Activities ── */}
      {tasks && (
        <Card className="p-6 sm:p-8 space-y-5">
          <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <span className="text-2xl">✅</span>
              <h2 className="dyslexia-text font-bold text-lg sm:text-xl text-slate-900">
                Today&apos;s Activities
              </h2>
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              {showExtendedTimeBadge && <Badge color="indigo">⏱ Extended Time</Badge>}
              {showTTSBadge && <Badge color="teal">🔊 Read-Aloud</Badge>}
              <Badge color={tasks.completed === tasks.total ? 'green' : 'amber'}>
                {tasks.completed}/{tasks.total} Done
              </Badge>
            </div>
          </div>

          {!tasks.hasScreening ? (
            <p className="dyslexia-text text-slate-500 text-sm">
              Complete your screening evaluation to get personalized daily activities!
            </p>
          ) : tasks.tasks?.length === 0 ? (
            <p className="dyslexia-text text-slate-500 text-sm">
              All caught up for today! Feel free to practice in Reading Coach or AI Tutor.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {tasks.tasks.slice(0, maxTasksShown).map((task) => (
                <div
                  key={task.id}
                  className={`flex items-center justify-between gap-4 p-4 rounded-xl border transition-all ${
                    task.completed
                      ? 'bg-slate-50/80 border-slate-200 opacity-60'
                      : 'bg-white border-slate-200 shadow-2xs hover:border-indigo-200'
                  }`}
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <span className="text-2xl shrink-0">{TASK_ICONS[task.type] || '💪'}</span>
                    <div className="min-w-0">
                      <p className="dyslexia-text font-bold text-sm sm:text-base text-slate-900 truncate">
                        {task.title}
                      </p>
                      <p className="dyslexia-text text-xs text-slate-500 mt-0.5">
                        {task.durationMinutes} minutes • {task.type}
                      </p>
                    </div>
                  </div>

                  {!task.completed ? (
                    <Button size="sm" onClick={() => completeTask(task.id)}>
                      Mark Done
                    </Button>
                  ) : (
                    <span className="text-emerald-600 font-bold text-sm flex items-center gap-1">
                      <span>✓</span> Done
                    </span>
                  )}
                </div>
              ))}
              {tasks.tasks.length > maxTasksShown && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/student/tasks')}
                  className="w-full mt-2"
                >
                  View all {tasks.total} activities →
                </Button>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ── Weekly Activity + Reading Progress ── */}
      {progress && (
        <div className="grid md:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <span className="text-xl">📅</span>
              <h2 className="dyslexia-text font-bold text-lg text-slate-900">Weekly Progress</h2>
            </div>
            <WeeklyBarChart weeklyActivity={progress.weeklyActivity} color={accent} />
          </Card>

          <Card className="p-6 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
              <span className="text-xl">📖</span>
              <h2 className="dyslexia-text font-bold text-lg text-slate-900">Reading Totals</h2>
            </div>
            <div className="grid grid-cols-2 gap-3.5">
              <StatCard icon="📄" label="Docs Scanned" value={progress.docsScanned} color="teal" />
              <StatCard icon="📖" label="Words Read" value={progress.wordsRead?.toLocaleString() || 0} color="amber" />
              <StatCard icon="⭐" label="Words Mastered" value={progress.wordsMastered || 0} color="green" />
              <StatCard icon="🏆" label="Reading Level" value={progress.levelLabel || 'Beginning'} color="indigo" />
            </div>
          </Card>
        </div>
      )}

      {/* ── Confidence Trend ── */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <span className="text-xl">📈</span>
            <h2 className="dyslexia-text font-bold text-lg text-slate-900">Confidence Trend</h2>
          </div>
          {typeof confidence === 'number' && <Badge color={riskColor}>Current: {confidence}%</Badge>}
        </div>
        <MiniLineChart values={trendValues} color={accent} />
        <p className="dyslexia-text text-xs text-slate-400">
          Calculated from your last {trendValues.length} reading comprehension checks.
        </p>
      </Card>

      {/* ── Adaptive Settings Summary ── */}
      {isV2Profile && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="text-xl">⚙️</span>
              <h2 className="dyslexia-text font-bold text-lg text-slate-900">Adaptive Reading Preferences</h2>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/student/settings')}>
              Customize →
            </Button>
          </div>
          <p className="dyslexia-text text-xs text-slate-500">
            Configured to fit your reading profile. You can tweak font, spacing, and tools anytime.
          </p>
          <div className="flex flex-wrap gap-2">
            <Badge color="gray">Font: {ui.font || 'OpenDyslexic'}</Badge>
            <Badge color="gray">Background: {ui.background || 'white'}</Badge>
            <Badge color="gray">Size: {ui.font_size || 'medium'}</Badge>
            {ui.tts_default_on && <Badge color="teal">Read-aloud by default</Badge>}
            {ui.extended_time && <Badge color="indigo">Extended time</Badge>}
            {ui.chunk_length === 'short' && <Badge color="amber">Short text chunks</Badge>}
            {ui.highlight_syllables && <Badge color="teal">Syllable highlighting</Badge>}
          </div>
        </Card>
      )}

      {/* ── Quick Actions Grid ── */}
      <div className="space-y-3">
        <h2 className="dyslexia-text font-bold text-lg text-slate-900">⚡ Quick Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          {[
            { icon: '🤖', label: 'AI Tutor', to: '/student/tutor', color: 'hover:border-indigo-400', bg: 'bg-indigo-50/60 text-indigo-700' },
            { icon: '📖', label: 'Reading Coach', to: '/student/reading-coach', color: 'hover:border-teal-400', bg: 'bg-teal-50/60 text-teal-700' },
            { icon: '🎯', label: 'Skill Drills', to: '/student/adaptive-learning', color: 'hover:border-indigo-400', bg: 'bg-indigo-50/60 text-indigo-700' },
            { icon: '📷', label: 'Scan Text', to: '/student/scan', color: 'hover:border-teal-400', bg: 'bg-teal-50/60 text-teal-700' },
            { icon: '📊', label: 'Progress', to: '/student/progress', color: 'hover:border-indigo-400', bg: 'bg-indigo-50/60 text-indigo-700' },
            { icon: '💬', label: 'AI Chat', to: '/student/chat', color: 'hover:border-amber-400', bg: 'bg-amber-50/60 text-amber-700' },
          ].map((a) => (
            <button
              key={a.to}
              onClick={() => navigate(a.to)}
              className={`p-4 rounded-2xl bg-white border border-slate-200 ${a.color} shadow-2xs hover:shadow-md transition-all flex flex-col items-center justify-center gap-2.5 min-h-[100px] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600`}
            >
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-2xl ${a.bg}`}>
                {a.icon}
              </div>
              <span className="dyslexia-text font-bold text-xs text-slate-800 text-center leading-tight">
                {a.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Classroom Info ── */}
      {classroom?.classroom && (
        <Card className="p-6 space-y-2 border-indigo-100 bg-indigo-50/40">
          <div className="flex items-center gap-2">
            <span className="text-xl">🏫</span>
            <h2 className="dyslexia-text font-bold text-base text-slate-900">Your Classroom</h2>
          </div>
          <div className="grid sm:grid-cols-3 gap-3 text-sm dyslexia-text text-slate-700 pt-1">
            <p>
              Teacher: <span className="font-bold text-slate-900">{classroom.classroom.teacherName}</span>
            </p>
            <p>
              School: <span className="font-bold text-slate-900">{classroom.classroom.schoolName}</span>
            </p>
            <p>
              Code: <span className="font-mono font-bold bg-white px-2 py-0.5 rounded-md border border-indigo-200 text-indigo-700">{classroom.classroom.code}</span>
            </p>
          </div>
        </Card>
      )}

      {/* ── Recent Activity ── */}
      {progress?.recentActivity?.length > 0 && (
        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <span className="text-xl">🕐</span>
            <h2 className="dyslexia-text font-bold text-lg text-slate-900">Recent Reading Sessions</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {progress.recentActivity.slice(0, 5).map((a, i) => (
              <div key={i} className="flex items-center gap-3.5 py-3 first:pt-1 last:pb-1">
                <span className="text-2xl shrink-0">{ACTIVITY_ICONS[a.type] || '📌'}</span>
                <div className="flex-1 min-w-0">
                  <p className="dyslexia-text text-sm font-semibold text-slate-800 truncate">
                    {a.description || a.type}
                  </p>
                  <p className="dyslexia-text text-xs text-slate-400 mt-0.5">{a.time || 'Recently'}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}