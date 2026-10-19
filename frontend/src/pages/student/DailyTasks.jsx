import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { tasksAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, Spinner, EmptyState, ProgressBar } from '../../components/ui'
import toast from 'react-hot-toast'

const TYPE_ICON = {
  reading: '📖',
  phonics: '🔤',
  vocabulary: '⭐',
  quiz: '🧠',
  exercise: '💪',
}

const TYPE_BADGE = {
  reading: 'teal',
  phonics: 'amber',
  vocabulary: 'indigo',
  quiz: 'purple',
  exercise: 'green',
}

export default function DailyTasks() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(null)

  useEffect(() => {
    tasksAPI
      .today()
      .then(setData)
      .catch(() => toast.error('Could not load tasks.'))
      .finally(() => setLoading(false))
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

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" color="primary" />
      </div>
    )
  }

  if (!data?.hasScreening) {
    return (
      <div className="space-y-4">
        <PageHeader icon="✅" title="Daily Tasks" />
        <EmptyState
          icon="🧠"
          title="Take your screening first"
          message="We need to discover your reading profile before personalizing tasks for you."
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
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      <PageHeader
        icon="✅"
        title="Daily Tasks"
        subtitle="Complete your daily micro-practices to build lasting reading skills."
      />

      {/* Progress summary */}
      <Card className={`p-6 sm:p-7 space-y-4 border-slate-200 ${allDone ? 'bg-emerald-50/60 border-emerald-300' : ''}`}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="dyslexia-text font-bold text-lg text-slate-900">
              {allDone ? '🎉 All Done for Today!' : `${done} of ${total} Tasks Complete`}
            </h2>
            <p className="dyslexia-text text-sm text-slate-500 mt-0.5">
              {allDone
                ? 'Fantastic work! You completed all scheduled activities.'
                : `${total - done} task${total - done !== 1 ? 's' : ''} remaining today`}
            </p>
          </div>
          <Badge color={allDone ? 'green' : done > 0 ? 'amber' : 'gray'} className="text-sm font-bold">
            {pct}%
          </Badge>
        </div>

        <ProgressBar
          value={done}
          max={total || 1}
          color={allDone ? 'green' : 'indigo'}
          showValue={false}
        />
      </Card>

      {/* Task list */}
      <div className="flex flex-col gap-3.5">
        {(data.tasks || []).map((task) => (
          <Card
            key={task.id}
            className={`p-4 sm:p-5 transition-all ${
              task.completed
                ? 'opacity-70 border-emerald-200 bg-emerald-50/30'
                : 'border-slate-200 shadow-2xs hover:border-indigo-300'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3.5 min-w-0">
                <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center text-2xl shrink-0 mt-0.5">
                  {TYPE_ICON[task.type] || '📌'}
                </div>
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="dyslexia-text font-bold text-base text-slate-900">{task.title}</p>
                    <Badge color={TYPE_BADGE[task.type] || 'gray'} className="text-xs">
                      {task.type}
                    </Badge>
                    <Badge color="gray" className="text-xs">
                      ⏱ {task.durationMinutes} min
                    </Badge>
                    {task.completed && <Badge color="green">✓ Done</Badge>}
                  </div>
                  {task.description && (
                    <p className="dyslexia-text text-sm text-slate-600 leading-relaxed">{task.description}</p>
                  )}
                </div>
              </div>

              {!task.completed ? (
                <Button
                  size="sm"
                  onClick={() => completeTask(task.id)}
                  loading={completing === task.id}
                  className="shrink-0"
                >
                  Mark Done
                </Button>
              ) : (
                <span className="text-emerald-600 font-bold text-2xl shrink-0 px-2" aria-label="Completed">
                  ✓
                </span>
              )}
            </div>
          </Card>
        ))}
      </div>

      {data.message && (
        <Card className="bg-amber-50/80 border-amber-200 p-4">
          <p className="dyslexia-text text-sm font-medium text-amber-900 flex items-center gap-2">
            <span>💡</span>
            <span>{data.message}</span>
          </p>
        </Card>
      )}
    </div>
  )
}
