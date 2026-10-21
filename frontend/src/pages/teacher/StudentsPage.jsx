import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { teacherAPI } from '../../api/client'
import { Card, Badge, PageHeader, Spinner, ProgressBar, EmptyState } from '../../components/ui'
import toast from 'react-hot-toast'

const TABS = [
  { key: 'all', label: 'All Learners' },
  { key: 'on_track', label: 'On Track' },
  { key: 'progressing', label: 'Progressing' },
  { key: 'needs_attention', label: 'Needs Attention' },
  { key: 'not_screened', label: 'Not Screened' },
]

const STATUS_COLOR = {
  on_track: 'green',
  progressing: 'amber',
  needs_attention: 'red',
  not_screened: 'gray',
}

const STATUS_BORDER = {
  on_track: 'border-l-emerald-500',
  progressing: 'border-l-amber-400',
  needs_attention: 'border-l-rose-500',
  not_screened: 'border-l-slate-300',
}

export default function StudentsPage() {
  const navigate = useNavigate()
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    teacherAPI.students()
      .then(setStudents)
      .catch(() => toast.error('Could not load students.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = students.filter((s) => {
    const matchesTab = activeTab === 'all' || s.status === activeTab
    const matchesSearch = !search || s.name.toLowerCase().includes(search.toLowerCase()) || s.email?.toLowerCase().includes(search.toLowerCase())
    return matchesTab && matchesSearch
  })

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <Spinner size="lg" color="primary" />
        <p className="dyslexia-text text-sm font-bold text-slate-600">
          Loading classroom student roster...
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        icon="👥"
        title="Classroom Learners"
        subtitle={`${students.length} student${students.length !== 1 ? 's' : ''} enrolled in your class.`}
        action={
          <button
            type="button"
            onClick={() => navigate('/teacher')}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition-all shrink-0"
          >
            <span>←</span> Back to Dashboard
          </button>
        }
      />

      {/* ── Search Input & Controls Bar ── */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200 shadow-card flex flex-col md:flex-row md:items-center gap-4">
        <div className="relative flex-1">
          <span className="absolute left-3.5 top-3 text-slate-400 text-sm">🔍</span>
          <input
            type="text"
            className="w-full pl-10 pr-4 py-2.5 rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 dyslexia-text text-sm
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all placeholder:text-slate-400"
            placeholder="Search learner by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="absolute right-3.5 top-2.5 text-xs text-slate-400 hover:text-slate-600"
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {TABS.map((tab) => {
            const count = tab.key === 'all'
              ? students.length
              : students.filter((s) => s.status === tab.key).length
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-xl dyslexia-text text-xs font-bold whitespace-nowrap transition-all
                  ${isActive
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 border border-transparent text-slate-600 hover:bg-slate-200'}`}
              >
                <span>{tab.label}</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold
                  ${isActive ? 'bg-white/25 text-white' : 'bg-slate-200 text-slate-700'}`}>
                  {count}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Student List ── */}
      {filtered.length === 0 ? (
        <div className="bg-white p-12 rounded-3xl border border-slate-200 text-center shadow-card">
          <EmptyState
            icon="👥"
            title="No students match criteria"
            message={search ? 'Try clearing or modifying your search term.' : 'No students found in this status category.'}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((s) => (
            <Card
              key={s.id}
              onClick={() => navigate(`/teacher/students/${s.id}`)}
              className={`p-5 bg-white border border-slate-200 border-l-4 ${STATUS_BORDER[s.status] || 'border-l-slate-300'} hover:border-indigo-300 hover:shadow-card hover:-translate-y-0.5 transition-all cursor-pointer flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <p className="dyslexia-text font-bold text-slate-900 text-sm">
                        {s.name}
                      </p>
                      <Badge color={STATUS_COLOR[s.status] || 'gray'} size="sm">
                        {s.status?.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="dyslexia-text text-xs text-slate-500 truncate">
                      {s.email}
                    </p>
                  </div>
                  <span className="text-slate-400 group-hover:text-indigo-600 transition-colors shrink-0">
                    →
                  </span>
                </div>

                {/* 3 Key Student Telemetry Numbers */}
                <div className="grid grid-cols-3 gap-2 p-3 bg-slate-50/70 rounded-2xl border border-slate-100 mb-3">
                  <div className="text-center">
                    <p className="dyslexia-text text-base font-black text-indigo-600 font-mono">
                      {s.comprehension || 0}%
                    </p>
                    <p className="dyslexia-text text-[11px] text-slate-500 font-medium">Comprehension</p>
                  </div>
                  <div className="text-center border-x border-slate-200/60">
                    <p className="dyslexia-text text-base font-black text-amber-600 font-mono">
                      {s.streak || 0}d 🔥
                    </p>
                    <p className="dyslexia-text text-[11px] text-slate-500 font-medium">Reading Streak</p>
                  </div>
                  <div className="text-center">
                    <p className="dyslexia-text text-base font-black text-slate-800 font-mono">
                      {s.assignmentsSubmitted || 0}/{s.assignmentsTotal || 0}
                    </p>
                    <p className="dyslexia-text text-[11px] text-slate-500 font-medium">Tasks Done</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1 mb-3">
                  <div className="flex justify-between text-[11px] font-bold text-slate-500">
                    <span>Performance Benchmark</span>
                    <span>{s.comprehension || 0}/100</span>
                  </div>
                  <ProgressBar
                    value={s.comprehension || 0}
                    max={100}
                    color={s.status === 'needs_attention' ? 'red' : s.status === 'on_track' ? 'green' : 'primary'}
                  />
                </div>
              </div>

              {/* Status and Capability Chips */}
              <div className="flex gap-1.5 flex-wrap pt-3 border-t border-slate-100">
                {s.profile && (
                  <Badge color="primary" size="sm">
                    {s.profile.replace('_', ' ')}
                  </Badge>
                )}
                {!s.screeningDone && <Badge color="gray" size="sm">No screening</Badge>}
                {!s.planGenerated && s.screeningDone && <Badge color="amber" size="sm">Plan pending</Badge>}
                {s.profileLevel && (
                  <span className="text-[11px] font-bold text-slate-600 px-2 py-0.5 rounded-full bg-slate-100">
                    Level {s.profileLevel}
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
