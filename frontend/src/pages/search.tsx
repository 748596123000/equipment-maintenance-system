import { useState, useRef, useCallback, lazy, Suspense } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/css-tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from '@/components/chat/message-bubble'
import { SourceCard } from '@/components/chat/source-card'
import { api } from '@/lib/api'
import { sanitizeSearchInput } from '@/lib/validate'
import { Upload, X, Send, Sparkles, Image, FileSearch, Zap } from 'lucide-react'
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

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

// Re-export COLORS for component-level customization if needed
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _LOCAL_COLORS = COLORS

interface ImageChatMessage {
  role: 'user' | 'assistant'
  content: string
  imageUrl?: string
  sources?: Array<{ title: string; content: string; score?: number }>
}

export default function SearchPage() {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  
  // Get theme-specific colors
  const colors = isLight ? COLORS.light : COLORS.dark
  
  // Aliases for backward compatibility
  const textPrimary = colors.textPrimary
  const textSecondary = colors.textSecondary
  const cardBg = colors.cardBg
  // borderColor intentionally kept for future use
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _borderColor = colors.borderColor
  const accentColor = colors.accentColor
  const inputBg = colors.inputBg
  
  const [image, setImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ImageChatMessage[]>([])
  const [isDragging, setIsDragging] = useState(false)
  // Mounted state is now handled synchronously
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [showSuggestions, _setShowSuggestions] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Common suggestions array - kept for future use
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const commonSuggestions = [
    '变压器维修', '断路器故障', '开关柜检修', '电机维护',
    '电缆检测', '接地系统', '保护装置', '预防性试验',
  ]

  // Remove unused handlers or prefix with underscore
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _handleInputFocus = () => _setShowSuggestions(true)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _handleInputBlur = () => setTimeout(() => _setShowSuggestions(false), 200)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _selectSuggestion = (suggestion: string) => {
    setQuestion(suggestion)
    _setShowSuggestions(false)
  }

  // Initialize mounted state synchronously (no effect needed)
  const isMounted = true // Replace setMounted with direct boolean

  const handleImageSelect = useCallback((file: File) => {
    if (file.size > 5 * 1024 * 1024) {
      alert('图片过大，请选择 5MB 以内的图片')
      return
    }
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
    if (!allowedTypes.includes(file.type)) {
      alert('不支持的图片格式，请使用 JPG/PNG/GIF/WebP/BMP')
      return
    }
    setImage(file)
    const reader = new FileReader()
    reader.onload = (e) => setImagePreview(e.target?.result as string)
    reader.readAsDataURL(file)
  }, [])

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length > 0) {
      handleImageSelect(e.dataTransfer.files[0])
    }
  }, [handleImageSelect])

  const handleFileInput = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleImageSelect(e.target.files[0])
      e.target.value = ''
    }
  }, [handleImageSelect])

  const clearImage = useCallback(() => {
    setImage(null)
    setImagePreview(null)
  }, [])

  const handleSend = async () => {
    if (!image || loading) return
    // Sanitize user input to prevent XSS
    const sanitizedQuestion = sanitizeSearchInput(question)
    const q = sanitizedQuestion || '请根据图片内容进行检索'
    setLoading(true)
    setMessages((prev) => [...prev, { role: 'user', content: q, imageUrl: imagePreview || undefined }])

    try {
      const base64 = await new Promise<string>((resolve) => {
        const reader = new FileReader()
        reader.onload = () => {
          const result = reader.result as string
          resolve(result.split(',')[1] || result)
        }
        reader.readAsDataURL(image)
      })

      const response = await api.post('/search/image', { image_base64: base64, top_k: 5 })
      const results = response.data.results || []
      const answerText = results.length > 0
        ? `找到 ${results.length} 个相关结果：\n${results.map((r: { content: string; source: string; score: number }, i: number) => `${i + 1}. ${r.content}（来源: ${r.source}，相似度: ${r.score}）`).join('\n')}`
        : '未找到相关结果'

      const sources = results.map((r: { content: string; source: string; score: number }) => ({
        title: r.source, content: r.content, score: r.score,
      }))

      setMessages((prev) => [...prev, { role: 'assistant', content: answerText, sources }])
    } catch (error: any) {
      const status = error?.response?.status
      const detail = error?.response?.data?.detail || ''
      let msg = '抱歉，图片检索失败'
      if (status === 503) msg = '视觉服务暂时繁忙，请稍后重试'
      else if (status === 502) msg = '无法连接到视觉服务，请检查网络或API配置'
      else if (status === 400) msg = detail || '图片格式无效，请上传 JPG/PNG/GIF/WebP/BMP 格式的图片'
      else if (detail) msg = `检索失败: ${detail}`
      setMessages((prev) => [...prev, { role: 'assistant', content: msg }])
    } finally {
      setLoading(false)
      setQuestion('')
      clearImage()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className={`space-y-6 transition-all duration-700 ${isMounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* Header - Theme-aware */}
      <div className="flex items-center gap-4 mb-2">
        <div 
          className="w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ 
            background: isLight 
              ? `${colors.CYBER_BLUE}10` 
              : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
            border: `1px solid ${isLight ? colors.CYBER_BLUE + '20' : 'transparent'}`,
            boxShadow: isLight ? '0 4px 16px rgba(37, 99, 235, 0.15)' : `0 0 20px ${colors.CYBER_CYAN}40`
          }}
        >
          <FileSearch size={24} style={{ color: isLight ? colors.CYBER_BLUE : '#000' }} />
        </div>
        <div>
          <GradientText as="h1"
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
            知识检索
          </GradientText>
          <p className="text-sm" style={{ color: textSecondary }}>多模态智能检索，精准定位设备检修知识</p>
        </div>
      </div>

      {/* Accent Line - Theme-aware */}
      <div className="w-full h-px" style={{ background: `linear-gradient(90deg, transparent 0%, ${accentColor}50 50%, transparent 100%)` }} />

      <Tabs defaultValue="text" className="w-full">
        <TabsList className="h-10 p-1 mb-2 rounded-xl" style={{
          background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.8)',
          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`
        }}>
          <TabsTrigger value="text" className="h-8 px-6 text-sm font-medium rounded-lg transition-all duration-300 data-[state=active]:bg-white data-[state=active]:text-black dark:data-[state=active]:text-black">
            <Zap size={16} className="mr-2" />
            文本检索
          </TabsTrigger>
          <TabsTrigger value="image" className="h-8 px-6 text-sm font-medium rounded-lg transition-all duration-300 data-[state=active]:bg-white data-[state=active]:text-black dark:data-[state=active]:text-black">
            <Image size={16} className="mr-2" />
            图片检索
          </TabsTrigger>
        </TabsList>

        <TabsContent value="text" className="h-[calc(100vh-140px)]">
          <div className="glass-card h-full p-2" style={{
            background: isLight ? 'rgba(10, 10, 25, 0.95)' : cardBg,
            border: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.15)' : colors.CYBER_CYAN + '15'}`
          }}>
            <Suspense fallback={<ComponentLoader />}>
            <ChatPanel sessionKey="search_text" title="知识检索" searchMode="hybrid" topK={5} forceDarkContent={isLight} />
          </Suspense>
          </div>
        </TabsContent>

        <TabsContent value="image" className="h-[calc(100vh-140px)]">
          <div className="glass-card h-full flex flex-col overflow-hidden" style={{ 
            background: isLight ? 'rgba(10, 10, 25, 0.95)' : cardBg, 
            border: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.15)' : colors.CYBER_CYAN + '15'}` 
          }}>
            {/* Header - Theme-aware */}
            <div className="flex items-center justify-between p-4" style={{ borderBottom: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.15)' : colors.CYBER_CYAN + '15'}` }}>
              <div className="flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ 
                    background: isLight 
                      ? `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`
                      : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
                    border: `1px solid ${isLight ? 'transparent' : 'transparent'}`,
                    boxShadow: isLight ? `0 0 15px ${colors.CYBER_CYAN}30` : `0 0 15px ${colors.CYBER_CYAN}30`
                  }}
                >
                  <Image size={20} style={{ color: '#000' }} />
                </div>
                <div>
                  <GradientText as="h2"
                    className="text-lg font-bold"
                    style={{ 
                      background: isLight
                        ? `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`
                        : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`,
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text'
                    }}
                  >
                    图片检索
                  </GradientText>
                  <p className="text-xs" style={{ color: isLight ? '#6b7280' : textSecondary }}>上传故障图片，AI 智能分析诊断</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setMessages([]); clearImage() }}
                style={{ color: isLight ? '#6b7280' : textSecondary }}
                onMouseEnter={(e) => { e.currentTarget.style.color = isLight ? '#00f0ff' : accentColor; e.currentTarget.style.background = `${isLight ? '#00f0ff' : accentColor}10` }}
                onMouseLeave={(e) => { e.currentTarget.style.color = isLight ? '#6b7280' : textSecondary; e.currentTarget.style.background = 'transparent' }}
              >
                <X size={16} className="mr-1" />
                清空
              </Button>
            </div>

            {/* Messages Area - Theme-aware */}
            <ScrollArea className="flex-1 px-4 py-2" ref={scrollRef}>
              {messages.length === 0 && !image && (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <div 
                      className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-4"
                      style={{ 
                        background: isLight ? `${colors.CYBER_CYAN}15` : `${colors.CYBER_CYAN}15`, 
                        boxShadow: isLight ? `0 0 30px ${colors.CYBER_CYAN}20` : `0 0 30px ${colors.CYBER_CYAN}20` 
                      }}
                    >
                      <Sparkles size={40} style={{ color: isLight ? '#00f0ff' : accentColor }} />
                    </div>
                    <p className="text-lg font-medium mb-2" style={{ color: isLight ? '#e8e8f0' : textPrimary }}>上传图片开始智能检索</p>
                    <p className="text-sm" style={{ color: isLight ? '#6b7280' : textSecondary }}>支持 JPG、PNG、BMP、GIF、WebP 格式</p>
                  </div>
                </div>
              )}
              <div className="space-y-4">
                {messages.map((msg, idx) => (
                  <div key={idx} className="animate-fade-in-up" style={{ animationDelay: `${idx * 0.1}s` }}>
                    <MessageBubble role={msg.role} content={msg.content} forceDark={isLight} />
                    {msg.role === 'user' && msg.imageUrl && (
                      <div className="flex justify-start mt-2">
                        <div className="relative group">
                          <img src={msg.imageUrl} alt="上传图片" className="max-h-56 rounded-xl object-cover" style={{ 
                            border: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.2)' : colors.CYBER_CYAN + '20'}`, 
                            boxShadow: isLight ? `0 8px 32px rgba(0,240,255,0.15)` : `0 8px 32px rgba(0,240,255,0.15)` 
                          }} />
                          <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity" style={{ background: `linear-gradient(to top, ${isLight ? '#00f0ff' : accentColor}20, transparent)` }} />
                        </div>
                      </div>
                    )}
                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="flex justify-start mt-2">
                        <div className="max-w-[80%]">
                          <SourceCard sources={msg.sources.map((s) => ({ source: s.title, content: s.content, score: s.score }))} forceDark={isLight} />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-5 py-3" style={{ 
                      background: isLight ? 'rgba(15, 15, 35, 0.8)' : 'rgba(15, 15, 35, 0.8)', 
                      border: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.15)' : colors.CYBER_CYAN + '15'}` 
                    }}>
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-8 h-8 rounded-lg flex items-center justify-center"
                          style={{ 
                            background: isLight ? `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)` : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)` 
                          }}
                        >
                          <Sparkles size={16} style={{ color: '#000' }} />
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: isLight ? '#00f0ff' : accentColor, animationDelay: '0s' }} />
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: isLight ? '#00f0ff' : accentColor, animationDelay: '0.2s' }} />
                          <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: isLight ? '#00f0ff' : accentColor, animationDelay: '0.4s' }} />
                        </div>
                        <span className="text-sm" style={{ color: isLight ? '#00f0ff' : accentColor }}>正在分析图片并检索...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Image Preview Bar - Theme-aware */}
            {image && imagePreview && (
              <div className="px-3 py-1.5" style={{ borderTop: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.15)' : colors.CYBER_CYAN + '15'}` }}>
                <div className="flex items-center gap-3">
                  <div className="relative group">
                    <img src={imagePreview} alt="预览" className="h-12 w-12 rounded-lg object-cover" style={{
                      border: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.3)' : accentColor + '30'}`,
                      boxShadow: isLight ? `0 4px 16px ${colors.CYBER_CYAN}20` : `0 4px 16px ${colors.CYBER_CYAN}20`
                    }} />
                    <button onClick={clearImage} className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full text-white transition-colors" style={{ background: '#dc2626', boxShadow: `0 2px 8px rgba(220,38,38,0.4)` }}>
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium" style={{ color: isLight ? '#e8e8f0' : textPrimary }}>{image.name}</p>
                    <p className="text-xs" style={{ color: isLight ? '#6b7280' : textSecondary }}>{(image.size / 1024).toFixed(1)} KB • 点击右侧按钮开始检索</p>
                  </div>
                </div>
              </div>
            )}

            {/* Upload / Input Area - Theme-aware */}
            <div className="p-2" style={{ borderTop: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.15)' : colors.CYBER_CYAN + '15'}` }}>
              {!image ? (
                <div
                  className="flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-xl p-6 transition-all duration-300"
                  style={{
                    border: `2px dashed ${isDragging ? (isLight ? '#00f0ff' : accentColor) : (isLight ? 'rgba(0, 240, 255, 0.25)' : accentColor + '40')}`,
                    background: isDragging ? `${isLight ? '#00f0ff' : accentColor}10` : (isLight ? 'rgba(15, 15, 35, 0.5)' : 'rgba(15, 15, 35, 0.5)')
                  }}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center mb-3"
                    style={{ background: isLight ? `${colors.CYBER_CYAN}15` : `${colors.CYBER_CYAN}15` }}
                  >
                    <Upload className="h-7 w-7" style={{ color: isLight ? '#00f0ff' : accentColor }} />
                  </div>
                  <p className="text-sm font-medium mb-1" style={{ color: isLight ? '#e8e8f0' : textPrimary }}>拖拽图片到此处，或点击选择图片</p>
                  <p className="text-xs" style={{ color: isLight ? '#6b7280' : textSecondary }}>支持 JPG、PNG、BMP、GIF、WebP 格式</p>
                  <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileInput} />
                </div>
              ) : (
                <div className="flex gap-3">
                  <div className="relative flex-1">
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-10" style={{ color: isLight ? '#6b7280' : textSecondary }}>
                      <Sparkles size={18} />
                    </div>
                    <Input
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="输入检索问题（可选）..."
                      disabled={loading}
                      className="h-12 pl-12 pr-4 rounded-xl text-base"
                      style={{ 
                        background: isLight ? 'rgba(10, 10, 25, 0.9)' : inputBg,
                        border: `1px solid ${isLight ? 'rgba(0, 240, 255, 0.3)' : colors.CYBER_CYAN + '20'}`,
                        color: isLight ? '#e8e8f0' : textPrimary
                      }}
                    />
                  </div>
                  <Button 
                    onClick={handleSend} 
                    disabled={loading}
                    className="h-12 px-6 rounded-xl font-semibold"
                    style={{ 
                      background: isLight 
                        ? `linear-gradient(135deg, #00f0ff 0%, ${colors.CYBER_BLUE} 100%)`
                        : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
                      color: '#fff',
                      boxShadow: isLight ? `0 4px 20px ${colors.CYBER_CYAN}30` : `0 4px 20px ${colors.CYBER_CYAN}30`
                    }}
                  >
                    <Send size={18} />
                    检索
                  </Button>
                </div>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}