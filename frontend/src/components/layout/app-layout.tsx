import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { Header } from './header'
import { AuthGuard } from '@/components/guards/auth-guard'
import { ShortcutProvider } from './shortcut-provider'
import { OnboardingTour } from './onboarding-tour'
import { useTheme } from '@/hooks/useTheme'

export function AppLayout() {
  const { theme } = useTheme()
  const isLight = theme === 'light'

  return (
    <AuthGuard>
      <ShortcutProvider>
        <div className="min-h-screen relative overflow-hidden" style={{
          background: isLight ? '#f8fafc' : undefined
        }}>
          {/* CSS-only粒子背景层 - 仅暗色模式显示 */}
          <div className="particle-container" style={{ display: isLight ? 'none' : undefined }}>
            {/* 粒子1-5 */}
            <div className="css-particles" style={{
              left: '10%', animationDelay: '0s', animationDuration: '20s',
              boxShadow: '0 0 6px #00f0ff, 0 0 12px #00f0ff'
            }} />
            <div className="css-particles" style={{
              left: '20%', animationDelay: '3s', animationDuration: '18s',
              boxShadow: '0 0 6px #ff00ff, 0 0 12px #ff00ff'
            }} />
            <div className="css-particles" style={{
              left: '35%', animationDelay: '6s', animationDuration: '22s',
              boxShadow: '0 0 6px #8b5cf6, 0 0 12px #8b5cf6'
            }} />
            <div className="css-particles" style={{
              left: '50%', animationDelay: '9s', animationDuration: '16s',
              boxShadow: '0 0 6px #00f0ff, 0 0 12px #00f0ff'
            }} />
            <div className="css-particles" style={{
              left: '65%', animationDelay: '12s', animationDuration: '24s',
              boxShadow: '0 0 6px #0066ff, 0 0 12px #0066ff'
            }} />
            <div className="css-particles" style={{
              left: '75%', animationDelay: '5s', animationDuration: '19s',
              boxShadow: '0 0 6px #ff00ff, 0 0 12px #ff00ff'
            }} />
            <div className="css-particles" style={{
              left: '85%', animationDelay: '8s', animationDuration: '21s',
              boxShadow: '0 0 6px #00f0ff, 0 0 12px #00f0ff'
            }} />
          </div>

          {/* 扫描线覆盖层 - 仅暗色模式显示 */}
          <div className="scanline-overlay" style={{ display: isLight ? 'none' : undefined }} />

          {/* 环境光效果层 - 仅暗色模式显示 */}
          <div className="ambient-light" style={{ display: isLight ? 'none' : undefined }} />

          {/* 焦散光斑 - 仅暗色模式显示 */}
          <div className="caustic-light" style={{ top: '10%', left: '15%', display: isLight ? 'none' : undefined }} />
          <div className="caustic-light" style={{ bottom: '20%', right: '10%', animationDelay: '2s', display: isLight ? 'none' : undefined }} />

          {/* 底部动态渐变光晕 - 仅暗色模式显示 */}
          <div className="absolute bottom-0 left-1/4 w-[500px] h-[400px] rounded-full blur-[120px]"
               style={{
                 background: 'radial-gradient(circle, rgba(6,182,212,0.05) 0%, transparent 70%)',
                 display: isLight ? 'none' : undefined
               }} />
          <div className="absolute bottom-0 right-1/4 w-[400px] h-[350px] rounded-full blur-[100px]"
               style={{
                 background: 'radial-gradient(circle, rgba(59,130,246,0.04) 0%, transparent 70%)',
                 display: isLight ? 'none' : undefined
               }} />

          {/* 主要内容区域 */}
          <div className="relative z-10">
            <Sidebar />
            <div className="ml-64 min-h-screen">
              <Header />
              <main className="p-6 scrollbar-luxury">
                <Outlet />
              </main>
            </div>
          </div>

          <OnboardingTour />
        </div>
      </ShortcutProvider>
    </AuthGuard>
  )
}