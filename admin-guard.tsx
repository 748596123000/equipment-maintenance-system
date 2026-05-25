import { Navigate, Outlet, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import type { ReactNode } from 'react'

interface AdminGuardProps {
  children?: ReactNode
}

export function AdminGuard({ children }: AdminGuardProps) {
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

  if (user.role !== 'admin') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">需要管理员权限</h2>
          <Link to="/" className="text-blue-500 hover:underline">返回首页</Link>
        </div>
      </div>
    )
  }

  return children ? <>{children}</> : <Outlet />
}
