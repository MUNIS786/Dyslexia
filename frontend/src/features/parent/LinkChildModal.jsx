import { useState } from 'react'
import toast from 'react-hot-toast'
import { Modal, Button, Input, Select, Alert } from '../../components/ui'
import { useTranslation } from '../../i18n/I18nContext'
import { parentV2API } from '../../api/v2/client'

export default function LinkChildModal({ open, onClose, onLinked }) {
  const { t } = useTranslation()
  const [tab, setTab] = useState('code') // 'code' | 'request'
  const [code, setCode] = useState('')
  const [studentId, setStudentId] = useState('')
  const [relationship, setRelationship] = useState('parent')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const relationOptions = [
    { value: 'parent', label: t('parent.relationParent', 'Parent') },
    { value: 'mother', label: t('parent.relationMother', 'Mother') },
    { value: 'father', label: t('parent.relationFather', 'Father') },
    { value: 'guardian', label: t('parent.relationGuardian', 'Guardian') },
    { value: 'caregiver', label: t('parent.relationCaregiver', 'Caregiver') },
  ]

  const handleClaimCode = async (e) => {
    if (e) e.preventDefault()
    if (!code.trim()) {
      setError(t('parent.enterCodePrompt', 'Please enter your invitation code.'))
      return
    }
    setError('')
    setLoading(true)
    try {
      const link = await parentV2API.claimCode(code.trim(), relationship)
      toast.success(t('parent.connectedSuccess', `Successfully connected to ${link.studentName}! 🎉`))
      setCode('')
      if (onLinked) onLinked(link)
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || t('parent.claimFailed', 'Failed to connect. Please check the code.'))
    } finally {
      setLoading(false)
    }
  }

  const handleRequestLink = async (e) => {
    if (e) e.preventDefault()
    if (!studentId.trim()) {
      setError(t('parent.enterEmailPrompt', "Please enter the student's email or student ID."))
      return
    }
    setError('')
    setLoading(true)
    try {
      const link = await parentV2API.requestLink(studentId.trim(), relationship)
      toast.success(t('parent.requestSentSuccess', 'Connection request sent! Waiting for learner or teacher approval.'))
      setStudentId('')
      if (onLinked) onLinked(link)
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || t('parent.requestFailed', 'Failed to send request. Learner not found.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('parent.linkChildTitle', 'Connect with Your Child')}>
      <div className="flex flex-col gap-4">
        {/* Tab switch */}
        <div className="flex border-b border-[#E5E0D8]">
          <button
            type="button"
            onClick={() => { setTab('code'); setError('') }}
            className={`flex-1 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              tab === 'code'
                ? 'border-[#1A6B6B] text-[#1A6B6B]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            🔑 {t('parent.tabCode', 'Use Invitation Code')}
          </button>
          <button
            type="button"
            onClick={() => { setTab('request'); setError('') }}
            className={`flex-1 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              tab === 'request'
                ? 'border-[#1A6B6B] text-[#1A6B6B]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            ✉️ {t('parent.tabRequest', 'Request Connection')}
          </button>
        </div>

        {error && <Alert type="error">{error}</Alert>}

        {tab === 'code' ? (
          <form onSubmit={handleClaimCode} className="flex flex-col gap-3">
            <p className="text-sm text-gray-600 dyslexia-text">
              {t('parent.codeHelpText', "Enter the 8-character invitation code generated from your child's student profile or provided by their teacher.")}
            </p>
            <Input
              label={t('parent.invitationCodeLabel', 'Invitation Code')}
              placeholder="e.g. PLC-A1B2-C3D4"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              autoFocus
            />
            <Select
              label={t('parent.relationshipLabel', 'Your Relationship')}
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              options={relationOptions}
            />
            <div className="bg-[#FFF8F0] p-3 rounded-xl border border-[#E8A020]/30 text-xs text-gray-600 dyslexia-text">
              💡 {t('parent.codeTip', 'Invitation codes are secure, valid for 48 hours, and can only be used once.')}
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <Button variant="ghost" onClick={onClose}>
                {t('common.cancel', 'Cancel')}
              </Button>
              <Button onClick={handleClaimCode} loading={loading}>
                {t('parent.connectNow', 'Connect Now')}
              </Button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleRequestLink} className="flex flex-col gap-3">
            <p className="text-sm text-gray-600 dyslexia-text">
              {t('parent.requestHelpText', "Enter your child's registered student email address or ID. An approval notification will be sent to their account.")}
            </p>
            <Input
              label={t('parent.studentEmailLabel', "Student's Email or ID")}
              placeholder="student@school.edu or student ID"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              autoFocus
            />
            <Select
              label={t('parent.relationshipLabel', 'Your Relationship')}
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              options={relationOptions}
            />
            <div className="bg-[#E0F2F2] p-3 rounded-xl border border-[#1A6B6B]/20 text-xs text-[#1A6B6B] dyslexia-text">
              🔒 {t('parent.requestPrivacyTip', 'For learner privacy, progress records are strictly shielded until the connection is approved.')}
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <Button variant="ghost" onClick={onClose}>
                {t('common.cancel', 'Cancel')}
              </Button>
              <Button onClick={handleRequestLink} loading={loading}>
                {t('parent.sendRequest', 'Send Request')}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  )
}
