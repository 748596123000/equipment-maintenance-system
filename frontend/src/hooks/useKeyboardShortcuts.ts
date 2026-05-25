import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface Shortcut {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  action: () => void
  description: string
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const key = event.key.toLowerCase()
      const ctrl = event.ctrlKey || event.metaKey
      const shift = event.shiftKey
      const alt = event.altKey

      for (const shortcut of shortcuts) {
        const shortcutKey = shortcut.key.toLowerCase()
        const shortcutCtrl = shortcut.ctrl || false
        const shortcutShift = shortcut.shift || false
        const shortcutAlt = shortcut.alt || false

        if (
          key === shortcutKey &&
          ctrl === shortcutCtrl &&
          shift === shortcutShift &&
          alt === shortcutAlt
        ) {
          event.preventDefault()
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts])
}

export function useGlobalShortcuts() {
  const navigate = useNavigate()

  const shortcuts: Shortcut[] = [
    {
      key: 'd',
      ctrl: true,
      action: () => navigate('/'),
      description: '返回首页（仪表盘）',
    },
    {
      key: 's',
      ctrl: true,
      action: () => navigate('/search'),
      description: '跳转到知识检索',
    },
    {
      key: 'k',
      ctrl: true,
      action: () => navigate('/knowledge'),
      description: '跳转到知识管理',
    },
    {
      key: 'g',
      ctrl: true,
      shift: true,
      action: () => navigate('/guide-generate'),
      description: '跳转到作业指引生成',
    },
    {
      key: '?',
      shift: true,
      action: () => {
        alert('键盘快捷键：\n\nCtrl+D: 返回首页\nCtrl+S: 知识检索\nCtrl+K: 知识管理\nCtrl+Shift+G: 作业指引\nShift+?: 显示帮助')
      },
      description: '显示帮助',
    },
  ]

  useKeyboardShortcuts(shortcuts)
}
