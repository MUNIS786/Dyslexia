import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { Modal, Button, Badge, Spinner } from '../../components/ui'
import { useTranslation } from '../../i18n/I18nContext'
import { parentV2API } from '../../api/v2/client'

export default function StudentParentConnectionsModal({ open, onClose }) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [codeData, setCodeData] = useState(null)
  const [pendingRequests, setPendingRequests] = useState([])
  const [activeLinks, setActiveLinks] = useState([])
  const [generating, setGenerating] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [reqs, links] = await Promise.all([
        parentV2API.getStudentRequests().catch(() => []),
        parentV2API.getStudentActiveLinks().catch(() => []),
      ])
      setPendingRequests(reqs)
      setActiveLinks(links)
    } catch (err) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      fetchData()
    }
  }, [open])

  const handleGenerateCode = async () => {
    setGenerating(true)
    try {
      const res = await parentV2API.generateInvitationCode()
      setCodeData(res)
      toast.success(t('parent.codeGeneratedSuccess', 'New invitation code created!'))
    } catch (err) {
      toast.error(t('parent.codeGenerateFailed', 'Failed to generate invitation code.'))
    } finally {
      setGenerating(false)
    }
  }

  const handleApprove = async (requestId) => {
    try {
      await parentV2API.approveRequest(requestId)
      toast.success(t('parent.requestApprovedSuccess', 'Parent connection approved!'))
      fetchData()
    } catch (err) {
      toast.error(t('parent.actionFailed', 'Failed to approve request.'))
    }
  }

  const handleReject = async (requestId) => {
    try {
      await parentV2API.rejectRequest(requestId)
      toast.success(t('parent.requestRejectedSuccess', 'Parent request declined.'))
      fetchData()
    } catch (err) {
      toast.error(t('parent.actionFailed', 'Failed to reject request.'))
    }
  }

  const handleRevoke = async (linkId) => {
    try {
      await parentV2API.studentRevokeLink(linkId)
      toast.success(t('parent.linkRevokedSuccess', 'Parent disconnected.'))
      fetchData()
    } catch (err) {
      toast.error(t('parent.actionFailed', 'Failed to disconnect parent.'))
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('parent.manageConnectionsTitle', 'Family & Guardian Connections')}>
      <div className="flex flex-col gap-6">
        {/* 1. Generate Invitation Code Section */}
        <div className="bg-amber-50/70 p-4 rounded-2xl border border-amber-200 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-bold text-slate-900 text-sm dyslexia-text">
                🔑 {t('parent.inviteCodeSectionTitle', 'Parent Invitation Code')}
              </p>
              <p className="text-xs text-slate-600 dyslexia-text">
                {t('parent.inviteCodeHelp', 'Share this code with your parent to let them connect instantly.')}
              </p>
            </div>
            <Button size="sm" onClick={handleGenerateCode} loading={generating} variant="accent">
              {codeData ? t('parent.getNewCode', 'New Code') : t('parent.generateCodeBtn', 'Get Code')}
            </Button>
          </div>

          {codeData && (
            <div className="bg-white p-3.5 rounded-xl border-2 border-dashed border-amber-300 text-center">
              <span className="text-xs text-slate-500 block mb-1 dyslexia-text">
                {t('parent.yourUniqueCode', 'Your One-Time Code (valid 48 hours):')}
              </span>
              <p className="text-2xl font-mono font-bold text-indigo-700 tracking-wider select-all">
                {codeData.invitationCode}
              </p>
            </div>
          )}
        </div>

        {/* 2. Pending Requests Section */}
        <div>
          <h4 className="font-bold text-sm text-slate-800 mb-2 flex items-center gap-2 dyslexia-text">
            <span>✉️</span>
            {t('parent.pendingRequestsSection', 'Pending Parent Requests')}
            {pendingRequests.length > 0 && <Badge color="amber">{pendingRequests.length}</Badge>}
          </h4>

          {loading ? (
            <div className="py-4 text-center"><Spinner size="sm" /></div>
          ) : pendingRequests.length === 0 ? (
            <p className="text-xs text-slate-400 italic dyslexia-text py-2">
              {t('parent.noPendingRequests', 'No pending requests from parents.')}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {pendingRequests.map((req) => (
                <div key={req.id} className="p-3.5 bg-white border border-slate-200 rounded-xl flex items-center justify-between gap-2 shadow-2xs">
                  <div>
                    <p className="text-sm font-bold text-slate-800 dyslexia-text">{req.parentName}</p>
                    <p className="text-xs text-slate-500">{req.parentEmail} • {req.relationship}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => handleReject(req.id)}>
                      {t('parent.decline', 'Decline')}
                    </Button>
                    <Button size="sm" onClick={() => handleApprove(req.id)}>
                      {t('parent.approve', 'Approve')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 3. Active Connections Section */}
        <div>
          <h4 className="font-bold text-sm text-slate-800 mb-2 flex items-center gap-2 dyslexia-text">
            <span>👨‍👩‍👧</span>
            {t('parent.activeConnectionsSection', 'Connected Family Members')}
            {activeLinks.length > 0 && <Badge color="indigo">{activeLinks.length}</Badge>}
          </h4>

          {activeLinks.length === 0 ? (
            <p className="text-xs text-slate-400 italic dyslexia-text py-2">
              {t('parent.noActiveConnections', 'No parents or guardians currently connected.')}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {activeLinks.map((link) => (
                <div key={link.id} className="p-3.5 bg-white border border-slate-200 rounded-xl flex items-center justify-between gap-2 shadow-2xs">
                  <div>
                    <p className="text-sm font-bold text-slate-800 dyslexia-text">{link.parentName}</p>
                    <p className="text-xs text-slate-500">{link.parentEmail} • {link.relationship}</p>
                  </div>
                  <Button size="sm" variant="ghost" className="text-rose-600 hover:bg-rose-50 text-xs font-semibold" onClick={() => handleRevoke(link.id)}>
                    {t('parent.disconnect', 'Disconnect')}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <Button variant="ghost" onClick={onClose}>
            {t('common.close', 'Close')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
