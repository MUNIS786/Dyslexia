import React, { useState, useEffect, useCallback } from 'react'
import { toast } from 'react-hot-toast'
import { useAuth } from '../../context/AuthContext'
import { useTranslation } from '../../i18n/I18nContext'
import { contentAuthoringV2API } from '../../api/v2/client'
import {
  ContentEditor,
  ContentPreview,
  ContentValidationPanel,
  ContentReviewQueue,
  ContentReviewModal,
  ContentVersionHistoryModal,
} from '../../components/authoring'

const STATUS_BADGES = {
  DRAFT: 'bg-gray-100 text-gray-800 border-gray-300',
  IN_REVIEW: 'bg-amber-100 text-amber-800 border-amber-300',
  CHANGES_REQUESTED: 'bg-orange-100 text-orange-800 border-orange-300',
  APPROVED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  PUBLISHED: 'bg-teal-100 text-teal-800 border-teal-300',
  ARCHIVED: 'bg-slate-100 text-slate-800 border-slate-300',
  REJECTED: 'bg-rose-100 text-rose-800 border-rose-300',
}

export default function ContentAuthoringPage() {
  const { user } = useAuth()
  const { t } = useTranslation()

  // Tabs: 'items' | 'editor' | 'queue'
  const [activeTab, setActiveTab] = useState('items')

  // Items list state
  const [items, setItems] = useState([])
  const [loadingItems, setLoadingItems] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [languageFilter, setLanguageFilter] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')

  // Review Queue state
  const [queueItems, setQueueItems] = useState([])
  const [loadingQueue, setLoadingQueue] = useState(false)

  // Editing draft state
  const [editingItem, setEditingItem] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Modals & Panels
  const [previewItem, setPreviewItem] = useState(null)
  const [reviewModalItem, setReviewModalItem] = useState(null)
  const [historyModalData, setHistoryModalData] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [activeValidationResult, setActiveValidationResult] = useState(null)

  // Fetch Items
  const loadItems = useCallback(async () => {
    setLoadingItems(true)
    try {
      const params = {}
      if (statusFilter) params.status = statusFilter
      if (languageFilter) params.language = languageFilter
      if (difficultyFilter) params.difficulty = parseInt(difficultyFilter, 10)
      const res = await contentAuthoringV2API.getItems(params)
      setItems(res.items || [])
    } catch (err) {
      console.error('Failed to load authored items:', err)
      toast.error('Could not load content items.')
    } finally {
      setLoadingItems(false)
    }
  }, [statusFilter, languageFilter, difficultyFilter])

  // Fetch Review Queue
  const loadQueue = useCallback(async () => {
    setLoadingQueue(true)
    try {
      const res = await contentAuthoringV2API.getReviewQueue()
      setQueueItems(res.items || [])
    } catch (err) {
      console.error('Failed to load review queue:', err)
    } finally {
      setLoadingQueue(false)
    }
  }, [])

  useEffect(() => {
    loadItems()
    loadQueue()
  }, [loadItems, loadQueue])

  // Save Draft (New or Update)
  const handleSaveDraft = async (payload) => {
    setIsSaving(true)
    try {
      if (editingItem?.contentId) {
        const res = await contentAuthoringV2API.updateDraft(editingItem.contentId, payload)
        toast.success('Draft updated successfully!')
        setActiveValidationResult(res.validationResult)
        setEditingItem(res)
      } else {
        const res = await contentAuthoringV2API.createDraft(payload)
        toast.success('New draft created!')
        setActiveValidationResult(res.validationResult)
        setEditingItem(res)
      }
      loadItems()
    } catch (err) {
      console.error('Failed to save draft:', err)
      toast.error(err.response?.data?.detail || 'Failed to save draft.')
    } finally {
      setIsSaving(false)
    }
  }

  // Submit Draft for Review
  const handleSubmitReview = async (payload) => {
    setIsSubmitting(true)
    try {
      let contentId = editingItem?.contentId
      if (!contentId) {
        const created = await contentAuthoringV2API.createDraft(payload)
        contentId = created.contentId
      } else {
        await contentAuthoringV2API.updateDraft(contentId, payload)
      }

      await contentAuthoringV2API.submitForReview(contentId)
      toast.success('Passage submitted for peer review!')
      setEditingItem(null)
      setActiveTab('items')
      loadItems()
      loadQueue()
    } catch (err) {
      console.error('Failed to submit for review:', err)
      toast.error(err.response?.data?.detail || 'Submission failed. Please check validation.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Run Quality Check on Editor
  const handleValidateContent = async (payload) => {
    try {
      const res = await contentAuthoringV2API.validateContent(payload)
      setActiveValidationResult(res)
      if (res.isValid) {
        toast.success(`Quality checks passed! Score: ${res.completenessScore}/100`)
      } else {
        toast.error(`Found ${res.errors.length} blocking issues. Review panel below.`)
      }
    } catch (err) {
      console.error('Validation error:', err)
      toast.error('Quality check failed to run.')
    }
  }

  // Publish Approved Content
  const handlePublish = async (contentId) => {
    try {
      await contentAuthoringV2API.publishItem(contentId)
      toast.success('Passage published to catalog! Students can now discover it.')
      loadItems()
    } catch (err) {
      console.error('Publish error:', err)
      toast.error(err.response?.data?.detail || 'Failed to publish.')
    }
  }

  // Archive Published Content
  const handleArchive = async (contentId) => {
    if (!window.confirm('Archive this passage? It will be removed from new student discovery.')) return
    try {
      await contentAuthoringV2API.archiveItem(contentId)
      toast.success('Passage archived successfully.')
      loadItems()
    } catch (err) {
      console.error('Archive error:', err)
      toast.error(err.response?.data?.detail || 'Failed to archive.')
    }
  }

  // Revise Published/Archived Content
  const handleRevise = async (contentId) => {
    try {
      const res = await contentAuthoringV2API.reviseItem(contentId)
      toast.success(`Created revision v${res.version}!`)
      setEditingItem(res)
      setActiveTab('editor')
      loadItems()
    } catch (err) {
      console.error('Revise error:', err)
      toast.error(err.response?.data?.detail || 'Failed to create revision.')
    }
  }

  // View History
  const handleViewHistory = async (contentId) => {
    setLoadingHistory(true)
    setHistoryModalData({ contentId, history: [] })
    try {
      const res = await contentAuthoringV2API.getHistory(contentId)
      setHistoryModalData(res)
    } catch (err) {
      console.error('History error:', err)
      toast.error('Could not load audit history.')
    } finally {
      setLoadingHistory(false)
    }
  }

  // Submit Review Decision
  const handleReviewDecision = async (payload) => {
    if (!reviewModalItem) return
    try {
      await contentAuthoringV2API.submitReviewDecision(reviewModalItem.contentId, payload)
      toast.success(`Review decision submitted: ${payload.decision}!`)
      setReviewModalItem(null)
      loadQueue()
      loadItems()
    } catch (err) {
      console.error('Review decision error:', err)
      toast.error(err.response?.data?.detail || 'Failed to submit review decision.')
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">✍️</span>
            <span className="text-xs font-bold uppercase tracking-widest text-[#1A6B6B]">
              Phase 16 Authoring & Quality Management
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
            {t('contentAuthoring.pageTitle', 'Learning Content Authoring')}
          </h1>
          <p className="text-sm text-gray-600 mt-1 max-w-2xl">
            {t(
              'contentAuthoring.pageSubtitle',
              'Create, validate, review, and publish dyslexia-friendly reading passages and educational activities.'
            )}
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            setEditingItem(null)
            setActiveValidationResult(null)
            setActiveTab('editor')
          }}
          className="px-5 py-2.5 rounded-xl bg-[#E8A020] text-white hover:bg-[#d49018] font-bold text-sm shadow-md transition-all self-start md:self-auto flex items-center gap-2"
        >
          <span>+</span>
          <span>{t('contentAuthoring.createDraftBtn', 'Create New Passage')}</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 gap-2 sm:gap-6 text-sm font-bold text-gray-500 overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab('items')}
          className={`py-3 px-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'items'
              ? 'border-[#1A6B6B] text-[#1A6B6B]'
              : 'border-transparent hover:text-gray-700'
          }`}
        >
          📚 {t('contentAuthoring.tabMyDrafts', 'My Drafts & Content')} ({items.length})
        </button>

        <button
          type="button"
          onClick={() => {
            if (!editingItem) setEditingItem(null)
            setActiveTab('editor')
          }}
          className={`py-3 px-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'editor'
              ? 'border-[#1A6B6B] text-[#1A6B6B]'
              : 'border-transparent hover:text-gray-700'
          }`}
        >
          ✏️ {editingItem ? `Editing: ${editingItem.title || 'Draft'}` : t('contentAuthoring.tabCreateNew', 'Create New Passage')}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('queue')}
          className={`py-3 px-2 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'queue'
              ? 'border-[#1A6B6B] text-[#1A6B6B]'
              : 'border-transparent hover:text-gray-700'
          }`}
        >
          <span>⚖️ {t('contentAuthoring.tabReviewQueue', 'Peer Review Queue')}</span>
          {queueItems.length > 0 && (
            <span className="text-xs bg-amber-500 text-white font-extrabold px-1.5 py-0.2 rounded-full">
              {queueItems.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab: Items & Catalog */}
      {activeTab === 'items' && (
        <div className="space-y-6">
          {/* Filters Bar */}
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-gray-300 font-medium text-gray-700 bg-white"
              >
                <option value="">{t('contentAuthoring.allStatuses', 'All Statuses')}</option>
                <option value="DRAFT">{t('contentAuthoring.statusDraft', 'Draft')}</option>
                <option value="IN_REVIEW">{t('contentAuthoring.statusInReview', 'In Review')}</option>
                <option value="CHANGES_REQUESTED">{t('contentAuthoring.statusChangesRequested', 'Changes Requested')}</option>
                <option value="APPROVED">{t('contentAuthoring.statusApproved', 'Approved')}</option>
                <option value="PUBLISHED">{t('contentAuthoring.statusPublished', 'Published')}</option>
                <option value="ARCHIVED">{t('contentAuthoring.statusArchived', 'Archived')}</option>
              </select>

              <select
                value={languageFilter}
                onChange={(e) => setLanguageFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-gray-300 font-medium text-gray-700 bg-white"
              >
                <option value="">{t('contentAuthoring.allLanguages', 'All Languages')}</option>
                <option value="en">English (en)</option>
                <option value="hi">Hindi (hi)</option>
                <option value="mr">Marathi (mr)</option>
              </select>

              <select
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-gray-300 font-medium text-gray-700 bg-white"
              >
                <option value="">{t('contentAuthoring.allTiers', 'All Tiers')}</option>
                <option value="1">Tier 1 - Foundation</option>
                <option value="2">Tier 2 - Early Phonics</option>
                <option value="3">Tier 3 - Guided Fluency</option>
                <option value="4">Tier 4 - Confident Reader</option>
                <option value="5">Tier 5 - Advanced</option>
              </select>
            </div>

            <button
              type="button"
              onClick={loadItems}
              className="text-xs font-bold text-gray-600 hover:text-gray-900"
            >
              ↻ Refresh List
            </button>
          </div>

          {/* Items Grid */}
          {loadingItems ? (
            <div className="py-16 text-center text-gray-400">Loading catalog items...</div>
          ) : items.length === 0 ? (
            <div className="bg-white rounded-2xl p-12 text-center border border-gray-200 space-y-3">
              <span className="text-3xl">📝</span>
              <h4 className="text-base font-bold text-gray-900">
                {t('contentAuthoring.emptyDrafts', 'No content items found. Create your first draft to get started!')}
              </h4>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {items.map((item) => {
                const badge = STATUS_BADGES[item.status] || STATUS_BADGES.DRAFT
                const isAuthor = item.authorId === user?.id
                return (
                  <div
                    key={item.contentId}
                    className="bg-white rounded-2xl border border-gray-200 hover:border-teal-300 p-5 shadow-sm space-y-4 flex flex-col justify-between transition-all"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${badge}`}>
                          {item.status}
                        </span>
                        <div className="flex items-center gap-1.5 text-xs text-gray-400">
                          <span className="uppercase font-bold">{item.language}</span>
                          <span>•</span>
                          <span>Tier {item.difficulty}</span>
                        </div>
                      </div>

                      <h4 className="font-bold text-gray-900 text-base leading-snug">{item.title}</h4>
                      <p className="text-xs text-gray-500 line-clamp-3 mt-1.5 leading-relaxed">
                        {item.text}
                      </p>

                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-500 mt-3 pt-3 border-t border-gray-100">
                        <span>Words: <strong>{item.wordCount}</strong></span>
                        <span>Questions: <strong>{item.questions?.length || 0}</strong></span>
                        <span>v{item.version}</span>
                      </div>

                      {item.reviewerFeedback && (
                        <div className="mt-2.5 p-2 rounded-lg bg-orange-50 border border-orange-200 text-xs text-orange-800">
                          <strong>Reviewer Feedback:</strong> "{item.reviewerFeedback}"
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="pt-2 border-t border-gray-100 flex flex-wrap items-center gap-2 justify-between">
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => setPreviewItem(item)}
                          className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700"
                        >
                          👁 Preview
                        </button>
                        <button
                          type="button"
                          onClick={() => handleViewHistory(item.contentId)}
                          className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700"
                        >
                          📜 History
                        </button>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {/* Status-dependent actions */}
                        {(item.status === 'DRAFT' || item.status === 'CHANGES_REQUESTED') && isAuthor && (
                          <button
                            type="button"
                            onClick={() => {
                              setEditingItem(item)
                              setActiveValidationResult(item.validationResult)
                              setActiveTab('editor')
                            }}
                            className="px-3 py-1 text-xs font-bold rounded-lg bg-[#1A6B6B] text-white hover:bg-[#145252]"
                          >
                            Edit Draft
                          </button>
                        )}

                        {item.status === 'APPROVED' && (
                          <button
                            type="button"
                            onClick={() => handlePublish(item.contentId)}
                            className="px-3 py-1 text-xs font-bold rounded-lg bg-teal-600 text-white hover:bg-teal-700"
                          >
                            🚀 Publish
                          </button>
                        )}

                        {item.status === 'PUBLISHED' && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleArchive(item.contentId)}
                              className="px-2 py-1 text-xs font-semibold rounded-lg text-slate-600 hover:bg-slate-100"
                            >
                              Archive
                            </button>
                            <button
                              type="button"
                              onClick={() => handleRevise(item.contentId)}
                              className="px-2.5 py-1 text-xs font-bold rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200"
                            >
                              Revise
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Editor */}
      {activeTab === 'editor' && (
        <div className="space-y-6">
          <ContentEditor
            initialContent={editingItem || {}}
            onSaveDraft={handleSaveDraft}
            onSubmitReview={handleSubmitReview}
            onValidate={handleValidateContent}
            isSaving={isSaving}
            isSubmitting={isSubmitting}
          />

          {/* Validation Result Panel */}
          {activeValidationResult && (
            <ContentValidationPanel
              validationResult={activeValidationResult}
              onClose={() => setActiveValidationResult(null)}
            />
          )}
        </div>
      )}

      {/* Tab: Review Queue */}
      {activeTab === 'queue' && (
        <ContentReviewQueue
          items={queueItems}
          loading={loadingQueue}
          onReviewItem={(item) => setReviewModalItem(item)}
          onRefresh={loadQueue}
        />
      )}

      {/* Preview Modal */}
      {previewItem && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-gray-100">
              <h3 className="font-bold text-gray-900 text-base">Passage Preview</h3>
              <button
                type="button"
                onClick={() => setPreviewItem(null)}
                className="text-gray-400 hover:text-gray-600 font-bold"
              >
                ✕
              </button>
            </div>
            <ContentPreview content={previewItem} />
          </div>
        </div>
      )}

      {/* Review Modal */}
      {reviewModalItem && (
        <ContentReviewModal
          item={reviewModalItem}
          currentUserId={user?.id}
          onClose={() => setReviewModalItem(null)}
          onSubmitDecision={handleReviewDecision}
        />
      )}

      {/* Version & Audit History Modal */}
      {historyModalData && (
        <ContentVersionHistoryModal
          historyData={historyModalData}
          loading={loadingHistory}
          onClose={() => setHistoryModalData(null)}
        />
      )}
    </div>
  )
}
