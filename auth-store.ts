import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: string
  username: string
  role: 'admin' | 'user'
  avatar?: string
}

interface AuthState {
  user: User | null
  token: string | null
  _hydrated: boolean
  login: (user: User, token: string) => void
  logout: () => void
  setHydrated: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      _hydrated: false,
      login: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
      setHydrated: () => set({ _hydrated: true }),
    }),
    {
      name: 'equipment_maintenance_auth',
      onRehydrateStorage: () => (state) => {
        state?.setHydrated()
      },
    }
  )
)
