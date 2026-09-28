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
  on_track: '✅ On Track',
  progressing: '📈 Progressing',
  needs_attention: '⚠️ Needs Attention',
  not_screened: '❓ Not Screened',
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
        setStudents(s)
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
      toast.success('📢 Announcement sent!')
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

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )

  const classroomCode = user?.classroomCode || analytics?.classroomCode || '------'
  const needsAttention = students.filter((s) => s.status === 'needs_attention')
  const typeDistribution = analytics?.dyslexiaTypeDistribution || {}
  const maxType = Math.max(...Object.values(typeDistribution), 1)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon="📊"
        title={`Welcome, ${user?.name?.split(' ')[0]}!`}
        subtitle="Here is your classroom overview."
      />

      {/* Classroom code — prominent */}
      <Card className="bg-[#1A6B6B] border-0 text-white">
        <p className="dyslexia-text text-white/80 text-sm mb-1">Your Classroom Code</p>
        <div className="flex items-center gap-4 flex-wrap">
          <span className="dyslexia-text text-4xl font-bold tracking-widest font-mono">
            {classroomCode}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCopyCode}
            className="bg-white/20 text-white border-white/40 hover:bg-white/30"
          >
            {copied ? '✅ Copied!' : '📋 Copy Code'}
          </Button>
        </div>
        <p className="dyslexia-text text-white/60 text-xs mt-2">
          Share this code with your students so they can join your classroom.
        </p>
      </Card>

      {/* Analytics stats */}
      {analytics && (
        <div className="grid grid-cols-2 gap-3">
          <StatCard icon="👥" label="Total Students" value={analytics.studentCount} color="teal" />
          <StatCard icon="🧠" label="Screened" value={analytics.screenedCount} color="amber" />
          <StatCard icon="🎯" label="Avg Score" value={`${analytics.avgComprehension || 0}%`} color="green" />
          <StatCard icon="📝" label="Submission Rate" value={`${analytics.submissionRate || 0}%`} color="teal" />
        </div>
      )}

      {/* Status overview */}
      {analytics && (
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: 'on_track', count: analytics.onTrack, icon: '✅' },
            { key: 'needs_attention', count: analytics.needsAttention, icon: '⚠️' },
          ].map((s) => (
            <Card key={s.key} className={s.key === 'needs_attention' && s.count > 0 ? 'border-red-200 bg-red-50' : ''}>
              <p className="text-3xl mb-1">{s.icon}</p>
              <p className="dyslexia-text text-2xl font-bold">{s.count}</p>
              <p className="dyslexia-text text-sm text-gray-500">{STATUS_LABEL[s.key]}</p>
            </Card>
          ))}
        </div>
      )}

      {/* Dyslexia type distribution */}
      {Object.keys(typeDistribution).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-4">🧠 Dyslexia Type Distribution</h2>
          <div className="flex flex-col gap-3">
            {Object.entries(typeDistribution).map(([type, count]) => (
              <div key={type}>
                <div className="flex justify-between mb-1">
                  <span className="dyslexia-text text-sm capitalize">{type.replace('_', ' ')}</span>
                  <span className="dyslexia-text text-sm font-semibold">{count} students</span>
                </div>
                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#1A6B6B] rounded-full transition-all"
                    style={{ width: `${Math.round((count / maxType) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Students needing attention */}
      {needsAttention.length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-3 text-red-600">
            ⚠️ Students Needing Attention
          </h2>
          <div className="flex flex-col gap-2">
            {needsAttention.slice(0, 5).map((s) => (
              <div
                key={s.id}
                onClick={() => navigate(`/teacher/students/${s.id}`)}
                className="flex items-center justify-between p-3 rounded-xl border border-red-200 bg-red-50 cursor-pointer hover:shadow-sm transition"
              >
                <div>
                  <p className="dyslexia-text font-semibold text-sm">{s.name}</p>
                  <p className="dyslexia-text text-xs text-gray-500">
                    Comprehension: {s.comprehension || 0}% · Streak: {s.streak || 0}d
                  </p>
                </div>
                <span className="text-gray-400">→</span>
              </div>
            ))}
            {needsAttention.length > 5 && (
              <Button variant="ghost" onClick={() => navigate('/teacher/students')} size="sm">
                View all {needsAttention.length} →
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* Announcement */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-3">📢 Send Announcement</h2>
        <div className="flex flex-col gap-3">
          <textarea
            className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
              focus:outline-none focus:border-[#1A6B6B] resize-none"
            rows={3}
            placeholder="Type a message for all your students…"
            value={announcement}
            onChange={(e) => setAnnouncement(e.target.value)}
          />
          <Button onClick={handleAnnounce} loading={sending} disabled={!announcement.trim()}>
            📢 Send to Class
          </Button>
        </div>
      </Card>

      {/* Quick links */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { icon: '👥', label: 'All Students', to: '/teacher/students', color: 'bg-[#E0F2F2]' },
          { icon: '📝', label: 'Assignments', to: '/teacher/assignments', color: 'bg-[#FFF3DC]' },
          { icon: '📷', label: 'Scan & Convert', to: '/teacher/scan', color: 'bg-[#F0F8FF]' },
          { icon: '💬', label: 'AI Chat', to: '/teacher/chat', color: 'bg-[#F5F0FF]' },
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
  )
}
