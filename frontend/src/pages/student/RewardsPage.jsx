/**
 * frontend/src/pages/student/RewardsPage.jsx
 *
 * Dyslexia-friendly Student Learning Rewards Dashboard.
 * Celebrates practice effort, consistency streaks, and milestones without shame or competition.
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { gamificationV2API } from '../../api/v2/client'
import {
  BadgeCard,
  StreakDisplay,
  MilestoneTracker,
  RewardHistoryList,
} from '../../features/gamification'
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
    } catch (err) {
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
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-stone-600 font-medium">Gathering your learning milestones...</p>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6 bg-white rounded-3xl border border-stone-200 shadow-sm mt-8">
        <div className="text-5xl" aria-hidden="true">🌱</div>
        <h1 className="text-2xl font-bold text-stone-900">Learning Rewards & Achievements</h1>
        <p className="text-stone-600 max-w-md mx-auto">
          Learning rewards are taking a quick rest right now, but your reading journey never stops! Keep reading and practicing at your own pace.
        </p>
        <div className="flex justify-center gap-4 pt-2">
          <Link
            to="/student/reading-coach"
            className="px-5 py-2.5 rounded-xl bg-teal-800 hover:bg-teal-900 text-white font-bold text-sm shadow-sm transition-all"
          >
            Go to Reading Coach 📖
          </Link>
          <Link
            to="/student"
            className="px-5 py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-800 font-bold text-sm border border-stone-300 transition-all"
          >
            Student Home 🏠
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white rounded-3xl p-6 sm:p-8 border border-stone-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-teal-800 uppercase tracking-wider mb-1">
            <span>🏆</span> My Learning Journey
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-stone-900">
            Learning Rewards & Achievements
          </h1>
          <p className="text-sm sm:text-base text-stone-600 mt-1 max-w-xl font-medium">
            Celebrate your practice effort, consistency, and reading milestones. Every step makes your reading brain stronger!
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/student/reading-coach"
            className="px-5 py-2.5 rounded-xl bg-teal-800 hover:bg-teal-900 text-white font-bold text-sm shadow-sm transition-all focus:ring-2 focus:ring-teal-600 focus:outline-none"
          >
            Practice Reading 📖
          </Link>
          <Link
            to="/student/adaptive-learning"
            className="px-5 py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-800 font-bold text-sm border border-stone-300 transition-all focus:ring-2 focus:ring-stone-400 focus:outline-none"
          >
            Skill Drills 🎯
          </Link>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div id="stat-total-points" className="bg-white rounded-2xl p-5 border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-500 uppercase">Total Points</span>
            <span className="text-xl" aria-hidden="true">🏆</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-amber-900">
            {summary?.totalPoints || 0}
          </p>
          <span className="text-xs text-stone-500 font-medium mt-1 block">Earned through practice</span>
        </div>

        <div id="stat-current-streak" className="bg-white rounded-2xl p-5 border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-500 uppercase">Active Streak</span>
            <span className="text-xl" aria-hidden="true">✨</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-teal-900">
            {summary?.currentStreak || 0} {summary?.currentStreak === 1 ? 'Day' : 'Days'}
          </p>
          <span className="text-xs text-stone-500 font-medium mt-1 block">Consecutive days active</span>
        </div>

        <div id="stat-badges-earned" className="bg-white rounded-2xl p-5 border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-500 uppercase">Badges Earned</span>
            <span className="text-xl" aria-hidden="true">🎖️</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-emerald-900">
            {unlockedCount} / {achievements.length}
          </p>
          <span className="text-xs text-stone-500 font-medium mt-1 block">Achievements unlocked</span>
        </div>

        <div id="stat-longest-streak" className="bg-white rounded-2xl p-5 border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-500 uppercase">Best Record</span>
            <span className="text-xl" aria-hidden="true">🌟</span>
          </div>
          <p className="text-2xl sm:text-3xl font-black text-indigo-900">
            {summary?.longestStreak || 0} {summary?.longestStreak === 1 ? 'Day' : 'Days'}
          </p>
          <span className="text-xs text-stone-500 font-medium mt-1 block">Longest practice streak</span>
        </div>
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
            <h3 className="text-lg font-bold text-stone-900 flex items-center gap-2">
              <span>🏅</span> Achievements & Badges Shelf
            </h3>
            <p className="text-xs text-stone-600 font-medium">
              Collect badges by reading stories, answering comprehension questions, and practicing consistently.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 bg-stone-100 p-1 rounded-xl self-start sm:self-auto border border-stone-200/80">
            <button
              id="filter-all-badges"
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'all'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              All ({achievements.length})
            </button>
            <button
              id="filter-unlocked-badges"
              onClick={() => setActiveTab('unlocked')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'unlocked'
                  ? 'bg-white text-emerald-800 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Unlocked ({unlockedCount})
            </button>
            <button
              id="filter-locked-badges"
              onClick={() => setActiveTab('locked')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'locked'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              In Progress ({achievements.length - unlockedCount})
            </button>
          </div>
        </div>

        {/* Badges Grid */}
        {loading ? (
          <div className="bg-white rounded-2xl p-12 text-center text-stone-500 border border-stone-200">
            Loading achievement badges...
          </div>
        ) : filteredBadges.length === 0 ? (
          <div className="bg-white rounded-2xl p-8 text-center text-stone-600 border border-stone-200">
            No badges match the selected filter.
          </div>
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
