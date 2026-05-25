import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { AuthGuard } from '@/components/guards/auth-guard'

export function AppLayout() {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-slate-50">
        <Sidebar />
        <div className="ml-64">
          <Header />
          <main className="p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </AuthGuard>
  )
}
