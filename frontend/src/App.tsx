import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from './components/layout/app-layout'
import { AdminGuard } from './components/guards/admin-guard'
import { initTheme } from './hooks/useTheme'
import { useGlobalShortcuts } from './hooks/useKeyboardShortcuts'

const LoginPage = lazy(() => import('./pages/login'))
const RegisterPage = lazy(() => import('./pages/register'))
const DashboardPage = lazy(() => import('./pages/dashboard'))
const SearchPage = lazy(() => import('./pages/search'))
const GuidePage = lazy(() => import('./pages/guide'))
const GuideGeneratePage = lazy(() => import('./pages/guide-generate'))
const KnowledgePage = lazy(() => import('./pages/knowledge'))
const CasesPage = lazy(() => import('./pages/cases'))
const KnowledgeGraphPage = lazy(() => import('./pages/knowledge-graph'))
const KnowledgeBasePage = lazy(() => import('./pages/knowledge-base'))
const DatabasePage = lazy(() => import('./pages/database'))
const AdminPage = lazy(() => import('./pages/admin'))
const ProfilePage = lazy(() => import('./pages/profile'))
const ApiSettingsPage = lazy(() => import('./pages/api-settings'))

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div 
        className="w-10 h-10 border-4 border-[var(--color-border,#e2e8f0)] border-t-[var(--cyber-cyan,#00f0ff)] rounded-full animate-spin"
        style={{ 
          borderColor: 'var(--color-border, #e2e8f0)',
          borderTopColor: 'var(--cyber-cyan, #00f0ff)'
        }}
      />
    </div>
  )
}

function AppContent() {
  useGlobalShortcuts()
  useEffect(() => {
    initTheme()
  }, [])
  return <></>
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="guide" element={<GuidePage />} />
            <Route path="guide-generate" element={<GuideGeneratePage />} />
            <Route path="knowledge" element={<KnowledgePage />} />
            <Route path="cases" element={<CasesPage />} />
            <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
            <Route path="kb" element={<KnowledgeBasePage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="api-settings" element={<AdminGuard><ApiSettingsPage /></AdminGuard>} />
            <Route path="database" element={<AdminGuard><DatabasePage /></AdminGuard>} />
            <Route path="admin" element={<AdminGuard><AdminPage /></AdminGuard>} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
