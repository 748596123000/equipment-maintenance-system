import { useTheme } from '@/hooks/useTheme'
import { Button } from '@/components/ui/button'
import { Sun, Moon } from 'lucide-react'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      className="relative h-9 w-9 rounded-lg hover:bg-[rgba(59,130,246,0.15)]"
      title={theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
    >
      {theme === 'dark' ? (
        <Sun className="h-5 w-5 text-[#3b82f6] transition-transform hover:rotate-45" />
      ) : (
        <Moon className="h-5 w-5 text-[#6366f1] transition-transform hover:-rotate-12" />
      )}
    </Button>
  )
}
