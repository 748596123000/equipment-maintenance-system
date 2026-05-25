import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  Home,
  Search,
  BookOpen,
  Wrench,
  Database,
  Settings,
  Shield,
  LogOut,
  ALargeSmall,
  Settings2,
  ClipboardList,
  FileText,
  Network,
  User,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { useFontSizeStore } from '@/stores/font-size-store'
import { useTheme, COLORS } from '@/hooks/useTheme'
import type { FontSize } from '@/stores/font-size-store'
import { useState, useEffect, memo } from 'react'
import { GradientText } from '@/components/ui/gradient-text'

// Sidebar-specific colors (extend shared COLORS with sidebar-specific properties)
const SIDEBAR_COLORS = {
  dark: {
    ...COLORS.dark,
    sidebarBg: 'linear-gradient(180deg, #070712 0%, #0a0a1f 100%)',
    sidebarText: '#e8e8f0',
    sidebarTextMuted: '#505080',
    sidebarBorder: 'rgba(0, 240, 255, 0.15)',
    activeBg: 'rgba(0, 240, 255, 0.15)',
    activeText: '#00f0ff',
    navItemColor: '#6b7280',
    logoGradient: 'linear-gradient(135deg, #00f0ff 0%, #0066ff 100%)',
  },
light: {
    ...COLORS.light,
    sidebarBg: '#ffffff',
    sidebarText: '#1e293b',
    sidebarTextMuted: '#94a3b8',
    sidebarBorder: '#e2e8f0',
    activeBg: '#eff6ff',
    activeText: '#2563eb',
    navItemColor: '#64748b',
    logoGradient: 'linear-gradient(135deg, #2563eb 0%, #0891b2 100%)',
  }
}

const navItems = [
  { label: '首页', path: '/', icon: Home, adminOnly: false },
  { label: '个人信息', path: '/profile', icon: User, adminOnly: false },
  { label: '知识检索', path: '/search', icon: Search, adminOnly: false },
  { label: '作业指引', path: '/guide', icon: Wrench, adminOnly: false },
  { label: '指引生成', path: '/guide-generate', icon: FileText, adminOnly: false },
  { label: '知识管理', path: '/knowledge', icon: BookOpen, adminOnly: false },
  { label: '案例管理', path: '/cases', icon: ClipboardList, adminOnly: false },
  { label: '知识图谱', path: '/knowledge-graph', icon: Network, adminOnly: false },
  { label: '知识库', path: '/kb', icon: Database, adminOnly: false },
  { label: '文档数据库', path: '/database', icon: Database, adminOnly: true },
  { label: '系统管理', path: '/admin', icon: Shield, adminOnly: true },
  { label: 'API 管理', path: '/api-settings', icon: Settings2, adminOnly: true },
]

const fontSizes: { value: FontSize; label: string }[] = [
  { value: 'small', label: '小' },
  { value: 'medium', label: '中' },
  { value: 'large', label: '大' },
]

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const { fontSize, setFontSize } = useFontSizeStore()
  const { theme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  const isLight = theme === 'light'
  
  // Get theme-specific sidebar colors
  const colors = isLight ? SIDEBAR_COLORS.light : SIDEBAR_COLORS.dark

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileOpen(false)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [mobileOpen])

  const handleLogout = () => {
    logout()
    navigate('/login')
    setMobileOpen(false)
  }

  const handleNavClick = () => {
    if (window.innerWidth < 1024) {
      setMobileOpen(false)
    }
  }

  const filteredItems = navItems.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  )

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-3 left-3 z-[60] lg:hidden w-11 h-11 rounded-lg flex items-center justify-center"
        style={{ 
          background: isLight ? '#ffffff' : 'rgba(7, 7, 18, 0.95)',
          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '30'}`,
          boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.08)' : 'none'
        }}
        aria-label="打开导航菜单"
        aria-expanded={mobileOpen}
        aria-controls="mobile-sidebar"
      >
        <Menu size={20} style={{ color: colors.accentColor }} />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 z-[70] lg:hidden"
          style={{ background: isLight ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.7)' }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Desktop sidebar - Theme-aware Style */}
      <aside 
        className={`hidden lg:flex fixed left-0 top-0 h-full flex-col transition-all duration-300 z-50 ${
          collapsed ? 'w-16' : 'w-60'
        }`}
        style={{ 
          background: colors.sidebarBg,
          borderRight: `1px solid ${colors.sidebarBorder}`,
          boxShadow: isLight ? '2px 0 10px rgba(0, 0, 0, 0.05)' : 'none'
        }}
      >
        
        {/* Header / Logo */}
        <div 
          className="h-16 flex items-center border-b relative"
          style={{ borderColor: colors.sidebarBorder }}
        >
          <div 
            className={`flex items-center gap-2 ${collapsed ? 'justify-center w-full px-2' : 'px-4'}`}
          >
            <div 
              className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ 
                background: colors.logoGradient,
                boxShadow: isLight 
                  ? '0 4px 12px rgba(37, 99, 235, 0.25)' 
                  : `0 0 20px ${colors.CYBER_CYAN}40`
              }}
            >
              <Wrench size={18} style={{ color: isLight ? '#ffffff' : '#000' }} />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <GradientText
                  as="span"
                  className="text-sm font-semibold leading-tight"
                  style={{ 
                    background: isLight 
                      ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)`
                      : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`,
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text'
                  }}
                >
                  设备检修
                </GradientText>
                <GradientText
                  as="span"
                  className="text-[10px] leading-tight mt-0.5"
                  style={{ 
                    background: isLight
                      ? `linear-gradient(90deg, ${colors.CYBER_BLUE}80 0%, ${colors.CYBER_CYAN} 100%)`
                      : `linear-gradient(90deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_CYAN} 100%)`,
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                    letterSpacing: '0.05em',
                    opacity: isLight ? 0.8 : 1
                  }}
                >
                  龙芯中科技术股份有限公司
                </GradientText>
              </div>
            )}
          </div>
        </div>

        {/* Navigation - Theme-aware style */}
        <nav className="flex-1 py-4 overflow-y-auto px-2 scrollbar-luxury">
          {filteredItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={handleNavClick}
                className={`flex items-center gap-3 my-1 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                  isActive ? 'active' : ''
                }`}
                style={{
                  background: isActive ? colors.activeBg : 'transparent',
                  color: isActive ? colors.activeText : colors.navItemColor,
                  border: isActive 
                    ? `1px solid ${isLight ? colors.CYBER_BLUE + '20' : colors.CYBER_CYAN + '30'}` 
                    : '1px solid transparent'
                }}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={18} className="flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>

        {/* Font size controls - Theme-aware */}
        {!collapsed && (
          <div 
            className="px-4 py-3 border-t"
            style={{ borderColor: colors.sidebarBorder }}
          >
            <div className="flex items-center gap-2 mb-2">
              <ALargeSmall size={14} style={{ color: colors.sidebarTextMuted }} />
              <span className="text-xs" style={{ color: colors.sidebarTextMuted }}>字体大小</span>
            </div>
            <div className="flex gap-1">
              {fontSizes.map((fs) => (
                <button
                  key={fs.value}
                  onClick={() => setFontSize(fs.value)}
                  className="flex-1 py-1.5 rounded text-xs font-medium transition-all duration-200"
                  style={{
                    background: fontSize === fs.value 
                      ? colors.accentColor
                      : (isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.8)'),
                    color: fontSize === fs.value 
                      ? (isLight ? '#ffffff' : '#000000') 
                      : colors.navItemColor,
                    border: `1px solid ${
                      fontSize === fs.value 
                        ? colors.accentColor 
                        : (isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)')
                    }`
                  }}
                >
                  {fs.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Collapse toggle - Theme-aware */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="h-10 flex items-center justify-center border-t transition-colors"
          style={{ 
            borderColor: colors.sidebarBorder,
            color: colors.sidebarTextMuted
          }}
          title={collapsed ? '展开' : '收起'}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>

        {/* User info & logout - Theme-aware */}
        <div 
          className={`border-t ${collapsed ? 'p-2' : 'p-4'}`}
          style={{ borderColor: colors.sidebarBorder }}
        >
          {collapsed ? (
            <div className="flex justify-center">
              <button
                onClick={() => navigate('/profile')}
                className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold"
                style={{ 
                  background: colors.logoGradient,
                  color: isLight ? '#ffffff' : '#000000',
                  boxShadow: isLight ? '0 4px 12px rgba(37, 99, 235, 0.3)' : 'none'
                }}
                title="个人信息"
              >
                {user?.username?.charAt(0)?.toUpperCase() || '?'}
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3 mb-3">
                <div 
                  className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold"
                  style={{ 
                    background: colors.logoGradient,
                    color: isLight ? '#ffffff' : '#000000'
                  }}
                >
                  {user?.username?.charAt(0)?.toUpperCase() || '?'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: colors.sidebarText }}>
                    {user?.username || '未登录'}
                  </p>
                  <p className="text-xs" style={{ color: colors.sidebarTextMuted }}>
                    {user?.role === 'admin' ? '管理员' : '普通用户'}
                  </p>
                </div>
                <button
                  onClick={() => navigate('/profile')}
                  className="p-1.5 rounded transition-colors"
                  style={{ color: colors.sidebarTextMuted }}
                >
                  <Settings size={16} />
                </button>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-xs transition-colors w-full py-2"
                style={{ color: colors.CYBER_RED }}
              >
                <LogOut size={14} />
                <span>退出登录</span>
              </button>
            </>
          )}
        </div>
      </aside>

      {/* Mobile sidebar - Theme-aware */}
      <aside 
        id="mobile-sidebar"
        className={`fixed left-0 top-0 h-full w-64 flex flex-col z-[80] lg:hidden transition-transform duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ 
          background: colors.sidebarBg,
          borderRight: `1px solid ${colors.sidebarBorder}`,
          boxShadow: isLight ? '4px 0 20px rgba(0, 0, 0, 0.1)' : 'none'
        }}
        role="navigation"
        aria-label="移动端导航"
        aria-hidden={!mobileOpen}
      >
        {/* Mobile Header */}
        <div 
          className="h-16 flex items-center justify-between px-4 border-b"
          style={{ borderColor: colors.sidebarBorder }}
        >
          <div className="flex items-center gap-2">
            <div 
              className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ 
                background: colors.logoGradient,
                boxShadow: isLight ? '0 4px 12px rgba(37, 99, 235, 0.25)' : 'none'
              }}
            >
              <Wrench size={18} style={{ color: isLight ? '#ffffff' : '#000' }} />
            </div>
            <div className="flex flex-col">
              <GradientText
                as="span"
                className="text-sm font-semibold leading-tight"
                style={{ 
                  background: isLight 
                    ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)`
                    : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}
              >
                设备检修
              </GradientText>
              <GradientText
                as="span"
                className="text-[10px] leading-tight mt-0.5"
                style={{ 
                  background: isLight
                    ? `linear-gradient(90deg, ${colors.CYBER_BLUE}80 0%, ${colors.CYBER_CYAN} 100%)`
                    : `linear-gradient(90deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_CYAN} 100%)`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  letterSpacing: '0.05em',
                  opacity: isLight ? 0.8 : 1
                }}
              >
                龙芯中科技术股份有限公司
              </GradientText>
            </div>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1.5 rounded-lg"
            style={{ color: colors.accentColor }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Mobile Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto px-3">
          {filteredItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={handleNavClick}
                className="flex items-center gap-3 my-1 px-3 py-2.5 rounded-lg text-sm transition-all duration-200"
                style={{
                  background: isActive ? colors.activeBg : 'transparent',
                  color: isActive ? colors.activeText : colors.navItemColor,
                  border: isActive ? (isLight ? `1px solid ${colors.CYBER_BLUE}20` : `1px solid ${colors.CYBER_CYAN}30`) : '1px solid transparent'
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Mobile Footer */}
        <div 
          className="p-4 border-t"
          style={{ borderColor: colors.sidebarBorder }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div 
              className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold"
              style={{ 
                background: colors.logoGradient,
                color: isLight ? '#ffffff' : '#000000'
              }}
            >
              {user?.username?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: colors.sidebarText }}>
                {user?.username || '未登录'}
              </p>
              <p className="text-xs" style={{ color: colors.sidebarTextMuted }}>
                {user?.role === 'admin' ? '管理员' : '普通用户'}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs transition-colors w-full py-2"
            style={{ color: colors.CYBER_RED }}
          >
            <LogOut size={14} />
            <span>退出登录</span>
          </button>
        </div>
      </aside>
    </>
  )
}