import { create } from 'zustand'

export interface User {
  id: string
  username: string
  role: 'admin' | 'user'
  avatar?: string
}

const AUTH_KEY = 'equipment_maintenance_auth'

interface AuthState {
  user: User | null
  token: string | null
  login: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  (set) => ({
    user: null,
    token: null,
    login: (user, token) => {
      sessionStorage.setItem(AUTH_KEY, JSON.stringify({ user, token }))
      set({ user, token })
    },
    logout: () => {
      sessionStorage.removeItem(AUTH_KEY)
      set({ user: null, token: null })
    },
  })
)

if (typeof window !== 'undefined') {
  const stored = sessionStorage.getItem(AUTH_KEY)
  if (stored) {
    try {
      const { user, token } = JSON.parse(stored)
      if (user && token) {
        useAuthStore.setState({ user, token })
      }
    } catch {}
  }
}
