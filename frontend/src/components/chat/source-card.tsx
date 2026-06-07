import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/hooks/useTheme'

interface SourceItem {
  source: string
  content: string
  score?: number
}

interface SourceCardProps {
  sources: SourceItem[]
  forceDark?: boolean
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen) + '...'
}

export function SourceCard({ sources, forceDark }: SourceCardProps) {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const effectiveLight = forceDark ? false : isLight
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  const textMuted = effectiveLight ? '#64748b' : '#6b7280'
  const textPrimary = effectiveLight ? '#1e293b' : '#e8e8f0'
  const textSecondary = effectiveLight ? '#475569' : '#a0a0c0'
  const bgCard = effectiveLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.6)'
  const borderColor = effectiveLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)'
  const badgeBg = effectiveLight ? '#f1f5f9' : 'rgba(0, 240, 255, 0.15)'

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-sm transition-colors"
        style={{ color: textMuted }}
      >
        <span>📚 引用来源</span>
        <span className="text-xs">({sources.length})</span>
        <span className="text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((item, idx) => (
            <Card 
              key={idx} 
              className="transition-colors"
              style={{ 
                background: bgCard,
                border: `1px solid ${borderColor}`
              }}
            >
              <CardContent className="p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium" style={{ color: textPrimary }}>
                    {item.source}
                  </span>
                  {item.score !== undefined && (
                    <Badge 
                      variant="secondary" 
                      className="text-xs"
                      style={{ 
                        background: badgeBg,
                        color: effectiveLight ? '#475569' : '#00f0ff'
                      }}
                    >
                      相似度: {(item.score * 100).toFixed(1)}%
                    </Badge>
                  )}
                </div>
                <p 
                  className="text-xs leading-relaxed"
                  style={{ color: textSecondary }}
                >
                  {truncate(item.content, 200)}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}