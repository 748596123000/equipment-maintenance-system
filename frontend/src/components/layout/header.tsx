import { useLocation, useNavigate } from 'react-router-dom'
import { User } from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
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
  '/knowledge': '知识管理',
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

  const title = routeTitles[location.pathname] || '设备检修知识系统'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-100 transition-colors">
            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
              <User size={16} className="text-slate-600" />
            </div>
            <span className="text-slate-700">{user?.username || '用户'}</span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => navigate('/profile')}>
            个人信息
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout}>
            退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
