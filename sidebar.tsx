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
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { useFontSizeStore } from '@/stores/font-size-store'
import type { FontSize } from '@/stores/font-size-store'
import { useState } from 'react'

const navItems = [
  { label: '首页', path: '/', icon: Home, adminOnly: false },
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
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const filteredItems = navItems.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  )

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-gray-50 border-r flex flex-col transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      {/* Logo / Brand */}
      <div className={`h-14 flex items-center border-b ${collapsed ? 'justify-center px-2' : 'px-4'}`}>
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center">
              <Wrench size={16} className="text-white" />
            </div>
            <h1 className="text-sm font-semibold text-gray-900">设备检修</h1>
          </div>
        )}
        {collapsed && (
          <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center">
            <Wrench size={16} className="text-white" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {filteredItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 mx-2 my-0.5 px-3 py-2.5 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} className="flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Font size controls */}
      {!collapsed && (
        <div className="px-3 py-2 border-t">
          <div className="flex items-center gap-2 mb-2">
            <ALargeSmall size={14} className="text-gray-400" />
            <span className="text-xs text-gray-500">字体大小</span>
          </div>
          <div className="flex gap-1">
            {fontSizes.map((fs) => (
              <button
                key={fs.value}
                onClick={() => setFontSize(fs.value)}
                className={`flex-1 py-1 rounded text-xs font-medium transition-colors ${
                  fontSize === fs.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                }`}
              >
                {fs.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="h-10 flex items-center justify-center border-t text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        title={collapsed ? '展开' : '收起'}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>

      {/* User section */}
      <div className={`border-t ${collapsed ? 'p-2' : 'p-3'}`}>
        {collapsed ? (
          <button
            onClick={() => navigate('/profile')}
            className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center text-sm text-gray-600 hover:bg-gray-300 transition-colors mx-auto"
            title="个人信息"
          >
            {user?.username?.charAt(0) || '?'}
          </button>
        ) : (
          <>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm text-white">
                {user?.username?.charAt(0) || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{user?.username || '未登录'}</p>
                <p className="text-xs text-gray-500">{user?.role === 'admin' ? '管理员' : '普通用户'}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-600 transition-colors w-full"
            >
              <LogOut size={14} />
              <span>退出登录</span>
            </button>
          </>
        )}
      </div>
    </aside>
  )
}