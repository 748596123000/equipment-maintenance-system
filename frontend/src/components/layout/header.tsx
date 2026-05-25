import { useLocation, useNavigate } from 'react-router-dom'
import { Search, ChevronDown, Sun, Moon, Bell, Cpu, Database, Wifi } from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'
import { NotificationDropdown } from './notification-dropdown'
import { GlobalSearch } from './global-search'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useState, useEffect } from 'react'

const LOCAL_COLORS = COLORS

const routeTitles: Record<string, string> = {
  '/': '首页',
  '/search': '知识检索',
  '/guide': '作业指引',
  '/guide-generate': '指引生成',
  '/knowledge': '知识管理',
  '/cases': '案例管理',
  '/knowledge-graph': '知识图谱',
  '/kb': '知识库',
  '/profile': '个人信息',
  '/database': '文档数据库',
  '/admin': '系统管理',
  '/api-settings': 'API 管理',
}

export function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useTheme()
  const [showSearch, setShowSearch] = useState(false)

  const title = routeTitles[location.pathname] || '设备检修知识系统'
  const isLight = theme === 'light'
  
  // Get theme-specific colors
  const colors = isLight ? COLORS.light : COLORS.dark
  
  // Aliases for backward compatibility
  const headerBg = colors.headerBg
  const borderColor = colors.borderColor
  const textPrimary = colors.textPrimary
  const textSecondary = colors.textSecondary
  const textMuted = colors.textMuted
  const accentColor = colors.accentColor

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowSearch(true)
      }
      if (e.key === 'Escape') {
        setShowSearch(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
      <header 
        className="h-16 flex items-center justify-between px-6 relative z-40"
        style={{ 
          background: headerBg,
          borderBottom: `1px solid ${borderColor}`,
          boxShadow: isLight ? '0 2px 10px rgba(0, 0, 0, 0.05)' : 'none',
          width: '100%'
        }}
      >
        {/* Left Section - Title & Status */}
        <div className="flex items-center gap-6 flex-1">
          <GradientText
            as="h2"
            className="text-lg font-bold whitespace-nowrap"
            style={{ 
              background: isLight
                ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)`
                : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '-0.02em'
            }}
          >
            {title}
          </GradientText>
          
          {/* System Status Indicators */}
          <div className="hidden xl:flex items-center gap-4 pl-4" style={{ borderLeft: `1px solid ${borderColor}` }}>
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ background: `${colors.CYBER_BLUE}20` }}>
                  <Cpu size={12} style={{ color: accentColor }} />
                </div>
                {!isLight && (
                  <div 
                    className="absolute inset-0 rounded-full animate-ping"
                    style={{ 
                      background: colors.CYBER_GREEN,
                      opacity: 0.4,
                      animation: 'statusPulse 2s ease-in-out infinite'
                    }} 
                  />
                )}
                <div 
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
                  style={{ 
                    background: colors.CYBER_GREEN, 
                    boxShadow: `0 0 8px ${colors.CYBER_GREEN}`,
                    animation: isLight ? undefined : 'statusPulse 2s ease-in-out infinite'
                  }}
                />
              </div>
              <span className="text-xs whitespace-nowrap" style={{ color: textSecondary }}>CPU</span>
              <span className="text-xs font-medium whitespace-nowrap" style={{ color: colors.CYBER_GREEN }}>正常</span>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ background: `${colors.CYBER_BLUE}15` }}>
                  <Database size={12} style={{ color: colors.CYBER_BLUE }} />
                </div>
                {!isLight && (
                  <div 
                    className="absolute inset-0 rounded-full animate-ping"
                    style={{ 
                      background: colors.CYBER_BLUE,
                      opacity: 0.3,
                      animation: 'statusPulse 2s ease-in-out infinite',
                      animationDelay: '0.5s'
                    }} 
                  />
                )}
              </div>
              <span className="text-xs whitespace-nowrap" style={{ color: textSecondary }}>内存</span>
              <span className="text-xs font-medium whitespace-nowrap" style={{ color: colors.CYBER_BLUE }}>正常</span>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ background: `${colors.CYBER_GREEN}15` }}>
                  <Wifi size={12} style={{ color: colors.CYBER_GREEN }} />
                </div>
                {!isLight && (
                  <div 
                    className="absolute inset-0 rounded-full animate-ping"
                    style={{ 
                      background: colors.CYBER_GREEN,
                      opacity: 0.4,
                      animation: 'statusPulse 2s ease-in-out infinite',
                      animationDelay: '1s'
                    }} 
                  />
                )}
                <div 
                  className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
                  style={{ 
                    background: colors.CYBER_GREEN, 
                    boxShadow: `0 0 8px ${colors.CYBER_GREEN}`,
                    animation: isLight ? undefined : 'statusPulse 2s ease-in-out infinite',
                    animationDelay: '1s'
                  }}
                />
              </div>
              <span className="text-xs whitespace-nowrap" style={{ color: textSecondary }}>网络</span>
              <span className="text-xs font-medium whitespace-nowrap" style={{ color: colors.CYBER_GREEN }}>良好</span>
            </div>
          </div>
        </div>

        {/* Right Section - Actions */}
        <div className="flex items-center gap-3">
          {/* Search Button - Theme-aware */}
          <button 
            data-global-search-trigger
            onClick={() => setShowSearch(true)}
            className="p-2.5 rounded-lg transition-all duration-300"
            style={{ 
              background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.8)',
              border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.15)'}`,
              color: textSecondary
            }}
            title="搜索 (Ctrl+K)"
          >
            <Search size={18} />
          </button>
          
          {/* Theme Toggle - Theme-aware */}
          <button
            onClick={toggleTheme}
            className="p-2.5 rounded-lg transition-all duration-300"
            style={{ 
              background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.8)',
              border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.15)'}`,
              color: textSecondary
            }}
            title={theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          
          {/* Notifications */}
          <NotificationDropdown />

          {/* User Menu - Theme-aware */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button 
                className="flex items-center gap-3 rounded-lg px-3 py-2 transition-all duration-300 group"
                style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.8)',
                  border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.15)'}`
                }}
              >
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                  style={{ 
                    background: `linear-gradient(135deg, ${accentColor} 0%, ${isLight ? '#1d4ed8' : colors.CYBER_BLUE} 100%)`,
                    color: '#ffffff'
                  }}
                >
                  {user?.username?.charAt(0)?.toUpperCase() || '?'}
                </div>
                <span className="text-sm font-medium" style={{ color: textPrimary }}>
                  {user?.username || '用户'}
                </span>
                <ChevronDown 
                  size={14} 
                  style={{ color: textMuted }} 
                  className={`group-hover:text-[${accentColor}] transition-colors`}
                />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent 
              align="end" 
              className="rounded-xl p-2 min-w-[180px]"
              style={{ 
                background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.98)',
                border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.15)'}`,
                boxShadow: isLight ? '0 10px 40px rgba(0, 0, 0, 0.1)' : 'none'
              }}
            >
              <DropdownMenuItem 
                onClick={() => navigate('/profile')} 
                className="px-3 py-2.5 rounded-lg cursor-pointer transition-colors text-sm"
                style={{ color: textPrimary }}
              >
                个人信息
              </DropdownMenuItem>
              <DropdownMenuSeparator 
                className="my-2" 
                style={{ background: isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)' }} 
              />
              <DropdownMenuItem 
                onClick={handleLogout}
                className="px-3 py-2.5 rounded-lg cursor-pointer transition-colors text-sm"
                style={{ color: '#dc2626' }}
              >
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Global Search Modal */}
      {showSearch && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
          <div 
            className="fixed inset-0" 
            onClick={() => setShowSearch(false)} 
            style={{ background: 'rgba(0, 0, 0, 0.5)' }}
          />
          <div className="relative animate-fade-in-up">
            <GlobalSearch onClose={() => setShowSearch(false)} />
          </div>
        </div>
      )}
    </>
  )
}