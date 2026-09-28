import axios from 'axios'

// Centralized base (uses Vite proxy → /api → backend)
const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('dyslexaid_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle auth errors globally
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('dyslexaid_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ================= AUTH =================
export const authAPI = {
  signup: (data) => api.post('/auth/signup', data).then((r) => r.data),
  signin: (data) => api.post('/auth/signin', data).then((r) => r.data),
  me: () => api.get('/auth/me').then((r) => r.data),
  updateProfile: (data) => api.patch('/auth/profile', data).then((r) => r.data),
  updateSettings: (data) => api.patch('/auth/settings', data).then((r) => r.data),
}

// ================= CLASSROOM =================
export const classroomAPI = {
  join: (code) => api.post('/classroom/join', { code }).then((r) => r.data),
  info: () => api.get('/classroom/info').then((r) => r.data),
  students: () => api.get('/classroom/students').then((r) => r.data),
  announce: (message) => api.post('/classroom/announce', { message }).then((r) => r.data),
  leave: () => api.post('/classroom/leave').then((r) => r.data),
}

// ================= ASSIGNMENTS =================
export const assignmentsAPI = {
  list: () => api.get('/assignments').then((r) => r.data),
  get: (id) => api.get(`/assignments/${id}`).then((r) => r.data),
  create: (data) => api.post('/assignments', data).then((r) => r.data),
  uploadAndCreate: (formData) =>
    api.post('/assignments/upload-and-create', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
  submit: (data) => api.post('/assignments/submit', data).then((r) => r.data),
  grade: (data) => api.post('/assignments/grade', data).then((r) => r.data),
  delete: (id) => api.delete(`/assignments/${id}`).then((r) => r.data),
}

// ================= TEST =================
export const testAPI = {
  questions: () => api.get('/dyslexia-test/questions').then((r) => r.data),
  submit: (data) => api.post('/dyslexia-test/submit', data).then((r) => r.data),
}

// ================= AI PLAN =================
export const planAPI = {
  generate: () => api.post('/ai-plan/generate').then((r) => r.data),
  get: () => api.get('/ai-plan').then((r) => r.data),
  checkAdapt: () => api.post('/ai-plan/check-adapt').then((r) => r.data),
  suggestions: () => api.get('/ai-plan/suggestions').then((r) => r.data),
}

// ================= TASKS =================
export const tasksAPI = {
  today: () => api.get('/tasks').then((r) => r.data),
  complete: (id) => api.post(`/tasks/${id}/complete`).then((r) => r.data),
}

// ================= PROGRESS =================
export const progressAPI = {
  summary: () => api.get('/progress/summary').then((r) => r.data),
  sessionStart: () => api.post('/progress/session-start').then((r) => r.data),
  sessionEnd: (durationMinutes) =>
    api.post('/progress/session-end', { durationMinutes }).then((r) => r.data),
  comprehension: (score) =>
    api.post('/progress/comprehension', { score }).then((r) => r.data),
  scan: (data) => api.post('/progress/scan', data).then((r) => r.data),
  word: (word) => api.post('/progress/word', { word }).then((r) => r.data),
}

// ================= SCAN =================
export const scanAPI = {
  scan: (formData) =>
    api.post('/scan', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
  simplify: (data) => api.post('/simplify', data).then((r) => r.data),
  convertNotes: (data) => api.post('/convert-notes', data).then((r) => r.data),
}

// ================= LIBRARY =================
export const libraryAPI = {
  list: () => api.get('/library').then((r) => r.data),
  get: (id) => api.get(`/library/${id}`).then((r) => r.data),
  save: (data) => api.post('/library', data).then((r) => r.data),
  delete: (id) => api.delete(`/library/${id}`).then((r) => r.data),
}

// ================= CHAT =================
export const chatAPI = {
  send: (message, history) =>
    api.post('/chat', { message, history }).then((r) => r.data),
}

// ================= TEACHER =================
export const teacherAPI = {
  students: () => api.get('/teacher/students').then((r) => r.data),
  studentDetail: (id) => api.get(`/teacher/student/${id}`).then((r) => r.data),
  analytics: () => api.get('/teacher/analytics').then((r) => r.data),
  lessonPlan: (data) => api.post('/teacher/lesson-plan', data).then((r) => r.data),
}

// ================= NOTIFICATIONS =================
export const notifAPI = {
  list: () => api.get('/notifications').then((r) => r.data),
  read: (id) => api.post(`/notifications/read/${id}`).then((r) => r.data),
  readAll: () => api.post('/notifications/read-all').then((r) => r.data),

  // ✅ FIXED (no BASE error)
  streamUrl: () => {
    const token = localStorage.getItem('dyslexaid_token')
    return `/api/notifications/stream?token=${token}`
  },
}

export default api