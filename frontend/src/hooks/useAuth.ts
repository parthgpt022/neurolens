// frontend/src/hooks/useAuth.ts
import { create } from 'zustand'
import { authApi, type User } from '../api/services'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('neurolens_token'),
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true })
    const { data } = await authApi.login(email, password)
    localStorage.setItem('neurolens_token', data.access_token)
    set({ user: data.user, token: data.access_token, isLoading: false })
  },

  register: async (email, name, password) => {
    set({ isLoading: true })
    const { data } = await authApi.register(email, name, password)
    localStorage.setItem('neurolens_token', data.access_token)
    set({ user: data.user, token: data.access_token, isLoading: false })
  },

  logout: () => {
    localStorage.removeItem('neurolens_token')
    set({ user: null, token: null })
    window.location.href = '/login'
  },

  loadUser: async () => {
    const token = localStorage.getItem('neurolens_token')
    if (!token) return
    try {
      const { data } = await authApi.me()
      set({ user: data, token })
    } catch {
      localStorage.removeItem('neurolens_token')
      set({ user: null, token: null })
    }
  },
}))
