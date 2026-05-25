import { useLocation, useNavigate } from 'react-router-dom'
import {
  Search,
  Bell,
  Sun,
  Moon,
  User,
  Settings,
  LogOut,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { useState, useEffect } from 'react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const routeTitles: Record<string, string> = {
  '/': '首页',
  '/search': '知识检索',
  '/guide': '作业指引',
  '/guide-generate': '指引生成',
  '/knowledge': '知识管理',
  '/knowledge-graph': '知识图谱',
  '/cases': '案例管理',
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
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  const title = routeTitles[location.pathname] || '设备检修知识系统'

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
    if (savedTheme) {
      setTheme(savedTheme)
      document.documentElement.classList.toggle('dark', savedTheme === 'dark')
    }
  }, [])

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.documentElement.classList.toggle('dark', newTheme === 'dark')
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Global search shortcut (Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        navigate('/search')
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [navigate])

  return (
    <header className="h-14 bg-white border-b flex items-center justify-between px-6">
      {/* Title */}
      <h2 className="text-base font-medium text-gray-900">{title}</h2>

      {/* Right side controls */}
      <div className="flex items-center gap-1">
        {/* Search button with Ctrl+K hint */}
        <button
          onClick={() => navigate('/search')}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 rounded-md transition-colors"
          title="搜索 (Ctrl+K)"
        >
          <Search size={18} />
          <span className="hidden sm:inline text-xs">搜索</span>
          <kbd className="hidden md:inline text-xs bg-gray-100 px-1.5 py-0.5 rounded border border-gray-200">⌘K</kbd>
        </button>

        {/* Notifications */}
        <button
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-md transition-colors"
          title="通知"
        >
          <Bell size={18} />
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-md transition-colors"
          title={theme === 'light' ? '深色模式' : '浅色模式'}
        >
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
        </button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 ml-2 px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors">
              <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center">
                <User size={14} className="text-white" />
              </div>
              <span className="hidden sm:inline">{user?.username || '用户'}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={() => navigate('/profile')}>
              <Settings size={16} className="mr-2" />
              个人信息
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-red-500">
              <LogOut size={16} className="mr-2" />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}