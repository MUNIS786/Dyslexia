import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Card, Button, StatCard, Badge, EmptyState, PageHeader, Spinner, Modal } from '../../components/ui'
import { useTranslation } from '../../i18n/I18nContext'
import { parentV2API } from '../../api/v2/client'
import LinkChildModal from './LinkChildModal'
import { ParentProgressSection } from '../../components/insights'
import { ParentSuggestedPracticeCard } from '../../components/recommendations'

export default function ParentDashboard() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [dashboardData, setDashboardData] = useState(null)
  const [selectedLearnerId, setSelectedLearnerId] = useState(null)
  const [linkModalOpen, setLinkModalOpen] = useState(false)
  const [revokeConfirmId, setRevokeConfirmId] = useState(null)
  const [revoking, setRevoking] = useState(false)

  const fetchDashboard = useCallback(async (studentId = null) => {
    try {
      setLoading(true)
      const data = await parentV2API.getDashboard(studentId)
      setDashboardData(data)
      if (data.selectedLearner) {
        setSelectedLearnerId(data.selectedLearner.studentId)
      } else {
        setSelectedLearnerId(null)
      }
    } catch (err) {
      toast.error(t('parent.loadFailed', 'Failed to load parent dashboard.'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    fetchDashboard(selectedLearnerId)
  }, [selectedLearnerId, fetchDashboard])

  const handleSelectLearner = (studentId) => {
    if (studentId !== selectedLearnerId) {
      setSelectedLearnerId(studentId)
      fetchDashboard(studentId)
    }
  }

  const handleRevoke = async () => {
    if (!revokeConfirmId) return
    setRevoking(true)
    try {
      await parentV2API.revokeLink(revokeConfirmId)
      toast.success(t('parent.revokedSuccess', 'Relationship connection revoked.'))
      setRevokeConfirmId(null)
      fetchDashboard(null)
    } catch (err) {
      toast.error(t('parent.revokeFailed', 'Failed to revoke connection.'))
    } finally {
      setRevoking(false)
    }
  }

  if (loading && !dashboardData) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Spinner size="lg" />
        <p className="dyslexia-text text-gray-500">{t('common.loading', 'Loading parent portal...')}</p>
      </div>
    )
  }

  const hasLearners = dashboardData?.hasLinkedLearners && dashboardData?.selectedLearner
  const learner = dashboardData?.selectedLearner
  const overview = dashboardData?.overview
  const recentReading = dashboardData?.recentReadingSessions || []
  const recentAdaptive = dashboardData?.recentAdaptiveActivities || []
  const gamification = dashboardData?.gamificationSummary
  const trends = dashboardData?.trends
  const suggestions = dashboardData?.homeSuggestions || []

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <PageHeader
        icon="👨‍👩‍👧"
        title={t('parent.portalTitle', 'Parent & Guardian Portal')}
        subtitle={t('parent.portalSubtitle', 'Encouraging reading progress, effort tracking, and home learning activities')}
        action={
          <Button onClick={() => setLinkModalOpen(true)} variant="primary">
            ➕ {t('parent.linkChildBtn', 'Link a Child')}
          </Button>
        }
      />

      {/* Linked Children Switcher Tabs (if multiple children) */}
      {dashboardData?.linkedLearners?.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200">
          <span className="text-sm font-semibold text-slate-500 dyslexia-text mr-1">
            {t('parent.yourLearners', 'Learners:')}
          </span>
          {dashboardData.linkedLearners.map((item) => (
            <button
              key={item.studentId}
              type="button"
              onClick={() => handleSelectLearner(item.studentId)}
              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2 dyslexia-text ${
                selectedLearnerId === item.studentId
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span>🧑‍🎓</span>
              <span>{item.studentName}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-white/20 capitalize">
                {item.relationship}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Empty State: No linked learners */}
      {!hasLearners ? (
        <div className="flex flex-col gap-8">
          <Card className="text-center py-12 px-6 flex flex-col items-center border border-slate-200 shadow-2xs">
            <div className="text-6xl mb-4">👨‍👩‍👧‍👦</div>
            <h2 className="dyslexia-text text-2xl font-bold text-slate-900 mb-2">
              {t('parent.noLearnersTitle', 'Connect with Your Child to Get Started')}
            </h2>
            <p className="dyslexia-text text-slate-600 max-w-lg mx-auto mb-6">
              {t('parent.noLearnersMessage', 'Link your account to your child to see their reading practice time, stories completed, badges earned, and encouraging home reading tips.')}
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Button onClick={() => setLinkModalOpen(true)} size="lg">
                ✨ {t('parent.connectWithChildBtn', 'Connect with Your Child')}
              </Button>
            </div>
            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4 text-left max-w-xl">
              <div className="bg-amber-50/70 p-4 rounded-2xl border border-amber-200 text-sm">
                <p className="font-bold text-amber-800 mb-1">🔑 {t('parent.step1Title', 'Have a code?')}</p>
                <p className="text-slate-600 text-xs">
                  {t('parent.step1Desc', 'Ask your child or their teacher for their 48-hour DyslexAid invitation code.')}
                </p>
              </div>
              <div className="bg-indigo-50/70 p-4 rounded-2xl border border-indigo-200 text-sm">
                <p className="font-bold text-indigo-800 mb-1">✉️ {t('parent.step2Title', 'No code yet?')}</p>
                <p className="text-slate-600 text-xs">
                  {t('parent.step2Desc', "Enter your child's student email or ID to send a secure connection request.")}
                </p>
              </div>
            </div>
          </Card>

          {/* Supportive Home Suggestions Still Visible */}
          <div>
            <h3 className="dyslexia-text text-lg font-bold text-slate-900 mb-3">
              💡 {t('parent.homeTipsTitle', 'Supportive Home Reading Suggestions')}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {suggestions.map((sug) => (
                <Card key={sug.id} className="p-4 border-l-4 border-l-amber-500 rounded-2xl border border-slate-200 shadow-2xs">
                  <p className="font-bold text-indigo-900 text-base mb-1">{sug.title}</p>
                  <p className="text-sm text-slate-600 mb-2 dyslexia-text">{sug.description}</p>
                  <p className="text-xs text-slate-600 bg-slate-50 border border-slate-200 p-2.5 rounded-xl font-medium">
                    📌 {sug.practicalTip}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Connected Learner View */
        <div className="flex flex-col gap-6">
          {/* Active Learner Banner */}
          <div className="bg-gradient-to-br from-indigo-600 via-indigo-700 to-indigo-800 text-white p-6 rounded-3xl shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center text-3xl shadow-xs">
                🌟
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="dyslexia-text text-2xl font-bold">{learner.studentName}</h2>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-white/20 uppercase font-semibold tracking-wide">
                    {learner.relationship}
                  </span>
                </div>
                <p className="text-indigo-100 text-sm dyslexia-text mt-0.5">
                  {t('parent.activeLearnerStatus', 'Connected & verified learner profile')}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                className="text-white hover:bg-white/10 hover:text-white text-xs border border-white/30 rounded-xl"
                onClick={() => setRevokeConfirmId(learner.id)}
              >
                ⚙️ {t('parent.disconnectLearner', 'Disconnect')}
              </Button>
            </div>
          </div>

          {/* Overview Key Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <StatCard
              icon="📖"
              label={t('parent.statStories', 'Stories Read')}
              value={overview?.storiesCompleted || 0}
              sub={`${overview?.totalReadingMinutes || 0} ${t('parent.mins', 'mins read')}`}
              color="indigo"
            />
            <StatCard
              icon="🎯"
              label={t('parent.statComprehension', 'Comprehension')}
              value={overview?.avgComprehensionScore != null ? `${overview.avgComprehensionScore}%` : '—'}
              sub={t('parent.understandingRate', 'Average score')}
              color="amber"
            />
            <StatCard
              icon="⚡"
              label={t('parent.statDifficulty', 'Reading Level')}
              value={`Tier ${overview?.currentDifficultyTier || 1}`}
              sub={t('parent.adaptiveTier', 'Adaptive Level')}
              color="green"
            />
            <StatCard
              icon="🔥"
              label={t('parent.statStreak', 'Active Streak')}
              value={`${overview?.currentStreak || 0} ${t('common.days', 'Days')}`}
              sub={`${t('parent.bestStreak', 'Best:')} ${overview?.longestStreak || 0} ${t('common.days', 'd')}`}
              color="amber"
            />
            <StatCard
              icon="🌟"
              label={t('parent.statPoints', 'Practice Points')}
              value={overview?.totalPoints || 0}
              sub={t('parent.effortReward', 'Effort rewards')}
              color="indigo"
            />
            <StatCard
              icon="🏆"
              label={t('parent.statBadges', 'Milestones')}
              value={overview?.badgesEarnedCount || 0}
              sub={t('parent.badgesEarned', 'Badges unlocked')}
              color="green"
            />
          </div>

          {/* Phase 13: Multi-window Learning Insights & Consistency Progress */}
          <ParentProgressSection studentId={learner.studentId} />

          {/* Phase 14: Personalized Home Practice Recommendations & Reading Tips */}
          <ParentSuggestedPracticeCard studentId={learner.studentId} />

          {/* Main 2-Column Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Columns: Practice Details & Trends */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              {/* Recent Reading Sessions */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="dyslexia-text text-lg font-bold text-slate-900 flex items-center gap-2">
                    <span>📖</span>
                    {t('parent.recentReadingTitle', 'Recent Reading Practice')}
                  </h3>
                  <Badge color="indigo">{recentReading.length} {t('parent.sessions', 'sessions')}</Badge>
                </div>

                {recentReading.length === 0 ? (
                  <p className="text-slate-500 text-sm italic py-4 text-center dyslexia-text">
                    {t('parent.noReadingYet', 'No completed reading sessions recorded yet.')}
                  </p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {recentReading.map((session, idx) => (
                      <div
                        key={session.id || idx}
                        className="flex flex-wrap items-center justify-between p-3.5 rounded-2xl border border-slate-200 hover:border-indigo-300 transition-colors bg-white gap-2"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-xl text-indigo-600">
                            📄
                          </div>
                          <div>
                            <p className="font-bold text-slate-900 dyslexia-text">{session.title}</p>
                            <p className="text-xs text-slate-500 dyslexia-text">
                              {session.date} • {session.wordsRead} {t('parent.words', 'words')} • Tier {session.difficultyTier}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {session.comprehensionScore != null && (
                            <span className="text-sm font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-lg border border-indigo-100">
                              {session.comprehensionScore}%
                            </span>
                          )}
                          <span className="text-xs text-slate-400">
                            {session.durationMinutes} min
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Adaptive Skill Exercises */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="dyslexia-text text-lg font-bold text-slate-900 flex items-center gap-2">
                    <span>🎯</span>
                    {t('parent.recentAdaptiveTitle', 'Adaptive Skill Challenges')}
                  </h3>
                  <Badge color="amber">{recentAdaptive.length} {t('parent.activities', 'tasks')}</Badge>
                </div>

                {recentAdaptive.length === 0 ? (
                  <p className="text-slate-500 text-sm italic py-4 text-center dyslexia-text">
                    {t('parent.noAdaptiveYet', 'No adaptive tasks completed yet.')}
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {recentAdaptive.map((act, idx) => (
                      <div
                        key={act.id || idx}
                        className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50/60 flex items-center justify-between gap-2"
                      >
                        <div>
                          <p className="font-bold text-slate-900 text-sm capitalize dyslexia-text">
                            {act.domain}
                          </p>
                          <p className="text-xs text-slate-500">{act.date} • Tier {act.difficultyTier}</p>
                        </div>
                        <span className="text-sm font-bold text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-lg">
                          {act.scorePercent}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Progress Over Time & Consistency */}
              <Card>
                <h3 className="dyslexia-text text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
                  <span>📈</span>
                  {t('parent.trendsTitle', 'Progress Over Time')}
                </h3>
                <p className="text-xs text-slate-500 dyslexia-text mb-4">
                  {trends?.trendExplanation || t('parent.trendDefaultDesc', 'Learning happens in steady, natural steps. Consistency builds mastery.')}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-2">
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-white text-center">
                    <p className="text-xs text-slate-500 mb-1">{t('parent.readingTrend', 'Reading Comprehension')}</p>
                    <span className="font-bold text-sm text-indigo-700 capitalize">
                      {trends?.readingTrend === 'improving' ? '📈 Steady Growth' : trends?.readingTrend === 'stable' ? '✨ Steady Pace' : '🌱 Building Skills'}
                    </span>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-white text-center">
                    <p className="text-xs text-slate-500 mb-1">{t('parent.adaptiveTrend', 'Adaptive Practice')}</p>
                    <span className="font-bold text-sm text-amber-700 capitalize">
                      {trends?.adaptiveTrend === 'improving' ? '🚀 Active Progress' : trends?.adaptiveTrend === 'stable' ? '✨ Consistent' : '🌱 Practicing'}
                    </span>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-white text-center">
                    <p className="text-xs text-slate-500 mb-1">{t('parent.speechTrend', 'Oral Reading')}</p>
                    <span className="font-bold text-sm text-emerald-700 capitalize">
                      {trends?.speechTrend === 'improving' ? '🌟 Gaining Fluency' : trends?.speechTrend === 'stable' ? '✨ Good Flow' : '🌱 Read-Aloud Practice'}
                    </span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Right Column: Badges & Home Practice Tips */}
            <div className="flex flex-col gap-6">
              {/* Earned Badges & Milestones */}
              <Card>
                <h3 className="dyslexia-text text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <span>🏆</span>
                  {t('parent.badgesTitle', 'Earned Achievements')}
                </h3>

                {gamification?.earnedBadges?.length === 0 ? (
                  <div className="text-center py-6 text-slate-400">
                    <div className="text-3xl mb-1">🌱</div>
                    <p className="text-sm dyslexia-text">{t('parent.noBadgesYet', 'Achievements will appear here as your child completes reading practice.')}</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2.5">
                    {gamification.earnedBadges.slice(0, 4).map((badge) => (
                      <div
                        key={badge.badgeId}
                        className="flex items-center gap-3 p-3 rounded-2xl border border-slate-200 bg-slate-50/60"
                      >
                        <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200/60 flex items-center justify-center text-xl shrink-0">
                          {badge.icon || '🏅'}
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-sm text-slate-900 truncate dyslexia-text">{badge.title}</p>
                          <p className="text-xs text-slate-500 line-clamp-1 dyslexia-text">{badge.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Supportive Home Practice Tips */}
              <Card className="border-t-4 border-t-indigo-600">
                <h3 className="dyslexia-text text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <span>💡</span>
                  {t('parent.homePracticeTitle', 'At-Home Support Tips')}
                </h3>
                <div className="flex flex-col gap-3">
                  {suggestions.map((sug) => (
                    <div key={sug.id} className="p-3.5 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="font-bold text-indigo-800 text-sm mb-1 dyslexia-text">{sug.title}</p>
                      <p className="text-xs text-slate-600 mb-1.5 dyslexia-text">{sug.description}</p>
                      <p className="text-xs text-slate-600 bg-white p-2.5 rounded-xl border border-slate-200 dyslexia-text">
                        📌 {sug.practicalTip}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          {/* Educational Disclaimer Reassurance */}
          <div className="bg-amber-50/60 border border-amber-200/80 rounded-2xl p-4 flex items-start gap-3.5 text-xs text-amber-950 dyslexia-text">
            <span className="text-xl shrink-0">🛡️</span>
            <div>
              <p className="font-bold text-amber-900 mb-0.5">{t('parent.disclaimerTitle', 'Educational Support Indicator')}</p>
              <p className="leading-relaxed">{dashboardData.disclaimer}</p>
            </div>
          </div>
        </div>
      )}

      {/* Link Child Modal */}
      <LinkChildModal
        open={linkModalOpen}
        onClose={() => setLinkModalOpen(false)}
        onLinked={(link) => {
          fetchDashboard(link.studentId)
        }}
      />

      {/* Revoke Confirmation Modal */}
      <Modal
        open={Boolean(revokeConfirmId)}
        onClose={() => setRevokeConfirmId(null)}
        title={t('parent.confirmRevokeTitle', 'Disconnect Learner Connection?')}
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-600 dyslexia-text">
            {t('parent.confirmRevokeMsg', "Are you sure you want to disconnect? You will no longer have access to this learner's progress until a new invitation code or approval is completed. Historical learning records remain completely safe.")}
          </p>
          <div className="flex justify-end gap-2 mt-2">
            <Button variant="ghost" onClick={() => setRevokeConfirmId(null)}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button variant="danger" onClick={handleRevoke} loading={revoking}>
              {t('parent.confirmDisconnect', 'Yes, Disconnect')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
