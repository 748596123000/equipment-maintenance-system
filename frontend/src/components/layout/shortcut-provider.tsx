import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search, FileText, MessageSquare, BookOpen, Database, User, Settings, Plus, HelpCircle
} from 'lucide-react'

const shortcuts = [
  {
    key: 'k',
    ctrl: true,
    description: '打开全局搜索',
    action: 'search',
    icon: <Search className="w-4 h-4" />,
  },
  {
    key: '1',
    ctrl: true,
    description: '仪表盘',
    action: '/',
    icon: <FileText className="w-4 h-4" />,
  },
  {
    key: '2',
    ctrl: true,
    description: '知识检索',
    action: '/search',
    icon: <Search className="w-4 h-4" />,
  },
  {
    key: '3',
    ctrl: true,
    description: 'AI问答',
    action: '/knowledge',
    icon: <MessageSquare className="w-4 h-4" />,
  },
  {
    key: '4',
    ctrl: true,
    description: '知识库',
    action: '/kb',
    icon: <BookOpen className="w-4 h-4" />,
  },
  {
    key: '5',
    ctrl: true,
    description: '作业指引',
    action: '/guide',
    icon: <FileText className="w-4 h-4" />,
  },
  {
    key: '6',
    ctrl: true,
    description: '案例管理',
    action: '/cases',
    icon: <Database className="w-4 h-4" />,
  },
  {
    key: '9',
    ctrl: true,
    description: '个人中心',
    action: '/profile',
    icon: <User className="w-4 h-4" />,
  },
  {
    key: '0',
    ctrl: true,
    description: 'API设置',
    action: '/api-settings',
    icon: <Settings className="w-4 h-4" />,
  },
  {
    key: 'n',
    ctrl: true,
    shift: true,
    description: '新建对话',
    action: 'new-chat',
    icon: <Plus className="w-4 h-4" />,
  },
  {
    key: 'h',
    ctrl: true,
    description: '快捷键帮助',
    action: 'help',
    icon: <HelpCircle className="w-4 h-4" />,
  },
]

export function ShortcutProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
      const isCtrl = isMac ? e.metaKey : e.ctrlKey

      const matchingShortcut = shortcuts.find(
        (sc) =>
          sc.key.toLowerCase() === e.key.toLowerCase() &&
          sc.ctrl === isCtrl &&
          (sc.shift ? e.shiftKey : true)
      )

      if (matchingShortcut) {
        e.preventDefault()

        if (matchingShortcut.action === 'search') {
          const searchBtn = document.querySelector('[data-global-search-trigger]') as HTMLElement
          if (searchBtn) searchBtn.click()
        } else if (matchingShortcut.action === 'new-chat') {
          navigate('/knowledge')
        } else if (matchingShortcut.action === 'help') {
          // 创建临时帮助提示
          const helpDiv = document.createElement('div')
          helpDiv.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: #1a1a2e; border: 2px solid #3b82f6; border-radius: 16px;
            padding: 24px; z-index: 10000; color: #e8e8e8; max-width: 400px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
          `
          helpDiv.innerHTML = `
            <h3 style="color: #3b82f6; margin-top: 0; margin-bottom: 16px;">⌨️ 快捷键帮助</h3>
            <div style="display: flex; flex-direction: column; gap: 10px; font-size: 14px;">
              ${shortcuts.map(s => `
                <div style="display: flex; justify-content: space-between; gap: 16px;">
                  <span>${s.description}</span>
                  <span style="color: #3b82f6; font-family: monospace; background: rgba(59, 130, 246, 0.1); padding: 2px 8px; border-radius: 4px;">
                    Ctrl+${s.key}
                  </span>
                </div>
              `).join('')}
            </div>
            <button id="help-close" style="
              margin-top: 20px; padding: 8px 24px; background: #3b82f6; color: white;
              border: none; border-radius: 8px; cursor: pointer; font-weight: bold;
            ">关闭</button>
          `
          document.body.appendChild(helpDiv)
          document.getElementById('help-close')?.addEventListener('click', () => {
            helpDiv.remove()
          })
          helpDiv.addEventListener('click', (ev) => {
            if (ev.target === helpDiv) helpDiv.remove()
          })
        } else if (typeof matchingShortcut.action === 'string' && matchingShortcut.action.startsWith('/')) {
          navigate(matchingShortcut.action)
        }
      }

      if (isCtrl && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        const searchBtn = document.querySelector('[data-global-search-trigger]') as HTMLElement
        if (searchBtn) searchBtn.click()
      }
    },
    [navigate]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return <>{children}</>
}
