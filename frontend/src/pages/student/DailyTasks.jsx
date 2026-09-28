import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { tasksAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, Spinner, EmptyState } from '../../components/ui'
import toast from 'react-hot-toast'

const TYPE_ICON = {
  reading: '📖',
  phonics: '🔤',
  vocabulary: '⭐',
  quiz: '🧠',
  exercise: '💪',
}
const TYPE_COLOR = {
  reading: 'bg-[#E0F2F2]',
  phonics: 'bg-[#FFF3DC]',
  vocabulary: 'bg-[#F0F8FF]',
  quiz: 'bg-[#F5F0FF]',
  exercise: 'bg-green-50',
}

export default function DailyTasks() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(null)

  useEffect(() => {
    tasksAPI.today().then(setData).catch(() => toast.error('Could not load tasks.')).finally(() => setLoading(false))
  }, [])

  const completeTask = async (id) => {
    setCompleting(id)
    try {
      const res = await tasksAPI.complete(id)
      setData((prev) => ({
        ...prev,
        tasks: prev.tasks.map((t) => (t.id === id ? { ...t, completed: true } : t)),
        completed: prev.completed + 1,
      }))
      if (res.allDone) toast.success('🎉 Amazing! You finished all tasks today!')
      else toast.success('✅ Task done! Great work!')
    } catch {
      toast.error('Could not complete task.')
    } finally {
      setCompleting(null)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )

  if (!data?.hasScreening) {
    return (
      <div>
        <PageHeader icon="✅" title="Daily Tasks" />
        <EmptyState
          icon="🧠"
          title="Take your screening first"
          message="We need to know your reading level before creating tasks for you."
          action={
            <Button onClick={() => navigate('/student/screening')}>
              Start Screening →
            </Button>
          }
        />
      </div>
    )
  }

  const total = data.total || 0
  const done = data.completed || 0
  const allDone = done >= total && total > 0
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div className="flex flex-col gap-5">
      <PageHeader icon="✅" title="Daily Tasks" subtitle="Complete these to build your skills." />

      {/* Progress summary */}
      <Card className={allDone ? 'bg-green-50 border-green-200' : ''}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="dyslexia-text font-bold text-lg">
              {allDone ? '🎉 All Done!' : `${done} of ${total} tasks complete`}
            </p>
            <p className="dyslexia-text text-sm text-gray-500">
              {allDone ? 'You finished all tasks for today. See you tomorrow!' : `${total - done} task${total - done !== 1 ? 's' : ''} remaining`}
            </p>
          </div>
          <Badge color={allDone ? 'green' : done > 0 ? 'amber' : 'gray'}>
            {pct}%
          </Badge>
        </div>
        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${allDone ? 'bg-green-500' : 'bg-[#1A6B6B]'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </Card>

      {/* Task list */}
      <div className="flex flex-col gap-3">
        {(data.tasks || []).map((task) => (
          <Card
            key={task.id}
            className={task.completed ? 'opacity-70 border-green-200 bg-green-50' : ''}
          >
            <div className="flex items-start gap-4">
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0
                  ${TYPE_COLOR[task.type] || 'bg-gray-100'}`}
              >
                {TYPE_ICON[task.type] || '📌'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <p className="dyslexia-text font-bold">{task.title}</p>
                  <Badge color="gray" className="text-xs">
                    ⏱ {task.durationMinutes} min
                  </Badge>
                  {task.completed && <Badge color="green">✓ Done</Badge>}
                </div>
                {task.description && (
                  <p className="dyslexia-text text-sm text-gray-600">{task.description}</p>
                )}
              </div>
              {!task.completed && (
                <Button
                  size="sm"
                  onClick={() => completeTask(task.id)}
                  loading={completing === task.id}
                  className="shrink-0"
                >
                  Mark Done
                </Button>
              )}
              {task.completed && <span className="text-green-500 text-2xl shrink-0">✓</span>}
            </div>
          </Card>
        ))}
      </div>

      {data.message && (
        <Card className="bg-[#FFF3DC] border-[#E8A020]">
          <p className="dyslexia-text text-sm text-amber-800">💡 {data.message}</p>
        </Card>
      )}
    </div>
  )
}
