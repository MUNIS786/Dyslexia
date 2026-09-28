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

export default {
  version: versionAPI,
  learner: learnerV2API,
}
