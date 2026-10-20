/**
 * frontend/src/pages/student/StudentProfilePage.jsx
 * Dedicated V2 Student Learner Intelligence Profile Page.
 */
import React, { useState } from 'react'
import {
  useLearnerProfile,
  LearnerProfileHeader,
  LearningLevelCard,
  StrengthsCard,
  PracticeAreasCard,
  DomainScoreChart,
  LearningPreferencesCard,
  AccessibilityPreferencesCard,
  LearningGoalsCard,
  ProfileConfidenceCard,
  LearnerDisclaimer,
  LearnerEmptyState,
  LearnerProfileSkeleton,
  LearnerErrorState,
} from '../../features/learner'
import StudentParentConnectionsModal from '../../features/parent/StudentParentConnectionsModal'
import toast from 'react-hot-toast'

export default function StudentProfilePage() {
  const { profile, loading, error, refresh, updateProfile } = useLearnerProfile()
  const [connectionsModalOpen, setConnectionsModalOpen] = useState(false)

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto py-4 px-2 sm:px-4">
        <LearnerProfileSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-2 sm:px-4">
        <LearnerErrorState onRetry={refresh} />
      </div>
    )
  }

  // Empty state if student has not completed screening
  const isScreened = profile?.metadata?.screening_completed ?? true
  const hasDomainScores = profile?.domain_scores && Object.keys(profile.domain_scores).length > 0

  if (!isScreened || !hasDomainScores) {
    return (
      <div className="max-w-5xl mx-auto py-4 px-2 sm:px-4">
        <LearnerEmptyState />
      </div>
    )
  }

  const handleUpdate = async (patch) => {
    try {
      await updateProfile(patch)
      toast.success('✨ Profile updated!')
    } catch {
      toast.error('Could not save changes.')
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 sm:space-y-8 py-4 px-2 sm:px-4">
      {/* 1. Welcoming Header */}
      <LearnerProfileHeader
        name={profile?.learner?.name}
        preferredLanguage={profile?.learner?.preferred_language}
        onRefresh={refresh}
      />

      {/* 2. Educational Learning Level */}
      <section aria-labelledby="learning-level-section">
        <LearningLevelCard learningLevel={profile?.learning_level} />
      </section>

      {/* 3. Strengths & Areas to Practice Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">
        <section aria-labelledby="strengths-section">
          <StrengthsCard strengths={profile?.strengths} />
        </section>

        <section aria-labelledby="practice-areas-section">
          <PracticeAreasCard practiceAreas={profile?.areas_for_practice} />
        </section>
      </div>

      {/* 4. Complete Learning Map (12 Domains) */}
      <section aria-labelledby="learning-map-section">
        <DomainScoreChart
          domainScores={profile?.domain_scores}
          domainInterpretations={profile?.domain_interpretations}
        />
      </section>

      {/* 5. How You Like to Learn */}
      <section aria-labelledby="learning-modes-section">
        <LearningPreferencesCard
          learningModes={profile?.preferences?.learning_modes}
          onUpdatePreferences={handleUpdate}
        />
      </section>

      {/* 6. Personal Reading Goals */}
      <section aria-labelledby="goals-section">
        <LearningGoalsCard
          goals={profile?.goals}
          onUpdateGoals={handleUpdate}
        />
      </section>

      {/* 7. Accessibility & Reading Ergonomics */}
      <section aria-labelledby="accessibility-section">
        <AccessibilityPreferencesCard
          preferences={profile?.preferences}
          onUpdatePreferences={handleUpdate}
        />
      </section>

      {/* 8. Profile Information & Calibration Confidence */}
      <section aria-labelledby="confidence-section">
        <ProfileConfidenceCard
          confidence={profile?.confidence}
          metadata={profile?.metadata}
        />
      </section>

      {/* 9. Family & Guardian Connections */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-card flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center text-2xl">
            👨‍👩‍👧
          </div>
          <div>
            <h3 className="font-bold text-slate-800 dyslexia-text">Family & Guardian Connections</h3>
            <p className="text-xs text-slate-500 dyslexia-text">
              Share an invitation code or approve family access to your reading journey.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setConnectionsModalOpen(true)}
          className="px-4 py-2.5 rounded-xl text-sm font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-600 hover:text-white transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
        >
          👨‍👩‍👧 Manage Family Access
        </button>
      </div>

      {/* 10. Educational Platform Disclaimer */}
      <LearnerDisclaimer />

      <StudentParentConnectionsModal
        open={connectionsModalOpen}
        onClose={() => setConnectionsModalOpen(false)}
      />
    </div>
  )
}
