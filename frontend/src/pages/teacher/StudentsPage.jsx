import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { teacherAPI } from '../../api/client'
import { Card, Badge, PageHeader, Spinner, ProgressBar, EmptyState } from '../../components/ui'
import toast from 'react-hot-toast'

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'on_track', label: '✅ On Track' },
  { key: 'progressing', label: '📈 Progressing' },
  { key: 'needs_attention', label: '⚠️ Needs Attention' },
  { key: 'not_screened', label: '❓ Not Screened' },
]

const STATUS_COLOR = {
  on_track: 'green',
  progressing: 'amber',
  needs_attention: 'red',
  not_screened: 'gray',
}

const STATUS_BG = {
  on_track: 'border-l-green-500',
  progressing: 'border-l-amber-400',
  needs_attention: 'border-l-red-500',
  not_screened: 'border-l-gray-300',
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
    const matchesSearch = !search || s.name.toLowerCase().includes(search.toLowerCase())
    return matchesTab && matchesSearch
  })

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon="👥"
        title="My Students"
        subtitle={`${students.length} student${students.length !== 1 ? 's' : ''} in your classroom`}
      />

      {/* Search */}
      <input
        className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
          focus:outline-none focus:border-[#1A6B6B]"
        placeholder="🔍 Search by name…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {/* Filter tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {TABS.map((tab) => {
          const count = tab.key === 'all'
            ? students.length
            : students.filter((s) => s.status === tab.key).length
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl dyslexia-text text-sm font-semibold whitespace-nowrap transition-all
                ${activeTab === tab.key ? 'bg-[#1A6B6B] text-white' : 'bg-white border border-[#E5E0D8] text-gray-600 hover:bg-gray-50'}`}
            >
              {tab.label}
              <span className={`text-xs px-1.5 py-0.5 rounded-full font-bold
                ${activeTab === tab.key ? 'bg-white/30 text-white' : 'bg-gray-200 text-gray-600'}`}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Student list */}
      {filtered.length === 0 ? (
        <EmptyState
          icon="👥"
          title="No students found"
          message={search ? 'Try a different search.' : 'No students in this category.'}
        />
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((s) => (
            <Card
              key={s.id}
              onClick={() => navigate(`/teacher/students/${s.id}`)}
              className={`border-l-4 ${STATUS_BG[s.status] || 'border-l-gray-300'} hover:shadow-md transition-shadow`}
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <p className="dyslexia-text font-bold">{s.name}</p>
                    <Badge color={STATUS_COLOR[s.status] || 'gray'}>
                      {s.status?.replace('_', ' ')}
                    </Badge>
                  </div>
                  <p className="dyslexia-text text-xs text-gray-500">{s.email}</p>
                </div>
                <span className="text-gray-400 shrink-0">→</span>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3">
                <div className="text-center">
                  <p className="dyslexia-text text-lg font-bold text-[#1A6B6B]">{s.comprehension || 0}%</p>
                  <p className="dyslexia-text text-xs text-gray-500">Score</p>
                </div>
                <div className="text-center">
                  <p className="dyslexia-text text-lg font-bold text-[#E8A020]">{s.streak || 0}🔥</p>
                  <p className="dyslexia-text text-xs text-gray-500">Streak</p>
                </div>
                <div className="text-center">
                  <p className="dyslexia-text text-lg font-bold">
                    {s.assignmentsSubmitted || 0}/{s.assignmentsTotal || 0}
                  </p>
                  <p className="dyslexia-text text-xs text-gray-500">Tasks</p>
                </div>
              </div>

              <ProgressBar
                value={s.comprehension || 0}
                max={100}
                color={s.status === 'needs_attention' ? 'red' : s.status === 'on_track' ? 'green' : 'teal'}
              />

              <div className="flex gap-2 mt-3 flex-wrap">
                {s.profile && (
                  <Badge color="teal" className="text-xs">
                    {s.profile.replace('_', ' ')}
                  </Badge>
                )}
                {!s.screeningDone && <Badge color="gray" className="text-xs">No screening</Badge>}
                {!s.planGenerated && s.screeningDone && <Badge color="amber" className="text-xs">No plan</Badge>}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
