/**
 * frontend/src/pages/student/RewardsPage.jsx
 *
 * Dyslexia-friendly Student Learning Rewards Dashboard.
 * Celebrates practice effort, consistency streaks, and milestones without shame or competition.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { gamificationV2API } from '../../api/v2/client'
import {
  BadgeCard,
  StreakDisplay,
  MilestoneTracker,
  RewardHistoryList,
} from '../../features/gamification'
import { Card, StatCard, Button, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

export default function RewardsPage() {
  const [summary, setSummary] = useState(null)
  const [achievements, setAchievements] = useState([])
  const [milestones, setMilestones] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all') // 'all' | 'unlocked' | 'locked'

  const loadData = async () => {
    setLoading(true)
    try {
      const [sumRes, achRes, mileRes, histRes] = await Promise.all([
        gamificationV2API.getSummary().catch(() => null),
        gamificationV2API.getAchievements().catch(() => []),
        gamificationV2API.getMilestones().catch(() => []),
        gamificationV2API.getHistory({ limit: 15 }).catch(() => ({ events: [] })),
      ])

      setSummary(sumRes)
      setAchievements(achRes || [])
      setMilestones(mileRes || [])
      setHistory(histRes?.events || [])
    } catch {
      toast.error('Failed to load rewards data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filteredBadges = achievements.filter((badge) => {
    if (activeTab === 'unlocked') return badge.unlocked
    if (activeTab === 'locked') return !badge.unlocked
    return true
  })

  const unlockedCount = achievements.filter((b) => b.unlocked).length

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20 flex flex-col items-center justify-center space-y-4">
        <Spinner size="lg" color="primary" />
        <p className="dyslexia-text text-slate-600 font-semibold text-sm">Gathering your learning milestones...</p>
      </div>
    )
  }

  if (!summary) {
    return (
      <Card className="max-w-2xl mx-auto p-8 sm:p-10 text-center space-y-6 border-slate-200 mt-8">
        <div className="text-5xl" aria-hidden="true">🌱</div>
        <h1 className="dyslexia-text text-2xl font-extrabold text-slate-900">Learning Rewards & Achievements</h1>
        <p className="dyslexia-text text-slate-600 max-w-md mx-auto text-sm sm:text-base">
          Learning rewards are taking a quick rest right now, but your reading journey never stops! Keep reading and practicing at your own pace.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Link to="/student/reading-coach">
            <Button size="md">
              Go to Reading Coach 📖
            </Button>
          </Link>
          <Link to="/student">
            <Button variant="outline" size="md">
              Student Home 🏠
            </Button>
          </Link>
        </div>
      </Card>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 space-y-8">
      {/* Page Header */}
      <Card className="p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6 border-slate-200 shadow-card">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-wider">
            <span>🏆</span> My Learning Journey
          </div>
          <h1 className="dyslexia-text text-2xl sm:text-3xl font-black text-slate-900">
            Learning Rewards & Achievements
          </h1>
          <p className="dyslexia-text text-sm sm:text-base text-slate-600 max-w-xl font-medium">
            Celebrate your practice effort, consistency, and reading milestones. Every step makes your reading brain stronger!
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link to="/student/reading-coach">
            <Button size="md">
              Practice Reading 📖
            </Button>
          </Link>
          <Link to="/student/adaptive-learning">
            <Button variant="outline" size="md">
              Skill Drills 🎯
            </Button>
          </Link>
        </div>
      </Card>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon="🏆"
          label="Total Points"
          value={summary?.totalPoints || 0}
          color="amber"
        />
        <StatCard
          icon="🔥"
          label="Active Streak"
          value={`${summary?.currentStreak || 0} ${summary?.currentStreak === 1 ? 'Day' : 'Days'}`}
          color="teal"
        />
        <StatCard
          icon="🎖️"
          label="Badges Earned"
          value={`${unlockedCount} / ${achievements.length}`}
          color="green"
        />
        <StatCard
          icon="🌟"
          label="Best Record"
          value={`${summary?.longestStreak || 0} ${summary?.longestStreak === 1 ? 'Day' : 'Days'}`}
          color="indigo"
        />
      </div>

      {/* Encouraging Consistency Streak Card */}
      <StreakDisplay
        currentStreak={summary?.currentStreak || 0}
        longestStreak={summary?.longestStreak || 0}
        streakMessage={summary?.streakMessage}
        lastActiveDate={summary?.lastActiveDate}
      />

      {/* Next Milestones & Goals Tracker */}
      <MilestoneTracker milestones={milestones} />

      {/* Achievement Badges Catalogue */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="dyslexia-text text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
              <span>🏅</span> Achievements & Badges Shelf
            </h2>
            <p className="dyslexia-text text-xs sm:text-sm text-slate-500 font-medium">
              Collect badges by reading stories, answering comprehension questions, and practicing consistently.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl self-start sm:self-auto border border-slate-200" role="tablist">
            <button
              id="filter-all-badges"
              type="button"
              role="tab"
              aria-selected={activeTab === 'all'}
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
                activeTab === 'all'
                  ? 'bg-white text-slate-900 shadow-2xs font-extrabold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All ({achievements.length})
            </button>
            <button
              id="filter-unlocked-badges"
              type="button"
              role="tab"
              aria-selected={activeTab === 'unlocked'}
              onClick={() => setActiveTab('unlocked')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
                activeTab === 'unlocked'
                  ? 'bg-white text-emerald-700 shadow-2xs font-extrabold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Unlocked ({unlockedCount})
            </button>
            <button
              id="filter-locked-badges"
              type="button"
              role="tab"
              aria-selected={activeTab === 'locked'}
              onClick={() => setActiveTab('locked')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
                activeTab === 'locked'
                  ? 'bg-white text-slate-900 shadow-2xs font-extrabold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              In Progress ({achievements.length - unlockedCount})
            </button>
          </div>
        </div>

        {/* Badges Grid */}
        {loading ? (
          <Card className="p-12 text-center text-slate-500 border-slate-200">
            Loading achievement badges...
          </Card>
        ) : filteredBadges.length === 0 ? (
          <Card className="p-8 text-center text-slate-500 border-slate-200 dyslexia-text">
            No badges match the selected filter.
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredBadges.map((badge) => (
              <BadgeCard key={badge.badgeId} badge={badge} />
            ))}
          </div>
        )}
      </div>

      {/* Rewards Ledger Feed */}
      <RewardHistoryList events={history} loading={loading} />
    </div>
  )
}
