/**
 * frontend/src/pages/student/ReadingCoachPage.jsx — DyslexAid V2 Adaptive Reading Coach.
 *
 * Dedicated page for adaptive reading practice:
 * - Active coach experience (reading, listening, word support, comprehension)
 * - Reading library & personal reading stats overview
 * - Safe fallback for unscreened / fresh learners
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { readingV2API } from '../../api/v2/client'
import { ReadingCoach } from '../../features/reading'

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
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Page Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 shadow-sm border border-stone-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">📖</span>
            <span className="text-xs font-bold uppercase tracking-wider text-teal-700">
              DyslexAid Coach
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-stone-900 leading-tight">
            Adaptive Reading Coach
          </h1>
          <p className="text-xs sm:text-sm text-stone-600 mt-1">
            Personalized stories calibrated for your reading sweet spot with font, speech, and word support.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 bg-stone-100 p-1.5 rounded-2xl border border-stone-200">
          <button
            onClick={() => setActiveTab('coach')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
              activeTab === 'coach'
                ? 'bg-white text-teal-900 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            Today's Reading
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
              activeTab === 'stats'
                ? 'bg-white text-teal-900 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            My Stats & History
          </button>
        </div>
      </div>

      {/* Unscreened Learner Welcome Card */}
      {isUnscreened && (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-3xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🌱</span>
            <div>
              <p className="text-sm font-bold text-amber-950">Welcome to your reading journey!</p>
              <p className="text-xs text-amber-900">
                You can start reading right away at Level 1, or take the 5-minute screening to personalize your stories.
              </p>
            </div>
          </div>
          <Link
            to="/student/screening"
            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold shadow-2xs whitespace-nowrap"
          >
            Take Screening Test →
          </Link>
        </div>
      )}

      {/* Main Content Area */}
      {activeTab === 'coach' ? (
        <ReadingCoach />
      ) : (
        /* Reading Stats & History Tab */
        <div className="space-y-6">
          {statsLoading ? (
            <div className="p-12 text-center text-stone-500 font-medium">Loading your reading progress...</div>
          ) : (
            <>
              {/* Stat Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-3xl border border-stone-200 text-center shadow-2xs">
                  <span className="text-2xl block mb-1">📚</span>
                  <span className="text-2xl font-extrabold text-stone-900 block">
                    {stats?.totalSessions || 0}
                  </span>
                  <span className="text-xs text-stone-500 font-medium">Stories Read</span>
                </div>

                <div className="bg-white p-5 rounded-3xl border border-stone-200 text-center shadow-2xs">
                  <span className="text-2xl block mb-1">⏱️</span>
                  <span className="text-2xl font-extrabold text-stone-900 block">
                    {stats?.totalMinutesRead || 0}m
                  </span>
                  <span className="text-xs text-stone-500 font-medium">Total Minutes</span>
                </div>

                <div className="bg-white p-5 rounded-3xl border border-stone-200 text-center shadow-2xs">
                  <span className="text-2xl block mb-1">🎯</span>
                  <span className="text-2xl font-extrabold text-stone-900 block">
                    {stats?.avgComprehensionAccuracy || 0}%
                  </span>
                  <span className="text-xs text-stone-500 font-medium">Avg Comprehension</span>
                </div>

                <div className="bg-white p-5 rounded-3xl border border-stone-200 text-center shadow-2xs">
                  <span className="text-2xl block mb-1">⭐</span>
                  <span className="text-2xl font-extrabold text-stone-900 block">
                    Level {stats?.currentTier || 1}
                  </span>
                  <span className="text-xs text-stone-500 font-medium">Current Tier</span>
                </div>
              </div>

              {/* Recent Sessions List */}
              <div className="bg-white rounded-3xl p-6 sm:p-7 border border-stone-200 shadow-2xs">
                <h3 className="text-base font-bold text-stone-900 mb-4 flex items-center gap-2">
                  <span>📜</span> Recent Reading Sessions
                </h3>

                {(!stats?.recentSessions || stats.recentSessions.length === 0) ? (
                  <div className="text-center py-8 text-stone-500 text-sm">
                    No completed sessions yet. Start your first story today!
                  </div>
                ) : (
                  <div className="space-y-3">
                    {stats.recentSessions.map((s, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-2xl bg-stone-50 border border-stone-200 flex flex-wrap items-center justify-between gap-3"
                      >
                        <div>
                          <p className="font-bold text-stone-900 text-sm">
                            {s.passageId} • Level {s.difficulty}
                          </p>
                          <p className="text-xs text-stone-500">
                            Mode: {s.readingMode} • {s.wordsRead || 0} words • {Math.round((s.durationSeconds || 0) / 60)} mins
                          </p>
                        </div>

                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold bg-teal-100 text-teal-800 px-3 py-1 rounded-full border border-teal-200">
                            {s.comprehensionAccuracy || s.comprehensionScore || 0}% Accuracy
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
