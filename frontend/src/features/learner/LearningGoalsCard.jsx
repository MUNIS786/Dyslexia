/**
 * frontend/src/features/learner/LearningGoalsCard.jsx
 * Interactive personal reading goals checklist.
 */
import React, { useState } from 'react'

export default function LearningGoalsCard({
  goals = [],
  onUpdateGoals,
}) {
  const [goalList, setGoalList] = useState(
    Array.isArray(goals) && goals.length > 0
      ? goals.map((g, idx) =>
          typeof g === 'string'
            ? { id: `goal-${idx + 1}`, title: g, completed: false }
            : { id: g.id || `goal-${idx + 1}`, title: g.title || '', completed: !!g.completed }
        )
      : [
          { id: 'goal-1', title: "Complete today's reading practice", completed: false },
          { id: 'goal-2', title: 'Master 5 new vocabulary words', completed: false },
          { id: 'goal-3', title: 'Read for 10 minutes', completed: false },
        ]
  )

  const [newGoalText, setNewGoalText] = useState('')
  const [saving, setSaving] = useState(false)

  const handleToggle = async (goalId) => {
    const updated = goalList.map((g) =>
      g.id === goalId ? { ...g, completed: !g.completed } : g
    )
    setGoalList(updated)

    if (onUpdateGoals) {
      setSaving(true)
      try {
        await onUpdateGoals({ current_goals: updated })
      } catch {
        setGoalList(goalList) // Revert on failure
      } finally {
        setSaving(false)
      }
    }
  }

  const handleAddGoal = async (e) => {
    e.preventDefault()
    if (!newGoalText.trim()) return

    const newGoal = {
      id: `goal-${Date.now()}`,
      title: newGoalText.trim(),
      completed: false,
    }

    const updated = [...goalList, newGoal]
    setGoalList(updated)
    setNewGoalText('')

    if (onUpdateGoals) {
      setSaving(true)
      try {
        await onUpdateGoals({ current_goals: updated })
      } catch {
        setGoalList(goalList)
      } finally {
        setSaving(false)
      }
    }
  }

  const completedCount = goalList.filter((g) => g.completed).length

  return (
    <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 shadow-card">
      <div className="flex items-center justify-between gap-3 mb-5">
        <div>
          <h3 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2 dyslexia-text">
            <span>🏆</span> YOUR GOALS
          </h3>
          <p className="text-xs text-slate-500">
            Check off your reading achievements and set fun new milestones
          </p>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
          {completedCount}/{goalList.length} Completed
        </span>
      </div>

      {/* Goals Checklist */}
      <div className="space-y-2.5 mb-5">
        {goalList.map((goal) => {
          return (
            <div
              key={goal.id}
              onClick={() => !saving && handleToggle(goal.id)}
              role="checkbox"
              aria-checked={goal.completed}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                  e.preventDefault()
                  handleToggle(goal.id)
                }
              }}
              className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer flex items-center gap-3.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                goal.completed
                  ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                  : 'bg-slate-50/80 border-slate-200 hover:bg-slate-100/70 text-slate-800'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 transition-all ${
                  goal.completed
                    ? 'bg-emerald-500 text-white shadow-sm'
                    : 'border-2 border-slate-300 bg-white'
                }`}
              >
                {goal.completed && '✓'}
              </div>

              <span
                className={`text-sm sm:text-base dyslexia-text font-medium flex-1 ${
                  goal.completed ? 'line-through text-slate-400' : 'text-slate-900'
                }`}
              >
                {goal.title}
              </span>
            </div>
          )
        })}
      </div>

      {/* Add New Goal Form */}
      <form onSubmit={handleAddGoal} className="flex gap-2">
        <input
          type="text"
          value={newGoalText}
          onChange={(e) => setNewGoalText(e.target.value)}
          placeholder="Add a new reading goal (e.g. Read chapter 3)..."
          className="flex-1 px-4 py-2.5 rounded-2xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium dyslexia-text"
        />
        <button
          type="submit"
          disabled={!newGoalText.trim() || saving}
          className="px-4 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white text-sm font-bold shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-40"
        >
          + Add
        </button>
      </form>
    </div>
  )
}
