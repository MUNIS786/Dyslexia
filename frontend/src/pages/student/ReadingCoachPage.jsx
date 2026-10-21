/**
 * frontend/src/pages/student/ReadingCoachPage.jsx — DyslexAid V2 Adaptive Reading Coach.
 *
 * Dedicated page for adaptive reading practice:
 * - Active coach experience (reading, listening, word support, comprehension)
 * - Reading library & personal reading stats overview
 * - Safe fallback for unscreened / fresh learners
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { readingV2API } from '../../api/v2/client'
import { ReadingCoach } from '../../features/reading'
import { Card, StatCard, Badge, Button, Spinner } from '../../components/ui'

export default function ReadingCoachPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('coach') // 'coach' | 'stats'
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)

  const isUnscreened = !user?.readingProfile?.primaryProfile && !user?.readingProfile?.type

  useEffect(() => {
    if (activeTab === 'stats') {
      setStatsLoading(true)
      readingV2API
        .getStats()
        .then((data) => setStats(data))
        .catch((err) => console.warn('Could not load reading stats:', err))
        .finally(() => setStatsLoading(false))
    }
  }, [activeTab])

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <Card className="p-5 sm:p-7 shadow-card border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">📖</span>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              DyslexAid Coach
            </span>
          </div>
          <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold text-slate-900 leading-tight">
            Adaptive Reading Coach
          </h1>
          <p className="dyslexia-text text-xs sm:text-sm text-slate-500 mt-1">
            Personalized stories calibrated for your reading sweet spot with font, speech, and word support.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1.5 rounded-2xl border border-slate-200" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'coach'}
            onClick={() => setActiveTab('coach')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
              activeTab === 'coach'
                ? 'bg-white text-indigo-700 shadow-2xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Today&apos;s Reading
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'stats'}
            onClick={() => setActiveTab('stats')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
              activeTab === 'stats'
                ? 'bg-white text-indigo-700 shadow-2xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            My Stats & History
          </button>
        </div>
      </Card>

      {/* Unscreened Learner Welcome Card */}
      {isUnscreened && (
        <Card className="border-2 border-amber-300 bg-amber-50/80 p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <span className="text-3xl">🌱</span>
            <div>
              <p className="dyslexia-text text-sm font-bold text-amber-950">Welcome to your reading journey!</p>
              <p className="dyslexia-text text-xs text-amber-900 mt-0.5">
                You can start reading right away at Level 1, or take the 5-minute screening to personalize your stories.
              </p>
            </div>
          </div>
          <Link to="/student/screening">
            <Button variant="accent" size="sm">
              Take Screening Test →
            </Button>
          </Link>
        </Card>
      )}

      {/* Main Content Area */}
      {activeTab === 'coach' ? (
        <ReadingCoach />
      ) : (
        /* Reading Stats & History Tab */
        <div className="space-y-6">
          {statsLoading ? (
            <div className="p-16 text-center flex flex-col items-center gap-3">
              <Spinner size="lg" color="primary" />
              <p className="dyslexia-text text-sm font-semibold text-slate-500">Loading your reading progress...</p>
            </div>
          ) : (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard
                  icon="📚"
                  label="Stories Read"
                  value={stats?.totalSessions || 0}
                  color="indigo"
                />
                <StatCard
                  icon="⏱️"
                  label="Total Minutes"
                  value={`${stats?.totalMinutesRead || 0}m`}
                  color="teal"
                />
                <StatCard
                  icon="🎯"
                  label="Avg Comprehension"
                  value={`${stats?.avgComprehensionAccuracy || 0}%`}
                  color="green"
                />
                <StatCard
                  icon="⭐"
                  label="Current Tier"
                  value={`Level ${stats?.currentTier || 1}`}
                  color="amber"
                />
              </div>

              {/* Recent Sessions List */}
              <Card className="p-6 sm:p-7 space-y-4">
                <h2 className="dyslexia-text text-base font-bold text-slate-900 flex items-center gap-2">
                  <span>📜</span> Recent Reading Sessions
                </h2>

                {!stats?.recentSessions || stats.recentSessions.length === 0 ? (
                  <div className="text-center py-10 text-slate-400 text-sm dyslexia-text">
                    No completed sessions yet. Start your first story today!
                  </div>
                ) : (
                  <div className="space-y-3">
                    {stats.recentSessions.map((s, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3"
                      >
                        <div>
                          <p className="dyslexia-text font-bold text-slate-900 text-sm">
                            {s.passageId} • Level {s.difficulty}
                          </p>
                          <p className="dyslexia-text text-xs text-slate-500 mt-0.5">
                            Mode: {s.readingMode} • {s.wordsRead || 0} words • {Math.round((s.durationSeconds || 0) / 60)} mins
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <Badge color="green">
                            {s.comprehensionAccuracy || s.comprehensionScore || 0}% Accuracy
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  )
}
