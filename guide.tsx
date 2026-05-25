import { useState, useEffect, useCallback } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ChatPanel } from '@/components/chat/chat-panel'
import { api } from '@/lib/api'
import { Search, ChevronDown, ChevronUp } from 'lucide-react'

const CATEGORIES = [
  '通用', '变压器', '开关柜', '断路器', '隔离开关',
  '互感器', '避雷器', '电容器', '电缆', '继电保护装置', '其他',
]

interface KnowledgeItem {
  id: string
  title: string
  category: string
  content: string
  file_type: string
  chunk_count: number
  status: string
}

export default function GuidePage() {
  const [category, setCategory] = useState('通用')
  const [keyword, setKeyword] = useState('')
  const [guides, setGuides] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [previewContent, setPreviewContent] = useState<Record<string, string>>({})

  const fetchGuides = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page_size: '100' }
      if (category) params.category = category
      if (keyword.trim()) params.keyword = keyword.trim()

      const response = await api.get<{ documents: Array<{ document_id: string; filename: string; category: string; file_type: string; chunk_count: number; status: string }> }>('/upload/list', { params })
      const docs = response.data.documents || []
      setGuides(docs.map(doc => ({
        id: doc.document_id,
        title: doc.filename,
        category: doc.category || '未分类',
        content: `${doc.file_type.toUpperCase()} 文档 | ${doc.chunk_count} 个分块 | 状态: ${doc.status}`,
        file_type: doc.file_type,
        chunk_count: doc.chunk_count,
        status: doc.status,
      })))
    } catch {
      setGuides([])
    } finally {
      setLoading(false)
    }
  }, [category, keyword])

  useEffect(() => {
    fetchGuides()
  }, [fetchGuides])

  const toggleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    setExpandedId(id)
    if (!previewContent[id]) {
      try {
        const res = await api.get<{ content: string }>(`/upload/${id}/preview`)
        setPreviewContent(prev => ({ ...prev, [id]: res.data.content || '暂无内容' }))
      } catch {
        setPreviewContent(prev => ({ ...prev, [id]: '加载预览内容失败' }))
      }
    }
  }

  const handleSearch = () => {
    fetchGuides()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">📋 作业指引</h1>

      <Tabs defaultValue="chat" className="w-full">
        <TabsList>
          <TabsTrigger value="chat">智能问答</TabsTrigger>
          <TabsTrigger value="regulations">作业规程</TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="h-[calc(100vh-220px)]">
          <ChatPanel
            sessionKey="guide_chat"
            title="作业指引问答"
            searchMode="hybrid"
            topK={5}
          />
        </TabsContent>

        <TabsContent value="regulations">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-48">
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择分类" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((cat) => (
                      <SelectItem key={cat} value={cat}>
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1">
                <Input
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="搜索作业规程..."
                />
              </div>
              <Button onClick={handleSearch} disabled={loading}>
                <Search className="mr-1 h-4 w-4" />
                搜索
              </Button>
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Card key={i}>
                    <CardHeader>
                      <div className="h-5 w-48 animate-pulse rounded bg-muted" />
                    </CardHeader>
                    <CardContent>
                      <div className="h-4 w-full animate-pulse rounded bg-muted" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : guides.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <p className="text-lg">暂无作业规程</p>
                <p className="mt-1 text-sm">请尝试更换分类或关键词</p>
              </div>
            ) : (
              <div className="space-y-3">
                {guides.map((guide) => (
                  <Card key={guide.id}>
                    <CardHeader
                      className="cursor-pointer"
                      onClick={() => toggleExpand(guide.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-base">{guide.title}</CardTitle>
                          <Badge variant="secondary">{guide.category}</Badge>
                        </div>
                        {expandedId === guide.id ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    </CardHeader>
                    {expandedId === guide.id && (
                      <CardContent>
                        <div className="prose prose-sm max-w-none text-muted-foreground whitespace-pre-wrap">
                          {previewContent[guide.id] || '加载中...'}
                        </div>
                      </CardContent>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
