/**
 * frontend/src/api/v2/client.js — DyslexAid V2 API Client.
 * Builds upon the centralized Axios client with typed V2 methods.
 */
import api from '../client'

export const versionAPI = {
  get: () => api.get('/version').then((r) => r.data),
}

export const learnerV2API = {
  getProfile: () => api.get('/v2/learner/profile').then((r) => r.data),
  updateProfile: (patchData) => api.patch('/v2/learner/profile', patchData).then((r) => r.data),
  getState: () => api.get('/v2/learner/state').then((r) => r.data),
  getStudentProfile: (studentId) =>
    api.get(`/v2/learner/student/${studentId}/profile`).then((r) => r.data),
}

export const learningV2API = {
  getActivities: (params) => api.get('/v2/learning/activities', { params }).then((r) => r.data),
  getRecommendations: (count = 4) =>
    api.get('/v2/learning/recommendations', { params: { count } }).then((r) => r.data),
  submitAttempt: (attemptData) =>
    api.post('/v2/learning/attempt', attemptData).then((r) => r.data),
  getState: () => api.get('/v2/learning/state').then((r) => r.data),
  getTierInfo: () => api.get('/v2/learning/tier-info').then((r) => r.data),
}

export const readingV2API = {
  getRecommendation: (params) => api.get('/v2/reading/recommendation', { params }).then((r) => r.data),
  getPassages: (params) => api.get('/v2/reading/passages', { params }).then((r) => r.data),
  getPassage: (passageId) => api.get(`/v2/reading/passages/${passageId}`).then((r) => r.data),
  startSession: (data) => api.post('/v2/reading/session/start', data).then((r) => r.data),
  completeSession: (data) => api.post('/v2/reading/session/complete', data).then((r) => r.data),
  getSessions: (params) => api.get('/v2/reading/sessions', { params }).then((r) => r.data),
  getStats: (params) => api.get('/v2/reading/stats', { params }).then((r) => r.data),
  analyzeSpeech: (data) => api.post('/v2/reading/speech/analyze', data).then((r) => r.data),
  getSpeechSession: (sessionId, studentId = null) =>
    api.get(`/v2/reading/speech/sessions/${sessionId}${studentId ? `?student_id=${studentId}` : ''}`).then((r) => r.data),
}

export const tutorV2API = {
  sendMessage: (data) => api.post('/v2/tutor/chat', data).then((r) => r.data),
  getContext: (params) => api.get('/v2/tutor/context', { params }).then((r) => r.data),
  getHistory: (params) => api.get('/v2/tutor/history', { params }).then((r) => r.data),
  clearHistory: () => api.delete('/v2/tutor/history').then((r) => r.data),
}

export const teacherV2API = {
  getOverview: (timeRange = 'all') =>
    api.get('/v2/teacher/analytics/overview', { params: { time_range: timeRange } }).then((r) => r.data),
  getLearners: (timeRange = 'all') =>
    api.get('/v2/teacher/analytics/learners', { params: { time_range: timeRange } }).then((r) => r.data),
  getLearnerDetail: (studentId, timeRange = 'all') =>
    api.get(`/v2/teacher/analytics/learners/${studentId}`, { params: { time_range: timeRange } }).then((r) => r.data),
  getLearnerTrend: (studentId, timeRange = 'all') =>
    api.get(`/v2/teacher/analytics/learners/${studentId}/trend`, { params: { time_range: timeRange } }).then((r) => r.data),
}

export const interventionV2API = {
  getInterventions: (params) =>
    api.get('/v2/teacher/interventions', { params }).then((r) => r.data),
  getIntervention: (id) =>
    api.get(`/v2/teacher/interventions/${id}`).then((r) => r.data),
  createIntervention: (data) =>
    api.post('/v2/teacher/interventions', data).then((r) => r.data),
  updateIntervention: (id, data) =>
    api.patch(`/v2/teacher/interventions/${id}`, data).then((r) => r.data),
  startIntervention: (id, data = {}) =>
    api.post(`/v2/teacher/interventions/${id}/start`, data).then((r) => r.data),
  reviewIntervention: (id, data = {}) =>
    api.post(`/v2/teacher/interventions/${id}/review`, data).then((r) => r.data),
  completeIntervention: (id, data = {}) =>
    api.post(`/v2/teacher/interventions/${id}/complete`, data).then((r) => r.data),
  cancelIntervention: (id, data = {}) =>
    api.post(`/v2/teacher/interventions/${id}/cancel`, data).then((r) => r.data),
  getEffectiveness: (id) =>
    api.get(`/v2/teacher/interventions/${id}/effectiveness`).then((r) => r.data),
  addMeasurement: (id, data) =>
    api.post(`/v2/teacher/interventions/${id}/measurements`, data).then((r) => r.data),
}

export const gamificationV2API = {
  getSummary: () =>
    api.get('/v2/gamification/summary').then((r) => r.data),
  getAchievements: () =>
    api.get('/v2/gamification/achievements').then((r) => r.data),
  getMilestones: () =>
    api.get('/v2/gamification/milestones').then((r) => r.data),
  getHistory: (params) =>
    api.get('/v2/gamification/history', { params }).then((r) => r.data),
  claimEvent: (data) =>
    api.post('/v2/gamification/claim-event', data).then((r) => r.data),
  getTeacherLearnerSummary: (studentId) =>
    api.get(`/v2/gamification/teacher/learner/${studentId}`).then((r) => r.data),
}

export const multilingualV2API = {
  getLanguages: () =>
    api.get('/v2/multilingual/languages').then((r) => r.data),
  getPreference: () =>
    api.get('/v2/multilingual/preference').then((r) => r.data),
  updatePreference: (language) =>
    api.put('/v2/multilingual/preference', { language }).then((r) => r.data),
}

export const parentV2API = {
  getProfile: () => api.get('/v2/parent/profile').then((r) => r.data),
  getLearners: () => api.get('/v2/parent/learners').then((r) => r.data),
  claimCode: (code, relationship = 'parent') =>
    api.post('/v2/parent/link/claim-code', { code, relationship }).then((r) => r.data),
  requestLink: (studentIdentifier, relationship = 'parent') =>
    api.post('/v2/parent/link/request', { studentIdentifier, relationship }).then((r) => r.data),
  revokeLink: (linkId) => api.post(`/v2/parent/links/${linkId}/revoke`).then((r) => r.data),
  getDashboard: (studentId = null) =>
    api.get('/v2/parent/dashboard', { params: studentId ? { student_id: studentId } : {} }).then((r) => r.data),
  getLearnerActivity: (studentId, limit = 15) =>
    api.get(`/v2/parent/learners/${studentId}/activity`, { params: { limit } }).then((r) => r.data),
  generateInvitationCode: (studentId = null) =>
    api.post('/v2/parent/invitations/generate', { studentId }).then((r) => r.data),
  getStudentRequests: () => api.get('/v2/parent/student/requests').then((r) => r.data),
  approveRequest: (requestId) =>
    api.post(`/v2/parent/student/requests/${requestId}/approve`).then((r) => r.data),
  rejectRequest: (requestId) =>
    api.post(`/v2/parent/student/requests/${requestId}/reject`).then((r) => r.data),
  getStudentActiveLinks: () => api.get('/v2/parent/student/links').then((r) => r.data),
  studentRevokeLink: (linkId) =>
    api.post(`/v2/parent/student/links/${linkId}/revoke`).then((r) => r.data),
}

export const accessibilityV2API = {
  getPreferences: () => api.get('/v2/accessibility/preferences').then((r) => r.data),
  updatePreferences: (data) => api.put('/v2/accessibility/preferences', data).then((r) => r.data),
  patchPreferences: (data) => api.patch('/v2/accessibility/preferences', data).then((r) => r.data),
  resetPreferences: () => api.post('/v2/accessibility/preferences/reset').then((r) => r.data),
}

export const insightsV2API = {
  getStudentInsights: (period = '30d') =>
    api.get('/v2/learning-insights/student', { params: { period } }).then((r) => r.data),
  getTeacherClassOverview: (period = '30d') =>
    api.get('/v2/learning-insights/teacher/overview', { params: { period } }).then((r) => r.data),
  getTeacherLearnerInsights: (learnerId, period = '30d') =>
    api.get(`/v2/learning-insights/teacher/${learnerId}`, { params: { period } }).then((r) => r.data),
  getParentLearnerInsights: (learnerId, period = '30d') =>
    api.get(`/v2/learning-insights/parent/${learnerId}`, { params: { period } }).then((r) => r.data),
}

export const recommendationsV2API = {
  getStudentRecommendations: (period = 'today') =>
    api.get('/v2/learning-recommendations/student', { params: { period } }).then((r) => r.data),
  refreshStudentRecommendations: (period = 'today') =>
    api.post('/v2/learning-recommendations/student/refresh', null, { params: { period } }).then((r) => r.data),
  getTeacherLearnerRecommendations: (learnerId, period = 'today') =>
    api.get(`/v2/learning-recommendations/teacher/${learnerId}`, { params: { period } }).then((r) => r.data),
  getParentLearnerRecommendations: (learnerId, period = 'today') =>
    api.get(`/v2/learning-recommendations/parent/${learnerId}`, { params: { period } }).then((r) => r.data),
}

export const personalizedContentV2API = {
  getNextActivity: (language = null, activityType = null) =>
    api
      .get('/v2/personalized-content/next', {
        params: {
          ...(language ? { language } : {}),
          ...(activityType ? { activity_type: activityType } : {}),
        },
      })
      .then((r) => r.data),
  getPersonalizedActivities: (params = {}) =>
    api.get('/v2/personalized-content/activities', { params }).then((r) => r.data),
  getContentForRecommendation: (recommendationId, language = null) =>
    api
      .get(`/v2/personalized-content/recommendation/${recommendationId}`, {
        params: language ? { language } : {},
      })
      .then((r) => r.data),
  launchActivity: (payload) =>
    api.post('/v2/personalized-content/launch', payload).then((r) => r.data),
  getTeacherPersonalizedContent: (learnerId) =>
    api.get(`/v2/personalized-content/teacher/${learnerId}`).then((r) => r.data),
  getParentPersonalizedContent: (learnerId) =>
    api.get(`/v2/personalized-content/parent/${learnerId}`).then((r) => r.data),
}

export const contentAuthoringV2API = {
  getItems: (params) =>
    api.get('/v2/content-authoring/items', { params }).then((r) => r.data),
  createDraft: (payload) =>
    api.post('/v2/content-authoring/drafts', payload).then((r) => r.data),
  getDraft: (contentId) =>
    api.get(`/v2/content-authoring/drafts/${contentId}`).then((r) => r.data),
  updateDraft: (contentId, payload) =>
    api.put(`/v2/content-authoring/drafts/${contentId}`, payload).then((r) => r.data),
  validateContent: (payload) =>
    api.post('/v2/content-authoring/validate', payload).then((r) => r.data),
  submitForReview: (contentId) =>
    api.post(`/v2/content-authoring/drafts/${contentId}/submit`).then((r) => r.data),
  getReviewQueue: (params) =>
    api.get('/v2/content-authoring/review-queue', { params }).then((r) => r.data),
  submitReviewDecision: (contentId, payload) =>
    api.post(`/v2/content-authoring/review/${contentId}/decision`, payload).then((r) => r.data),
  publishItem: (contentId) =>
    api.post(`/v2/content-authoring/items/${contentId}/publish`).then((r) => r.data),
  archiveItem: (contentId) =>
    api.post(`/v2/content-authoring/items/${contentId}/archive`).then((r) => r.data),
  reviseItem: (contentId) =>
    api.post(`/v2/content-authoring/items/${contentId}/revise`).then((r) => r.data),
  getHistory: (contentId) =>
    api.get(`/v2/content-authoring/items/${contentId}/history`).then((r) => r.data),
  getTranslations: (translationGroupId) =>
    api.get(`/v2/content-authoring/translations/${translationGroupId}`).then((r) => r.data),
}

export default {
  version: versionAPI,
  learner: learnerV2API,
  learning: learningV2API,
  reading: readingV2API,
  tutor: tutorV2API,
  teacher: teacherV2API,
  intervention: interventionV2API,
  gamification: gamificationV2API,
  multilingual: multilingualV2API,
  parent: parentV2API,
  accessibility: accessibilityV2API,
  insights: insightsV2API,
  recommendations: recommendationsV2API,
  personalizedContent: personalizedContentV2API,
  authoring: contentAuthoringV2API,
}


