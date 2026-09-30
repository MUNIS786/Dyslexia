/**
 * frontend/src/pages/student/TutorPage.jsx — DyslexAid V2 Personal AI Tutor Page.
 *
 * Dedicated educational tutor workspace for students:
 * - Socratic, level-adapted assistance
 * - Deep reading context awareness
 * - Safe fallback support when offline
 * - Preserves existing V1 Chat while offering modern V2 tutoring
 */
import React from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { TutorChat } from '../../features/tutor'

export default function TutorPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()

  const initialWord = searchParams.get('word') || null
  const initialPassageId = searchParams.get('passageId') || null
  const studentName = user?.name ? user.name.split(' ')[0] : 'Learner'

  return (
    <div className="space-y-4 max-w-4xl mx-auto pb-8">
      {/* Interactive Tutor Chat */}
      <TutorChat
        initialPassageId={initialPassageId}
        initialWord={initialWord}
        studentName={studentName}
      />
    </div>
  )
}
