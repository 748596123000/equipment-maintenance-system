import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from './components/layout/app-layout'
import { AdminGuard } from './components/guards/admin-guard'

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
      <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-600 rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
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
