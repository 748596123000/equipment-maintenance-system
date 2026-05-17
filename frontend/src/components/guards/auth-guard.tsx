import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import type { ReactNode } from 'react'

interface AuthGuardProps {
  children?: ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const user = useAuthStore((s) => s.user)
  const hydrated = useAuthStore((s) => s._hydrated)

  if (!hydrated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-600 rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children ? <>{children}</> : <Outlet />
}
