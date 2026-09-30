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
  getRecommendation: () => api.get('/v2/reading/recommendation').then((r) => r.data),
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

export default {
  version: versionAPI,
  learner: learnerV2API,
  learning: learningV2API,
  reading: readingV2API,
}
