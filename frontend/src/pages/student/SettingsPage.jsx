/**
 * frontend/src/pages/student/SettingsPage.jsx
 *
 * Student Settings Page: Reading & Accessibility ergonomics, focus tools,
 * and Classroom joining.
 */
import React, { useState } from 'react'
import { PageHeader, Card, Button } from '../../components/ui'
import { AccessibilitySettingsCard } from '../../components/accessibility'
import { classroomAPI } from '../../api/client'
import { useTranslation } from '../../i18n/I18nContext'
import toast from 'react-hot-toast'

export default function SettingsPage() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('accessibility') // 'accessibility' | 'classroom'

  // Classroom state
  const [classCode, setClassCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [classroom, setClassroom] = useState(null)

  const handleJoinClassroom = async () => {
    if (!classCode.trim()) return
    setJoining(true)
    try {
      const res = await classroomAPI.join(classCode.trim())
      setClassroom(res)
      toast.success(`✅ Joined ${res.teacherName}'s classroom!`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid classroom code.')
    } finally {
      setJoining(false)
    }
  }

  const handleLeave = async () => {
    if (!confirm('Leave this classroom?')) return
    await classroomAPI.leave()
    setClassroom(null)
    toast.success('Left classroom.')
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto pb-12">
      <PageHeader
        icon="⚙️"
        title={t('nav.settings', 'Settings')}
        subtitle={t('accessibility.settingsSubtitle', 'Personalize your reading comfort, focus tools, and classroom.')}
      />

      {/* Tab Switcher */}
      <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-2xl border border-slate-200 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab('accessibility')}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'accessibility'
              ? 'bg-white text-indigo-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <span>👓</span>
          <span>{t('accessibility.tabReading', 'Reading & Accessibility')}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('classroom')}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
            activeTab === 'classroom'
              ? 'bg-white text-indigo-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <span>🏫</span>
          <span>{t('accessibility.tabClassroom', 'Classroom')}</span>
        </button>
      </div>

      {activeTab === 'accessibility' ? (
        <AccessibilitySettingsCard />
      ) : (
        /* Classroom Card */
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-2 text-slate-900">🏫 {t('nav.classroom', 'Classroom')}</h2>
          <p className="text-xs text-slate-600 mb-4">
            Connect to your teacher's classroom to receive personalized assignments and reading recommendations.
          </p>

          {classroom ? (
            <div className="flex flex-col gap-3">
              <div className="bg-emerald-50 rounded-2xl p-4 border border-emerald-200">
                <p className="dyslexia-text font-bold text-emerald-800">✅ Connected to Classroom</p>
                <p className="dyslexia-text text-sm text-slate-700 mt-1">Teacher: <span className="font-semibold">{classroom.teacherName}</span></p>
                {classroom.classroomCode && (
                  <p className="dyslexia-text text-sm text-slate-700">Code: <span className="font-mono font-bold bg-white px-2 py-0.5 rounded border border-emerald-300">{classroom.classroomCode}</span></p>
                )}
              </div>
              <Button variant="danger" size="sm" onClick={handleLeave}>Leave Classroom</Button>
            </div>
          ) : (
            <div className="flex gap-3">
              <input
                className="flex-1 px-4 py-3 rounded-2xl border-2 border-slate-200 dyslexia-text focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100"
                placeholder="Enter classroom code (e.g. ABC123)"
                value={classCode}
                onChange={(e) => setClassCode(e.target.value.toUpperCase())}
                aria-label="Enter classroom code"
              />
              <Button onClick={handleJoinClassroom} loading={joining} disabled={!classCode.trim()}>
                Join
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
