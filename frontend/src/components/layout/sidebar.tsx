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
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { useFontSizeStore } from '@/stores/font-size-store'
import type { FontSize } from '@/stores/font-size-store'

const navItems = [
  { label: '首页', path: '/', icon: Home, adminOnly: false },
  { label: '知识检索', path: '/search', icon: Search, adminOnly: false },
  { label: '作业指引', path: '/guide', icon: Wrench, adminOnly: false },
  { label: '知识管理', path: '/knowledge', icon: BookOpen, adminOnly: false },
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

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const filteredItems = navItems.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  )

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-slate-900 text-white flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-lg font-bold">设备检修知识系统</h1>
      </div>

      <nav className="flex-1 py-4">
        {filteredItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                isActive
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div className="px-4 py-3 border-t border-slate-700">
        <div className="flex items-center gap-2 mb-2">
          <ALargeSmall size={16} className="text-slate-400" />
          <span className="text-xs text-slate-400">字体大小</span>
        </div>
        <div className="flex gap-1">
          {fontSizes.map((fs) => (
            <button
              key={fs.value}
              onClick={() => setFontSize(fs.value)}
              className={`flex-1 py-1.5 rounded text-xs font-medium transition-colors ${
                fontSize === fs.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {fs.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center text-sm">
            {user?.username?.charAt(0) || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.username || '未登录'}</p>
            <p className="text-xs text-slate-400">{user?.role === 'admin' ? '管理员' : '普通用户'}</p>
          </div>
          <button
            onClick={() => navigate('/profile')}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <Settings size={16} />
          </button>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors w-full"
        >
          <LogOut size={16} />
          <span>退出登录</span>
        </button>
      </div>
    </aside>
  )
}
