import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/css-tabs'
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
import { api } from '@/lib/api'
import { GradientText } from '@/components/ui/gradient-text'
import { sanitizeSearchInput } from '@/lib/validate'
import { Search, ChevronDown, ChevronUp, BookOpen, Wrench, FileText, Sparkles, ClipboardList, Zap } from 'lucide-react'
import { useTheme, COLORS } from '@/hooks/useTheme'

// Lazy load heavy components
const ChatPanel = lazy(() => import('@/components/chat/chat-panel').then(m => ({ default: m.ChatPanel })))

// Loading fallback with cyberpunk animation
function ComponentLoader() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="relative">
        <div className="w-10 h-10 border-4 border-[var(--color-border,#e2e8f0)] border-t-[#00f0ff] rounded-full animate-spin" />
        <div className="absolute inset-0 w-10 h-10 border-4 border-[rgba(0,240,255,0.3)] border-b-[#6366f1] rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
      </div>
    </div>
  )
}

const LOCAL_COLORS = COLORS

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
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  
  const [category, setCategory] = useState('通用')
  const [keyword, setKeyword] = useState('')
  const [guides, setGuides] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [previewContent, setPreviewContent] = useState<Record<string, string>>({})
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const fetchGuides = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { page_size: '100' }
      if (category) params.category = category
      // Sanitize search keyword to prevent XSS
      const sanitizedKeyword = sanitizeSearchInput(keyword)
      if (sanitizedKeyword) params.keyword = sanitizedKeyword

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
    <div className={`space-y-6 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-2">
        <div 
          className="w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ 
            background: `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
            boxShadow: `0 0 20px ${colors.CYBER_CYAN}40`
          }}
        >
          <ClipboardList size={24} className="text-black" />
        </div>
        <div>
          <GradientText
            as="h1"
            className="text-3xl font-bold mb-1"
            style={{ 
              background: isLight 
                ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
                : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '-0.02em'
            }}
          >
            作业指引
          </GradientText>
          <p className="text-sm" style={{ color: isLight ? '#64748b' : '#6b7280' }}>标准化作业流程，规范化设备检修</p>
        </div>
      </div>
      
      {/* Accent Line */}
      <div 
        className="w-full h-px"
        style={{ background: `linear-gradient(90deg, transparent 0%, ${colors.CYBER_CYAN}50 50%, transparent 100%)` }}
      />

      <Tabs defaultValue="chat" className="w-full">
        <TabsList 
          className="h-12 p-1 mb-4 rounded-xl"
          style={{ 
            background: isLight ? '#f1f5f9' : 'rgba(15, 15, 35, 0.8)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
          }}
        >
          <TabsTrigger 
            value="chat" 
            className="h-10 px-6 text-sm font-medium rounded-lg transition-all duration-300 data-[state=active]:text-black dark:data-[state=active]:text-black"
            style={{ 
              background: 'transparent',
              color: isLight ? '#64748b' : '#6b7280',
            }}
          >
            <Sparkles size={16} className="mr-2" />
            智能问答
          </TabsTrigger>
          <TabsTrigger 
            value="regulations" 
            className="h-10 px-6 text-sm font-medium rounded-lg transition-all duration-300 data-[state=active]:text-black dark:data-[state=active]:text-black"
            style={{ 
              background: 'transparent',
              color: isLight ? '#64748b' : '#6b7280'
            }}
          >
            <FileText size={16} className="mr-2" />
            作业规程
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="h-[calc(100vh-300px)]">
          <div 
            className="glass-card h-full p-6"
            style={{ 
              background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
              boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
            }}
          >
            <div 
              className="flex items-center gap-3 mb-4 pb-4"
              style={{ borderBottom: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` }}
            >
              <div 
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ 
                  background: isLight 
                    ? `${colors.CYBER_BLUE}15` 
                    : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
                  boxShadow: isLight ? `0 0 15px ${colors.CYBER_BLUE}20` : `0 0 15px ${colors.CYBER_CYAN}30`,
                  color: isLight ? colors.CYBER_BLUE : '#000'
                }}
              >
                <Wrench size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold" style={{ color: isLight ? '#1e293b' : '#e8e8f0' }}>作业指引问答</h3>
                <p className="text-xs" style={{ color: isLight ? '#64748b' : '#6b7280' }}>AI 智能解答您的检修问题</p>
              </div>
            </div>
            <Suspense fallback={<ComponentLoader />}>
              <ChatPanel
                sessionKey="guide_chat"
                title="作业指引问答"
                searchMode="hybrid"
                topK={5}
              />
            </Suspense>
          </div>
        </TabsContent>

        <TabsContent value="regulations">
          <div 
            className="glass-card p-6"
            style={{ 
              background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)', 
              border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
              boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
            }}
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ 
                    background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15`, 
                    color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN 
                  }}
                >
                  <BookOpen size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold" style={{ color: isLight ? '#1e293b' : '#e8e8f0' }}>作业规程库</h3>
                  <p className="text-xs" style={{ color: isLight ? '#64748b' : '#6b7280' }}>浏览和搜索标准化检修规程</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 mb-6">
              <div className="w-48">
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger 
                    className="h-11 rounded-xl"
                    style={{ 
                      background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)',
                      border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`,
                      color: isLight ? '#1e293b' : '#e8e8f0'
                    }}
                  >
                    <SelectValue placeholder="选择分类" />
                  </SelectTrigger>
                  <SelectContent 
                    className="rounded-xl"
                    style={{ background: isLight ? 'rgba(255, 255, 255, 0.98)' : 'rgba(10, 10, 25, 0.98)', border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` }}
                  >
                    {CATEGORIES.map((cat) => (
                      <SelectItem 
                        key={cat} 
                        value={cat}
                        style={{ 
                          color: isLight ? '#1e293b' : '#e8e8f0',
                          background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)'
                        }}
                      >
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 relative group">
                <div 
                  className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-10"
                  style={{ color: isLight ? '#94a3b8' : '#505080' }}
                >
                  <Search size={18} />
                </div>
                <Input
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="搜索作业规程..."
                  className="h-11 pl-12 pr-4 rounded-xl text-base"
                  style={{ 
                    background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)',
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`,
                    color: isLight ? '#1e293b' : '#e8e8f0'
                  }}
                />
              </div>
              <Button 
                onClick={handleSearch} 
                disabled={loading}
                className="h-11 px-6 rounded-xl font-semibold"
                style={{ 
                  background: isLight 
                    ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, #1d4ed8 100%)`
                    : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
                  color: '#ffffff',
                  boxShadow: isLight ? `0 4px 20px ${colors.CYBER_BLUE}30` : `0 4px 20px ${colors.CYBER_CYAN}30`
                }}
              >
                <Zap size={16} />
                搜索
              </Button>
            </div>

            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div 
                    key={i} 
                    className="p-4 rounded-xl animate-pulse"
                    style={{ 
                      background: isLight ? '#f1f5f9' : `${colors.CYBER_CYAN}10`, 
                      border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '10'}` 
                    }}
                  >
                    <div className="h-5 w-48 rounded mb-2" style={{ background: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}20` }} />
                    <div className="h-4 w-full rounded" style={{ background: isLight ? '#f1f5f9' : `${colors.CYBER_CYAN}10` }} />
                  </div>
                ))}
              </div>
            ) : guides.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div 
                  className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                  style={{ 
                    background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15`, 
                    color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN 
                  }}
                >
                  <FileText size={32} />
                </div>
                <p className="text-lg font-medium" style={{ color: isLight ? '#1e293b' : '#e8e8f0' }}>暂无作业规程</p>
                <p className="text-sm mt-1" style={{ color: isLight ? '#64748b' : '#6b7280' }}>请尝试更换分类或关键词</p>
              </div>
            ) : (
              <div className="space-y-3">
                {guides.map((guide, index) => (
                  <div 
                    key={guide.id} 
                    className="rounded-xl transition-all duration-300 overflow-hidden"
                    style={{ 
                      background: isLight ? '#ffffff' : 'rgba(15, 15, 35, 0.6)',
                      border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
                      boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.06)' : 'none',
                      animationDelay: `${index * 0.05}s`
                    }}
                  >
                    <div 
                      className="cursor-pointer p-5 flex items-center justify-between"
                      onClick={() => toggleExpand(guide.id)}
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div 
                          className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                          style={{ 
                            background: isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}15`, 
                            color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN 
                          }}
                        >
                          <FileText size={24} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <CardTitle className="text-base" style={{ color: isLight ? '#1e293b' : '#e8e8f0' }}>{guide.title}</CardTitle>
                            <Badge 
                              variant="secondary" 
                              className="px-2 py-0.5 text-xs"
                              style={{ 
                                background: isLight ? `${colors.CYBER_PURPLE}15` : `${colors.CYBER_PURPLE}20`, 
                                color: isLight ? colors.CYBER_PURPLE : colors.CYBER_PURPLE 
                              }}
                            >
                              {guide.category}
                            </Badge>
                            <Badge 
                              variant="secondary" 
                              className="px-2 py-0.5 text-xs"
                              style={{ 
                                background: isLight ? `${colors.CYBER_GREEN}15` : `${colors.CYBER_GREEN}20`, 
                                color: isLight ? colors.CYBER_GREEN : colors.CYBER_GREEN 
                              }}
                            >
                              {guide.chunk_count} 个分块
                            </Badge>
                          </div>
                          <p className="text-sm" style={{ color: isLight ? '#64748b' : '#6b7280' }}>{guide.content}</p>
                        </div>
                      </div>
                      <div 
                        className="ml-4 p-2 rounded-lg transition-all duration-300"
                        style={{ 
                          background: expandedId === guide.id 
                            ? (isLight ? `${colors.CYBER_BLUE}15` : `${colors.CYBER_CYAN}20`)
                            : 'transparent',
                          color: expandedId === guide.id 
                            ? (isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN)
                            : (isLight ? '#94a3b8' : '#505080')
                        }}
                      >
                        {expandedId === guide.id ? (
                          <ChevronUp size={20} />
                        ) : (
                          <ChevronDown size={20} />
                        )}
                      </div>
                    </div>
                    {expandedId === guide.id && (
                      <div 
                        className="px-5 pb-5 pt-4"
                        style={{ borderTop: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '10'}` }}
                      >
                        <div 
                          className="whitespace-pre-wrap p-4 rounded-xl"
                          style={{ 
                            background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.5)',
                            color: isLight ? '#1e293b' : '#e8e8f0'
                          }}
                        >
                          {previewContent[guide.id] || (
                            <div className="flex items-center justify-center py-4">
                              <div className="flex items-center gap-2" style={{ color: isLight ? '#64748b' : '#6b7280' }}>
                                <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN, animationDelay: '0s' }} />
                                <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN, animationDelay: '0.2s' }} />
                                <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN, animationDelay: '0.4s' }} />
                                <span className="ml-2">加载中...</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}