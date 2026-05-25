import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import type { ReactNode } from 'react'

interface AuthGuardProps {
  children?: ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const user = useAuthStore((s) => s.user)

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children ? <>{children}</> : <Outlet />
}
