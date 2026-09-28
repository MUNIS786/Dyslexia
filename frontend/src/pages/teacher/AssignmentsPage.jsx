import { useEffect, useState, useRef } from 'react'
import { assignmentsAPI, progressAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, ProgressBar, Spinner, EmptyState, Select, Textarea } from '../../components/ui'
import toast from 'react-hot-toast'

const LANGUAGES = [
  { value: 'en', label: '🇬🇧 English' },
  { value: 'hi', label: '🇮🇳 Hindi' },
  { value: 'ta', label: '🇮🇳 Tamil' },
  { value: 'mr', label: '🇮🇳 Marathi' },
]
const DUE_OPTIONS = [
  { value: '1', label: 'Tomorrow' },
  { value: '3', label: 'In 3 days' },
  { value: '7', label: 'In 1 week' },
  { value: '14', label: 'In 2 weeks' },
]

export default function AssignmentsPage() {
  const [tab, setTab] = useState('list') // list | create
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [form, setForm] = useState({
    title: '',
    description: '',
    originalText: '',
    language: 'en',
    dueInDays: '7',
    maxScore: '100',
  })
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadMode, setUploadMode] = useState('text') // text | file
  const [deletingId, setDeletingId] = useState(null)
  const fileRef = useRef(null)

  useEffect(() => {
    loadAssignments()
  }, [])

  const loadAssignments = () => {
    setLoading(true)
    assignmentsAPI.list()
      .then(setAssignments)
      .catch(() => toast.error('Could not load assignments.'))
      .finally(() => setLoading(false))
  }

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleCreate = async () => {
    if (!form.title.trim()) { toast.error('Please enter a title.'); return }
    setSubmitting(true)
    try {
      if (uploadMode === 'file' && uploadFile) {
        const fd = new FormData()
        fd.append('file', uploadFile)
        fd.append('title', form.title)
        fd.append('description', form.description)
        fd.append('language', form.language)
        fd.append('dueInDays', form.dueInDays)
        await assignmentsAPI.uploadAndCreate(fd)
      } else {
        if (!form.originalText.trim()) { toast.error('Please enter assignment text.'); setSubmitting(false); return }
        await assignmentsAPI.create({
          ...form,
          dueInDays: parseInt(form.dueInDays),
          maxScore: parseInt(form.maxScore),
        })
      }
      toast.success('✅ Assignment created!')
      setForm({ title: '', description: '', originalText: '', language: 'en', dueInDays: '7', maxScore: '100' })
      setUploadFile(null)
      setTab('list')
      loadAssignments()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not create assignment.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this assignment?')) return
    setDeletingId(id)
    try {
      await assignmentsAPI.delete(id)
      setAssignments((prev) => prev.filter((a) => a.id !== id))
      toast.success('Deleted.')
    } catch {
      toast.error('Could not delete.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader icon="📝" title="Assignments" subtitle="Create and manage class assignments." />

      {/* Tabs */}
      <div className="flex gap-2 bg-white rounded-xl p-1 border border-[#E5E0D8]">
        {[
          { id: 'list', label: '📋 My Assignments' },
          { id: 'create', label: '+ Create New' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-2.5 rounded-lg dyslexia-text text-sm font-semibold transition-all
              ${tab === t.id ? 'bg-[#1A6B6B] text-white' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* LIST TAB */}
      {tab === 'list' && (
        loading ? (
          <div className="flex justify-center py-10"><Spinner size="lg" /></div>
        ) : assignments.length === 0 ? (
          <EmptyState
            icon="📝"
            title="No assignments yet"
            message="Create your first assignment for your class."
            action={<Button onClick={() => setTab('create')}>+ Create Assignment</Button>}
          />
        ) : (
          <div className="flex flex-col gap-4">
            {assignments.map((a) => {
              const isExpanded = expanded === a.id
              const isOverdue = a.dueDate && new Date(a.dueDate) < new Date()
              const subPct = a.totalStudents > 0
                ? Math.round((a.submissionCount / a.totalStudents) * 100) : 0

              return (
                <Card key={a.id}>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <p className="dyslexia-text font-bold">{a.title}</p>
                        {isOverdue && <Badge color="red">Overdue</Badge>}
                      </div>
                      {a.description && (
                        <p className="dyslexia-text text-sm text-gray-500">{a.description}</p>
                      )}
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {a.language && <Badge color="teal">{a.language.toUpperCase()}</Badge>}
                        {a.dueDate && (
                          <Badge color="gray">
                            Due {new Date(a.dueDate).toLocaleDateString('en-IN')}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => setExpanded(isExpanded ? null : a.id)}
                        className="px-3 py-1.5 rounded-lg bg-gray-100 dyslexia-text text-sm hover:bg-gray-200"
                      >
                        {isExpanded ? '▲ Hide' : '▼ Show'}
                      </button>
                      <button
                        onClick={() => handleDelete(a.id)}
                        disabled={deletingId === a.id}
                        className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-red-50 text-red-400"
                      >
                        🗑
                      </button>
                    </div>
                  </div>

                  <ProgressBar
                    value={a.submissionCount || 0}
                    max={a.totalStudents || 1}
                    label={`${a.submissionCount || 0} / ${a.totalStudents || 0} submitted`}
                    color="teal"
                  />

                  {isExpanded && (a.submissions || []).length > 0 && (
                    <div className="mt-4 flex flex-col gap-2">
                      <p className="dyslexia-text font-semibold text-sm">Submissions:</p>
                      {a.submissions.map((sub, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-gray-50">
                          <div>
                            <p className="dyslexia-text text-sm font-medium">{sub.studentName}</p>
                            <p className="dyslexia-text text-xs text-gray-400">
                              {new Date(sub.submittedAt).toLocaleDateString('en-IN')}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {sub.score != null && <Badge color="teal">{sub.score} pts</Badge>}
                            {sub.graded ? (
                              <Badge color="green">Graded</Badge>
                            ) : (
                              <Badge color="amber">Ungraded</Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {isExpanded && (a.submissions || []).length === 0 && (
                    <p className="dyslexia-text text-sm text-gray-400 mt-3 text-center">No submissions yet.</p>
                  )}
                </Card>
              )
            })}
          </div>
        )
      )}

      {/* CREATE TAB */}
      {tab === 'create' && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-4">✏️ New Assignment</h2>

          {/* Input mode toggle */}
          <div className="flex gap-2 mb-4 bg-gray-100 rounded-xl p-1">
            {[
              { id: 'text', label: '✏️ Type Text' },
              { id: 'file', label: '📁 Upload File' },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => setUploadMode(m.id)}
                className={`flex-1 py-2 rounded-lg dyslexia-text text-sm font-semibold transition-all
                  ${uploadMode === m.id ? 'bg-white shadow-sm text-[#1A6B6B]' : 'text-gray-500'}`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-4">
            <div>
              <label className="dyslexia-text font-semibold block mb-1">📌 Title</label>
              <input
                className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                  focus:outline-none focus:border-[#1A6B6B]"
                placeholder="Assignment title"
                value={form.title}
                onChange={set('title')}
              />
            </div>

            <div>
              <label className="dyslexia-text font-semibold block mb-1">📝 Description (optional)</label>
              <textarea
                className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                  focus:outline-none focus:border-[#1A6B6B] resize-none"
                rows={2}
                placeholder="Instructions for students"
                value={form.description}
                onChange={set('description')}
              />
            </div>

            <Select label="🌐 Language" value={form.language} onChange={set('language')} options={LANGUAGES} />
            <Select label="📅 Due In" value={form.dueInDays} onChange={set('dueInDays')} options={DUE_OPTIONS} />

            {uploadMode === 'text' ? (
              <div>
                <label className="dyslexia-text font-semibold block mb-1">📄 Assignment Text</label>
                <textarea
                  className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                    focus:outline-none focus:border-[#1A6B6B] resize-none"
                  rows={6}
                  placeholder="Paste or type the assignment text here…"
                  value={form.originalText}
                  onChange={set('originalText')}
                />
              </div>
            ) : (
              <div>
                <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx" className="hidden"
                  onChange={(e) => setUploadFile(e.target.files[0])} />
                <div
                  onClick={() => fileRef.current?.click()}
                  className="border-2 border-dashed border-[#1A6B6B] rounded-xl p-6 text-center cursor-pointer hover:bg-[#E0F2F2]"
                >
                  <p className="text-3xl mb-2">📤</p>
                  <p className="dyslexia-text text-sm text-[#1A6B6B] font-semibold">
                    {uploadFile ? uploadFile.name : 'Click to select a file'}
                  </p>
                  <p className="dyslexia-text text-xs text-gray-400 mt-1">
                    PDF, image, Word, or text — auto OCR + dyslexia-friendly conversion
                  </p>
                </div>
              </div>
            )}

            <div>
              <label className="dyslexia-text font-semibold block mb-1">🏆 Max Score</label>
              <input
                type="number"
                className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                  focus:outline-none focus:border-[#1A6B6B]"
                placeholder="100"
                value={form.maxScore}
                onChange={set('maxScore')}
              />
            </div>

            <Button onClick={handleCreate} loading={submitting} size="lg" className="w-full">
              📝 Create Assignment
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
