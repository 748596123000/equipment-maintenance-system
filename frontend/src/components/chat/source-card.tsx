import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface SourceItem {
  source: string
  content: string
  score?: number
}

interface SourceCardProps {
  sources: SourceItem[]
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen) + '...'
}

export function SourceCard({ sources }: SourceCardProps) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <span>📚 引用来源</span>
        <span className="text-xs">({sources.length})</span>
        <span className="text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((item, idx) => (
            <Card key={idx} className="bg-gray-50">
              <CardContent className="p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-700">
                    {item.source}
                  </span>
                  {item.score !== undefined && (
                    <Badge variant="secondary" className="text-xs">
                      相似度: {(item.score * 100).toFixed(1)}%
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">
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
