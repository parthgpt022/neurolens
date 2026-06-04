// frontend/src/api/services.ts
// Typed API functions for every backend endpoint

import { apiClient } from './client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Document {
  id: string
  filename: string
  original_filename: string
  page_count: number
  status: 'pending' | 'processing' | 'done' | 'failed'
  file_size_bytes: number
  created_at: string
  processed_at: string | null
}

export interface DocumentDetail extends Document {
  extracted_text: string | null
  ocr_metadata: Record<string, unknown> | null
}

export interface Entity {
  id: string
  entity_type: string
  value: string
  normalized_value: string | null
  confidence: number
  page_number: number
  bbox: { x: number; y: number; width: number; height: number } | null
}

export interface ChatSession {
  id: string
  title: string
  document_ids: string[]
  created_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[] | null
  latency_ms: number | null
  created_at: string
}

export interface Citation {
  index: number
  text: string
  document_id: string
  page_number: number
  relevance_score: number
}

export interface ChatResponse {
  answer: string
  citations: Citation[]
  latency_ms: number
  message_id: string
}

export interface NPUStatus {
  available_providers: string[]
  active_embed_provider: string
  npu_available: boolean
  vitisai_available: boolean
  directml_available: boolean
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, name: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/register', { email, name, password }),

  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),

  me: () => apiClient.get<User>('/auth/me'),
}

// ── Documents ─────────────────────────────────────────────────────────────────

export const documentsApi = {
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<Document>('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      },
    })
  },

  list: () => apiClient.get<Document[]>('/documents'),

  get: (id: string) => apiClient.get<DocumentDetail>(`/documents/${id}`),

  getEntities: (id: string) => apiClient.get<Entity[]>(`/documents/${id}/entities`),

  delete: (id: string) => apiClient.delete(`/documents/${id}`),
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export const chatApi = {
  createSession: (documentIds: string[], title?: string) =>
    apiClient.post<ChatSession>('/chat/sessions', {
      document_ids: documentIds,
      title: title ?? 'New Chat',
    }),

  listSessions: () => apiClient.get<ChatSession[]>('/chat/sessions'),

  getSession: (id: string) =>
    apiClient.get<ChatSession & { messages: ChatMessage[] }>(`/chat/sessions/${id}`),

  sendMessage: (sessionId: string, message: string) =>
    apiClient.post<ChatResponse>(`/chat/sessions/${sessionId}/messages`, {
      message,
      session_id: sessionId,
    }),

  deleteSession: (id: string) => apiClient.delete(`/chat/sessions/${id}`),
}

// ── System ────────────────────────────────────────────────────────────────────

export const systemApi = {
  health: () => apiClient.get('/system/health'),
  npuStatus: () => apiClient.get<NPUStatus>('/system/npu'),
  benchmark: () => apiClient.get('/system/benchmark'),
}
