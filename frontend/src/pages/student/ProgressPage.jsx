import { useEffect, useState } from 'react'
import { progressAPI, planAPI } from '../../api/client'
import { Card, StatCard, Badge, PageHeader, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function ProgressPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [p] = await Promise.all([progressAPI.summary()])
        setData(p)
        // Silent plan adaptation check
        planAPI.checkAdapt().then((res) => {
          if (res?.adapted) toast.success('🔄 Your learning plan has been updated!')
        }).catch(() => {})
      } catch {
        toast.error('Could not load progress.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )
  if (!data) return null

  const weeklyValues = Object.values(data.weeklyActivity || {})
  const maxWeekly = Math.max(...weeklyValues, 1)
  const comprScores = (data.comprehensionScores || []).slice(-10)
  const maxCompr = Math.max(...comprScores, 1)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader icon="📊" title="My Progress" subtitle="See how far you have come!" />

      {/* Level badge */}
      {data.levelLabel && (
        <div className="flex items-center gap-3">
          <span className="dyslexia-text font-bold text-slate-500">Current Level:</span>
          <Badge color="indigo" className="text-base px-4 py-1">
            🏆 {data.levelLabel}
          </Badge>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard icon="📄" label="Docs Scanned" value={data.docsScanned} color="indigo" />
        <StatCard icon="📖" label="Words Read" value={(data.wordsRead || 0).toLocaleString()} color="amber" />
        <StatCard icon="🔥" label="Day Streak" value={data.streak || 0} sub="days in a row" color="amber" />
        <StatCard icon="🎯" label="Avg Score" value={`${data.avgComprehension || 0}%`} color="green" />
        <StatCard icon="⭐" label="Words Mastered" value={data.wordsMastered || 0} color="indigo" />
        <StatCard icon="📅" label="Sessions" value={data.sessionCount || 0} color="green" />
      </div>

      {/* Weekly activity chart */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">📅 This Week's Activity</h2>
        <div className="flex items-end gap-2 h-32" role="region" aria-label="Weekly activity bar chart">
          {DAYS.map((day, i) => {
            const val = weeklyValues[i] || 0
            const h = Math.round((val / maxWeekly) * 100)
            return (
              <div key={day} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex items-end justify-center" style={{ height: '80px' }}>
                  <div
                    role="img"
                    aria-label={`${day}: ${val} minutes`}
                    className="w-full rounded-t-lg bg-indigo-600 hover:bg-indigo-700 transition-all"
                    style={{ height: `${Math.max(h, 4)}%`, minHeight: val > 0 ? '8px' : '4px' }}
                    title={`${day}: ${val} minutes`}
                  />
                </div>
                <p className="dyslexia-text text-xs text-slate-500 font-semibold">{day}</p>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Comprehension trend */}
      {comprScores.length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-4">🎯 Comprehension Trend</h2>
          <div className="flex items-end gap-2 h-32" role="region" aria-label="Comprehension score history">
            {comprScores.map((score, i) => {
              const h = Math.round((score / 100) * 100)
              const color = score >= 70 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex items-end justify-center" style={{ height: '80px' }}>
                    <div
                      role="img"
                      aria-label={`Session ${i + 1}: ${score}% comprehension`}
                      className={`w-full rounded-t-lg ${color} transition-all`}
                      style={{ height: `${Math.max(h, 4)}%` }}
                      title={`${score}%`}
                    />
                  </div>
                  <p className="dyslexia-text text-xs text-slate-500 font-semibold">{score}%</p>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Dyslexia type if available */}
      {data.dyslexiaType && (
        <Card>
          <p className="dyslexia-text text-sm text-slate-500">Dyslexia Profile</p>
          <p className="dyslexia-text font-bold capitalize text-slate-900">{data.dyslexiaType?.replace('_', ' ')}</p>
        </Card>
      )}

      {/* Mastered words */}
      {(data.masteredWords || []).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-3">⭐ Words I've Mastered</h2>
          <div className="flex flex-wrap gap-2">
            {data.masteredWords.map((w, i) => (
              <span
                key={i}
                className="bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1 rounded-full dyslexia-text text-sm font-semibold"
              >
                {w}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Recent activity */}
      {(data.recentActivity || []).length > 0 && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-3">🕐 Recent Activity</h2>
          <div className="flex flex-col gap-2">
            {data.recentActivity.slice(0, 10).map((a, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-slate-200 last:border-0">
                <span className="text-xl">
                  {a.type === 'scan' ? '📷' : a.type === 'reading' ? '📖' : a.type === 'word' ? '⭐' : '📌'}
                </span>
                <div className="flex-1">
                  <p className="dyslexia-text text-sm text-slate-800">{a.description || a.type}</p>
                  {a.time && <p className="dyslexia-text text-xs text-slate-400">{a.time}</p>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
