import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
})

export { API_BASE_URL }

export async function sendChatMessage(message, conversationId) {
  const payload = conversationId ? { message, conversation_id: conversationId } : { message }
  const { data } = await client.post('/api/chat', payload)
  return data
}

export async function searchPOs(query) {
  const { data } = await client.post('/api/search', { query })
  return data
}

export async function getPODetails(id) {
  const { data } = await client.get(`/api/po/${id}`)
  return data
}

export async function exportPO(id) {
  const { data } = await client.get(`/api/po/${id}/export`)
  return data
}

export async function getAuthStatus() {
  const { data } = await client.get('/auth/status')
  return data
}

export async function getAuthLoginUrl(state) {
  const { data } = await client.get('/auth/login', { params: { state } })
  return data
}

export async function disconnectAuth() {
  const { data } = await client.delete('/auth/token')
  return data
}

export async function triggerSync() {
  const { data } = await client.post('/api/sync')
  return data
}

export async function getAnalytics() {
  const { data } = await client.get('/api/analytics')
  return data
}
