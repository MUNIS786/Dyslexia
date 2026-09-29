import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { progressAPI, tasksAPI, planAPI, classroomAPI } from '../../api/client'
import { Card, Button, Badge, StatCard, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

const ACTIVITY_ICONS = { scan: '📷', reading: '📖', task: '✅', quiz: '🧠', word: '⭐', assignment: '📝' }

const TASK_ICONS = { reading: '📖', phonics: '🔤', vocabulary: '⭐', quiz: '🧠', exercise: '💪' }

const RISK_COLOR = { Low: 'green', Mild: 'teal', Moderate: 'amber', High: 'red' }

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

// ─── Cognitive Radar Chart (pure SVG, no chart library needed) ────────────

function CognitiveRadarChart({ domains, accent = '#1A6B6B', size = 280 }) {
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
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" height={size} className="mx-auto">
      {rings.map((r, i) => {
        const pts = entries.map((_, idx) => pointFor(idx, r).join(',')).join(' ')
        return <polygon key={i} points={pts} fill="none" stroke="#E5E0D8" strokeWidth="1" />
      })}
      {entries.map((d, i) => {
        const [x, y] = pointFor(i, 1)
        return <line key={i} x1={center} y1={center} x2={x} y2={y} stroke="#E5E0D8" strokeWidth="1" />
      })}
      <polygon points={polygon} fill={accent} fillOpacity="0.25" stroke={accent} strokeWidth="2" />
      {masteryPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3.5" fill={entries[i].tested ? accent : '#C9C2B6'} />
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
            fill={d.tested ? '#1A2A2A' : '#B0AAA0'}
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

function MiniLineChart({ values = [], color = '#1A6B6B', height = 70 }) {
  if (!values.length) return <p className="dyslexia-text text-sm text-gray-400">Not enough data yet.</p>
  const w = 260
  const max = Math.max(100, ...values)
  const min = Math.min(0, ...values)
  const range = max - min || 1
  const stepX = values.length > 1 ? w / (values.length - 1) : 0
  const pts = values.map((v, i) => [i * stepX, height - ((v - min) / range) * height])
  const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ')

  return (
    <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height}>
      <path d={path} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill={color} />
      ))}
    </svg>
  )
}

function WeeklyBarChart({ weeklyActivity = {}, color = '#1A6B6B' }) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const values = days.map((d) => weeklyActivity[d] || 0)
  const max = Math.max(1, ...values)
  return (
    <div className="flex items-end justify-between gap-2 h-24">
      {values.map((v, i) => (
        <div key={i} className="flex flex-col items-center gap-1 flex-1">
          <div className="w-full flex items-end justify-center h-16">
            <div
              className="w-full max-w-[26px] rounded-t-md transition-all"
              style={{ height: `${(v / max) * 100}%`, minHeight: v > 0 ? '4px' : '0px', backgroundColor: color }}
            />
          </div>
          <span className="dyslexia-text text-xs text-gray-500">{days[i][0]}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Main dashboard ─────────────────────────────────────────────────────────

export default function StudentHome() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [progress, setProgress] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [plan, setPlan] = useState(null)
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
      } catch (err) {
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
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  const profile = user?.readingProfile
  const isV2Profile = !!profile?.cognitiveProfile && Object.keys(profile.cognitiveProfile).length > 0
  const riskLevel = profile?.riskLevel || (profile?.level === 'high' ? 'High' : profile?.level === 'moderate' ? 'Moderate' : profile?.level ? 'Low' : null)
  const riskColor = RISK_COLOR[riskLevel] || 'gray'

  // ── Adaptive UI: theme + density respond to the student's own settings ──
  const ui = profile?.uiSettings || {}
  const accent = riskColor === 'red' ? '#C0504D' : riskColor === 'amber' ? '#E8A020' : '#1A6B6B'
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
      {/* Greeting */}
      <Card className="text-white border-0" style={{ backgroundColor: accent }}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-white/80 text-sm dyslexia-text">{greeting},</p>
            <h1 className="text-2xl font-bold dyslexia-text">{user?.name} 👋</h1>
            {progress?.streak > 0 && (
              <p className="mt-2 dyslexia-text text-white/90">
                🔥 {progress.streak} day streak — keep it up!
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-white/70 text-sm dyslexia-text">Comprehension</p>
            <p className="text-3xl font-bold dyslexia-text">{progress?.avgComprehension ?? 0}%</p>
          </div>
        </div>
      </Card>

      {/* No screening yet */}
      {!profile ? (
        <Card className="border-2 border-[#E8A020] bg-[#FFF3DC]">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="text-4xl">🧠</div>
            <div className="flex-1">
              <p className="dyslexia-text font-bold text-lg">Take your reading screening test</p>
              <p className="dyslexia-text text-sm text-gray-600">
                Just 8 minutes. We'll build your personal cognitive profile.
              </p>
            </div>
            <Button onClick={() => navigate('/student/screening')} variant="accent">
              Start Screening →
            </Button>
          </div>
        </Card>
      ) : (
        <>
          {/* ── Adaptive Learning Quick Spotlight ── */}
          <Card className="border-2 border-[#1A6B6B]/20 bg-gradient-to-r from-[#F0F8FF] to-[#FFF8F0]">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <span className="text-3xl">🎯</span>
                <div>
                  <h3 className="dyslexia-text font-bold text-base text-[#1A2A2A]">
                    Adaptive Learning Challenges
                  </h3>
                  <p className="dyslexia-text text-xs text-gray-600">
                    Bite-sized micro-tasks calibrated to your current learning level and ZPD growth areas.
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => navigate('/student/adaptive-learning')}
                className="bg-[#1A6B6B] text-white hover:bg-[#155555] font-semibold"
              >
                Play Adaptive Tasks →
              </Button>
            </div>
          </Card>

          {/* ── Cognitive Profile: radar chart + strengths/weaknesses + learning style ── */}
          <Card>
            <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
              <h2 className="dyslexia-text font-bold text-lg flex items-center gap-2">
                🧠 Your Cognitive Profile
              </h2>
              <div className="flex gap-2 flex-wrap items-center">
                <Button size="sm" variant="secondary" onClick={() => navigate('/student/profile')} className="text-xs py-1 px-2.5">
                  🌟 Full Learning Profile →
                </Button>
                {riskLevel && <Badge color={riskColor}>{riskLevel} support level</Badge>}
                {typeof confidence === 'number' && <Badge color="gray">{confidence}% confidence</Badge>}
              </div>
            </div>

            {!isV2Profile ? (
              // v1 fallback — old profile shape, no per-domain data available.
              <div className="mt-3">
                <div className="flex flex-wrap gap-2 mb-3">
                  <Badge color={riskColor}>{profile.type}</Badge>
                  <Badge color={riskColor}>{profile.level} level</Badge>
                </div>
                {profile.recommendation && (
                  <p className="dyslexia-text text-sm text-gray-600 mb-3">{profile.recommendation}</p>
                )}
                <Alert type="info">
                  Retake the screening test to unlock your full cognitive profile — radar chart, strengths,
                  weaknesses, and personalized learning style.
                </Alert>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-6 mt-3">
                <div>
                  <CognitiveRadarChart domains={profile.cognitiveProfile} accent={accent} />
                  <p className="dyslexia-text text-xs text-gray-400 text-center mt-1">
                    Outer edge = stronger skill. Grey dots = not yet tested.
                  </p>
                </div>

                <div className="flex flex-col gap-4">
                  {learningStyle && (
                    <div>
                      <p className="dyslexia-text text-sm text-gray-500 mb-1">Recommended Learning Style</p>
                      <Badge color="blue" className="text-sm">{learningStyle}</Badge>
                    </div>
                  )}

                  {strengths.length > 0 && (
                    <div>
                      <p className="dyslexia-text text-sm text-gray-500 mb-1.5">💪 Strengths</p>
                      <div className="flex flex-wrap gap-1.5">
                        {strengths.map((s) => (
                          <Badge key={s} color="green">{s}</Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {weaknesses.length > 0 && (
                    <div>
                      <p className="dyslexia-text text-sm text-gray-500 mb-1.5">🎯 Growth Areas</p>
                      <div className="flex flex-wrap gap-1.5">
                        {weaknesses.map((w) => (
                          <Badge key={w} color="amber">{w}</Badge>
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
            <Card>
              <h2 className="dyslexia-text font-bold text-lg mb-3 flex items-center gap-2">
                ✨ AI Recommendations
              </h2>
              <div className="flex flex-col gap-3">
                {interventions.slice(0, 3).map((text, i) => (
                  <div key={i} className="flex items-start gap-2 p-3 rounded-xl bg-[#F0F8FF]">
                    <span className="text-lg">💡</span>
                    <p className="dyslexia-text text-sm">{text}</p>
                  </div>
                ))}
                {recommendedActivities.length > 0 && (
                  <div>
                    <p className="dyslexia-text text-sm text-gray-500 mb-1.5">Suggested Activities</p>
                    <div className="flex flex-wrap gap-1.5">
                      {recommendedActivities.map((a) => (
                        <Badge key={a} color="teal">{a}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {recommendedGames.length > 0 && (
                  <div>
                    <p className="dyslexia-text text-sm text-gray-500 mb-1.5">Suggested Games</p>
                    <div className="flex flex-wrap gap-1.5">
                      {recommendedGames.map((g) => (
                        <Badge key={g} color="blue">🎮 {g}</Badge>
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
        <Card>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h2 className="dyslexia-text font-bold text-lg flex items-center gap-2">
              ✅ Today's Activities
            </h2>
            <div className="flex gap-2 items-center flex-wrap">
              {showExtendedTimeBadge && <Badge color="blue">⏱ Extended time on</Badge>}
              {showTTSBadge && <Badge color="teal">🔊 Read-aloud default</Badge>}
              <Badge color={tasks.completed === tasks.total ? 'green' : 'amber'}>
                {tasks.completed}/{tasks.total} done
              </Badge>
            </div>
          </div>

          {!tasks.hasScreening ? (
            <p className="dyslexia-text text-gray-500 text-sm">
              Complete your screening test to get daily activities!
            </p>
          ) : tasks.tasks?.length === 0 ? (
            <p className="dyslexia-text text-gray-500 text-sm">
              No activities for today. Come back tomorrow!
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {tasks.tasks.slice(0, maxTasksShown).map((task) => (
                <div
                  key={task.id}
                  className={`flex items-center gap-3 p-3 rounded-xl border ${
                    task.completed ? 'bg-green-50 border-green-200 opacity-60' : 'bg-[#FFF8F0] border-[#E5E0D8]'
                  }`}
                >
                  <span className="text-xl">{TASK_ICONS[task.type] || '💪'}</span>
                  <div className="flex-1 min-w-0">
                    <p className="dyslexia-text font-semibold text-sm truncate">{task.title}</p>
                    <p className="dyslexia-text text-xs text-gray-500">{task.durationMinutes} min</p>
                  </div>
                  {!task.completed && (
                    <Button size="sm" onClick={() => completeTask(task.id)}>Done</Button>
                  )}
                  {task.completed && <span className="text-green-500 text-xl">✓</span>}
                </div>
              ))}
              {tasks.tasks.length > maxTasksShown && (
                <Button variant="ghost" size="sm" onClick={() => navigate('/student/tasks')} className="w-full">
                  View all {tasks.total} activities →
                </Button>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ── Weekly Progress + Reading Progress ── */}
      {progress && (
        <div className="grid md:grid-cols-2 gap-4">
          <Card>
            <h2 className="dyslexia-text font-bold text-lg mb-3 flex items-center gap-2">📅 Weekly Progress</h2>
            <WeeklyBarChart weeklyActivity={progress.weeklyActivity} color={accent} />
          </Card>

          <Card>
            <h2 className="dyslexia-text font-bold text-lg mb-3 flex items-center gap-2">📖 Reading Progress</h2>
            <div className="grid grid-cols-2 gap-3">
              <StatCard icon="📄" label="Docs Scanned" value={progress.docsScanned} color="teal" />
              <StatCard icon="📖" label="Words Read" value={progress.wordsRead?.toLocaleString()} color="amber" />
              <StatCard icon="⭐" label="Words Mastered" value={progress.wordsMastered} color="green" />
              <StatCard icon="🏆" label="Level" value={progress.levelLabel || 'Beginning'} color="teal" />
            </div>
          </Card>
        </div>
      )}

      {/* ── Confidence Trend ── */}
      <Card>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h2 className="dyslexia-text font-bold text-lg flex items-center gap-2">📈 Confidence Trend</h2>
          {typeof confidence === 'number' && <Badge color={riskColor}>Current: {confidence}%</Badge>}
        </div>
        <MiniLineChart values={trendValues} color={accent} />
        <p className="dyslexia-text text-xs text-gray-400 mt-2">Based on your last {trendValues.length} comprehension checks.</p>
      </Card>

      {/* ── Adaptive Settings ── */}
      {isV2Profile && (
        <Card>
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h2 className="dyslexia-text font-bold text-lg flex items-center gap-2">⚙️ Adaptive Settings</h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/student/settings')}>
              Customize →
            </Button>
          </div>
          <p className="dyslexia-text text-sm text-gray-500 mb-3">
            These were set automatically from your cognitive profile.
          </p>
          <div className="flex flex-wrap gap-1.5">
            <Badge color="gray">Font: {ui.font || 'OpenDyslexic'}</Badge>
            <Badge color="gray">Background: {ui.background || 'white'}</Badge>
            <Badge color="gray">Text size: {ui.font_size || 'medium'}</Badge>
            {ui.tts_default_on && <Badge color="teal">Read-aloud on by default</Badge>}
            {ui.extended_time && <Badge color="blue">Extended time on tasks</Badge>}
            {ui.chunk_length === 'short' && <Badge color="amber">Short text chunks</Badge>}
            {ui.highlight_syllables && <Badge color="teal">Syllable highlighting</Badge>}
          </div>
        </Card>
      )}

      {/* Quick actions */}
      <div>
        <h2 className="dyslexia-text font-bold text-lg mb-3">⚡ Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { icon: '📷', label: 'Scan Text', to: '/student/scan', color: 'bg-[#E0F2F2]' },
            { icon: '🧠', label: 'My Plan', to: '/student/plan', color: 'bg-[#FFF3DC]' },
            { icon: '📊', label: 'Progress', to: '/student/progress', color: 'bg-[#F0F8FF]' },
            { icon: '💬', label: 'AI Chat', to: '/student/chat', color: 'bg-[#F5F0FF]' },
          ].map((a) => (
            <button
              key={a.to}
              onClick={() => navigate(a.to)}
              className={`${a.color} rounded-2xl p-4 flex flex-col items-center gap-2 hover:shadow-md transition-shadow min-h-[90px]`}
            >
              <span className="text-3xl">{a.icon}</span>
              <span className="dyslexia-text font-semibold text-sm">{a.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Classroom info */}
      {classroom?.classroom && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-2 flex items-center gap-2">🏫 Your Classroom</h2>
          <p className="dyslexia-text text-gray-600 text-sm">
            Teacher: <span className="font-semibold">{classroom.classroom.teacherName}</span>
          </p>
          <p className="dyslexia-text text-gray-600 text-sm">School: {classroom.classroom.schoolName}</p>
          <p className="dyslexia-text text-gray-600 text-sm">
            Code: <span className="font-mono font-bold">{classroom.classroom.code}</span>
          </p>
        </Card>
      )}

      {/* Recent activity */}
      {progress?.recentActivity?.length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-3">🕐 Recent Activity</h2>
          <div className="flex flex-col gap-2">
            {progress.recentActivity.slice(0, 5).map((a, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-[#E5E0D8] last:border-0">
                <span className="text-xl">{ACTIVITY_ICONS[a.type] || '📌'}</span>
                <div className="flex-1">
                  <p className="dyslexia-text text-sm font-medium">{a.description || a.type}</p>
                  <p className="dyslexia-text text-xs text-gray-400">{a.time || ''}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}