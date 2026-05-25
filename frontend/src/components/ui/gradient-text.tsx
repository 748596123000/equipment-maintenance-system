import type { ReactNode, CSSProperties } from 'react'
import { useTheme } from '@/hooks/useTheme'

interface GradientTextProps {
  children: ReactNode
  style: CSSProperties
  className?: string
  as?: 'span' | 'h1' | 'h2' | 'h3' | 'p' | 'div'
}

export function GradientText({ children, style, className, as: Tag = 'span' }: GradientTextProps) {
  const { theme } = useTheme()
  return (
    <Tag key={theme} className={className} style={style}>
      {children}
    </Tag>
  )
}
