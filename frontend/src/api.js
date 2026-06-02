import axios from 'axios'
import { getToken, clearToken } from './auth.js'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use((cfg) => {
  const t = getToken()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) clearToken()
    return Promise.reject(err)
  }
)

export const childApi = {
  enter: (name) => api.post('/api/auth/enter', { name }).then(r => r.data),
  home: () => api.get('/api/child/home').then(r => r.data),
  quest: (id) => api.get(`/api/child/quest/${id}`).then(r => r.data),
  answer: (payload) => api.post('/api/child/answer', payload).then(r => r.data),
  complete: (id) => api.post(`/api/child/complete/${id}`).then(r => r.data),
  extraQuest: () => api.post('/api/child/extra-quest').then(r => r.data),
  review: (id) => api.get(`/api/child/session/${id}/review`).then(r => r.data),
  startBeltExam: () => api.post('/api/child/belt-exam/start').then(r => r.data),
  weakSpots: () => api.get('/api/child/weak-spots').then(r => r.data),
  recentQuests: () => api.get('/api/child/recent-quests').then(r => r.data),
  weakSpotQuest: () => api.post('/api/child/weak-spot-quest').then(r => r.data),
  hint: (qid) => api.get(`/api/child/hint/${qid}`).then(r => r.data),
  soundToggle: () => api.post('/api/child/sound-toggle').then(r => r.data),
}

export const tablesApi = {
  log: (payload) => api.post('/api/tables/session/log', payload).then(r => r.data),
  heatmap: () => api.get('/api/tables/heatmap').then(r => r.data),
  setTarget: (payload) => api.post('/api/tables/target', payload).then(r => r.data),
  weakFacts: () => api.get('/api/tables/weak-facts').then(r => r.data),
}

export const parentApi = {
  login: (email, password) => api.post('/api/auth/login', { email, password }).then(r => r.data),
  dashboard: () => api.get('/api/parent/dashboard').then(r => r.data),
  mastery: () => api.get('/api/parent/mastery').then(r => r.data),
  topicRecent: (topic) => api.get(`/api/parent/mastery/${encodeURIComponent(topic)}/recent`).then(r => r.data),
  suggestions: () => api.get('/api/parent/suggestions').then(r => r.data),
  approve: (id) => api.post(`/api/parent/suggestion/${id}/approve`).then(r => r.data),
  dismiss: (id) => api.post(`/api/parent/suggestion/${id}/dismiss`).then(r => r.data),
  assignBonus: (payload) => api.post('/api/parent/assign-bonus', payload).then(r => r.data),
  restDay: (date) => api.post('/api/parent/rest-day', { date }).then(r => r.data),
  history: (subject) => api.get('/api/parent/history', { params: subject ? { subject } : {} }).then(r => r.data),
  weekly: () => api.get('/api/parent/weekly-summary').then(r => r.data),
  beltStatus: () => api.get('/api/parent/belt-status').then(r => r.data),
  beltSchedule: () => api.post('/api/parent/belt-exam/schedule').then(r => r.data),
  beltOverride: (belt) => api.post('/api/parent/belt-exam/override-gate', null, { params: { belt } }).then(r => r.data),
  beltHistory: () => api.get('/api/parent/belt-exam/history').then(r => r.data),
  templates: () => api.get('/api/parent/templates').then(r => r.data),
  scanTemplate: (file) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post('/api/parent/scan-template', fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
  },
  confirmTemplate: (id, source_name) => api.post('/api/parent/template/confirm', { template_id: id, source_name }).then(r => r.data),
  deleteTemplate: (id) => api.delete(`/api/parent/template/${id}`).then(r => r.data),
  assignFromTemplate: (id, count) => api.post('/api/parent/assign-from-template', { template_id: id, questions_count: count }).then(r => r.data),
  maxControls: () => api.get('/api/parent/max-controls').then(r => r.data),
  maxUpdate: (payload) => api.post('/api/parent/max-controls/update', payload).then(r => r.data),
  maxReset: () => api.post('/api/parent/max-controls/reset').then(r => r.data),
  notifications: () => api.get('/api/parent/notifications').then(r => r.data),
  notifRead: (id) => api.post(`/api/parent/notifications/${id}/read`).then(r => r.data),
  setTablesTarget: (payload) => api.post('/api/tables/target', payload).then(r => r.data),
  tablesHeatmap: () => api.get('/api/tables/heatmap').then(r => r.data),
}
