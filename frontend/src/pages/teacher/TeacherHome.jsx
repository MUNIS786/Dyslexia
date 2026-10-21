import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { teacherAPI, classroomAPI } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { Card, Button, Badge, StatCard, PageHeader, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

const STATUS_COLOR = {
  on_track: 'green',
  progressing: 'amber',
  needs_attention: 'red',
  not_screened: 'gray',
}
const STATUS_LABEL = {
  on_track: 'On Track',
  progressing: 'Progressing',
  needs_attention: 'Needs Attention',
  not_screened: 'Not Screened',
}

export default function TeacherHome() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [analytics, setAnalytics] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [announcement, setAnnouncement] = useState('')
  const [sending, setSending] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const [a, s] = await Promise.all([teacherAPI.analytics(), teacherAPI.students()])
        setAnalytics(a)
        setStudents(s || [])
      } catch {
        toast.error('Could not load dashboard.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleAnnounce = async () => {
    if (!announcement.trim()) return
    setSending(true)
    try {
      await classroomAPI.announce(announcement)
      toast.success('📢 Announcement sent to class!')
      setAnnouncement('')
    } catch {
      toast.error('Could not send announcement.')
    } finally {
      setSending(false)
    }
  }

  const handleCopyCode = () => {
    const code = user?.classroomCode || analytics?.classroomCode || ''
    if (!code) return
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <Spinner size="lg" color="primary" />
        <p className="dyslexia-text text-sm font-bold text-slate-600">
          Loading classroom overview...
        </p>
      </div>
    )
  }

  const classroomCode = user?.classroomCode || analytics?.classroomCode || '------'
  const needsAttention = students.filter((s) => s.status === 'needs_attention')
  const typeDistribution = analytics?.dyslexiaTypeDistribution || {}
  const maxType = Math.max(...Object.values(typeDistribution), 1)

  return (
    <div className="flex flex-col gap-6">
      {/* ── Welcome & Classroom Code Hero ── */}
      <Card className="p-5 sm:p-8 bg-gradient-to-br from-indigo-600 via-indigo-700 to-indigo-800 text-white border-0 shadow-lg relative overflow-hidden">
        <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-white/10 blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 text-white text-xs font-bold dyslexia-text">
              <span>🏫 Educator Portal</span>
              <span>·</span>
              <span>{students.length} Enrolled</span>
            </div>
            <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome, {user?.name?.split(' ')[0] || 'Teacher'}!
            </h1>
            <p className="dyslexia-text text-white/85 text-sm max-w-xl">
              Track student comprehension, identify reading support needs early, and manage inclusive classroom assignments.
            </p>
          </div>

          {/* Prominent Classroom Code Box */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 flex flex-col items-center md:items-end gap-2 shrink-0">
            <span className="dyslexia-text text-xs uppercase tracking-wider text-white/80 font-bold">
              Classroom Code
            </span>
            <div className="flex items-center gap-3">
              <span className="font-mono text-3xl font-black tracking-widest text-white drop-shadow-sm">
                {classroomCode}
              </span>
              <button
                type="button"
                onClick={handleCopyCode}
                className="px-3 py-1.5 rounded-xl bg-white text-indigo-700 hover:bg-white/90 text-xs font-bold transition-all shadow-sm flex items-center gap-1 focus:ring-2 focus:ring-white"
                aria-label="Copy classroom code"
              >
                {copied ? '✅ Copied!' : '📋 Copy'}
              </button>
            </div>
            <span className="dyslexia-text text-[11px] text-white/70">
              Students join with this code
            </span>
          </div>
        </div>
      </Card>

      {/* ── Key Metrics Overview ── */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon="👥"
            label="Total Students"
            value={analytics.studentCount || students.length || 0}
            color="primary"
          />
          <StatCard
            icon="🧠"
            label="Screened"
            value={analytics.screenedCount || 0}
            color="amber"
          />
          <StatCard
            icon="🎯"
            label="Avg Comprehension"
            value={`${analytics.avgComprehension || 0}%`}
            color="emerald"
          />
          <StatCard
            icon="📝"
            label="Submission Rate"
            value={`${analytics.submissionRate || 0}%`}
            color="primary"
          />
        </div>
      )}

      {/* ── Status Triage & Dyslexia Type Distribution ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cohort Status Triage */}
        <Card className="p-6 bg-white border border-slate-200 shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="dyslexia-text text-lg font-bold text-slate-900 flex items-center gap-2">
                <span>⚡</span> Cohort Status Triage
              </h2>
              <span className="text-xs font-semibold text-slate-500">
                {students.length} active learners
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200/80">
                <span className="text-2xl block mb-1">✅</span>
                <p className="dyslexia-text text-2xl font-black text-emerald-900">
                  {analytics?.onTrack || 0}
                </p>
                <p className="dyslexia-text text-xs font-bold text-emerald-700">
                  On Track
                </p>
              </div>

              <div className={`p-4 rounded-2xl border transition-all ${
                (analytics?.needsAttention || 0) > 0
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}>
                <span className="text-2xl block mb-1">⚠️</span>
                <p className="dyslexia-text text-2xl font-black text-rose-900">
                  {analytics?.needsAttention || 0}
                </p>
                <p className="dyslexia-text text-xs font-bold text-rose-700">
                  Needs Attention
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Students requiring guided support are highlighted in the student roster.</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/teacher/students')}
            >
              View Roster →
            </Button>
          </div>
        </Card>

        {/* Dyslexia Type Distribution */}
        <Card className="p-6 bg-white border border-slate-200 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="dyslexia-text text-lg font-bold text-slate-900 flex items-center gap-2">
              <span>🧠</span> Dyslexia Type Distribution
            </h2>
            <span className="text-xs font-semibold text-slate-500">Screening breakdown</span>
          </div>

          {Object.keys(typeDistribution).length > 0 ? (
            <div className="flex flex-col gap-3">
              {Object.entries(typeDistribution).map(([type, count]) => {
                const pct = Math.round((count / maxType) * 100)
                return (
                  <div key={type} className="space-y-1">
                    <div className="flex justify-between text-xs font-bold text-slate-700">
                      <span className="capitalize">{type.replace(/_/g, ' ')}</span>
                      <span className="text-slate-500 font-mono">{count} student{count !== 1 ? 's' : ''}</span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-600 rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(pct, 6)}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400 text-xs dyslexia-text space-y-1">
              <span>No screening profile data available yet.</span>
              <p className="text-slate-400">Students will appear here as they complete the initial reading check.</p>
            </div>
          )}
        </Card>
      </div>

      {/* ── Students Needing Attention Alert Card ── */}
      {needsAttention.length > 0 && (
        <Card className="p-6 bg-rose-50/50 border border-rose-200 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="dyslexia-text text-lg font-bold text-rose-900 flex items-center gap-2">
              <span>⚠️</span> Priority Attention Needed ({needsAttention.length})
            </h2>
            <span className="text-xs text-rose-700 font-semibold">
              Low comprehension score or declining streak
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {needsAttention.slice(0, 6).map((s) => (
              <div
                key={s.id}
                onClick={() => navigate(`/teacher/students/${s.id}`)}
                className="p-4 rounded-2xl bg-white border border-rose-200 hover:border-rose-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <p className="dyslexia-text font-bold text-sm text-slate-900 truncate">
                      {s.name}
                    </p>
                    <Badge color="red" size="sm">Attention</Badge>
                  </div>
                  <p className="dyslexia-text text-xs text-slate-500 truncate mb-2">
                    {s.email}
                  </p>
                </div>
                <div className="flex items-center justify-between text-xs font-bold text-slate-600 pt-2 border-t border-slate-100">
                  <span>Score: <strong className="text-rose-600 font-mono">{s.comprehension || 0}%</strong></span>
                  <span>Streak: <strong className="text-amber-600 font-mono">{s.streak || 0}d</strong></span>
                  <span className="text-indigo-600">Inspect →</span>
                </div>
              </div>
            ))}
          </div>

          {needsAttention.length > 6 && (
            <div className="mt-4 text-center">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/teacher/students')}
              >
                View all {needsAttention.length} students needing attention →
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* ── Class Announcement Composer ── */}
      <Card className="p-6 bg-white border border-slate-200 shadow-card">
        <h2 className="dyslexia-text text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
          <span>📢</span> Send Class Announcement
        </h2>
        <p className="dyslexia-text text-xs text-slate-500 mb-3">
          Broadcast a motivational message, reading reminder, or weekly homework note to all enrolled students.
        </p>
        <div className="flex flex-col gap-3">
          <textarea
            className="w-full px-4 py-3 rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 dyslexia-text text-sm
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white resize-none transition-all placeholder:text-slate-400"
            rows={3}
            placeholder="Type a supportive message or assignment update for your class…"
            value={announcement}
            onChange={(e) => setAnnouncement(e.target.value)}
          />
          <div className="flex justify-end">
            <Button
              onClick={handleAnnounce}
              loading={sending}
              disabled={!announcement.trim()}
              size="md"
            >
              📢 Send to Class
            </Button>
          </div>
        </div>
      </Card>

      {/* ── Quick Workflows Grid ── */}
      <div>
        <h2 className="dyslexia-text text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
          <span>⚡</span> Educator Workflows
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { icon: '👥', label: 'All Students', to: '/teacher/students', desc: 'Roster & profiles' },
            { icon: '📈', label: 'Class Analytics', to: '/teacher/analytics', desc: 'Longitudinal data' },
            { icon: '🎯', label: 'Interventions', to: '/teacher/interventions', desc: 'Targeted support' },
            { icon: '✍️', label: 'Content Studio', to: '/teacher/content', desc: 'Author passages' },
            { icon: '📝', label: 'Assignments', to: '/teacher/assignments', desc: 'Manage homework' },
            { icon: '📷', label: 'Scan & Convert', to: '/teacher/scan', desc: 'OCR & simplification' },
          ].map((a) => (
            <button
              key={a.to}
              type="button"
              onClick={() => navigate(a.to)}
              className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-card hover:-translate-y-0.5 transition-all text-left flex flex-col justify-between group min-h-[110px]"
            >
              <span className="text-3xl mb-2 group-hover:scale-110 transition-transform">{a.icon}</span>
              <div>
                <p className="dyslexia-text font-bold text-sm text-slate-900 group-hover:text-indigo-600 transition-colors">
                  {a.label}
                </p>
                <p className="dyslexia-text text-[11px] text-slate-500">
                  {a.desc}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
