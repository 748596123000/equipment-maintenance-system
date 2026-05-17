import { useState, useRef, useCallback } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChatPanel } from '@/components/chat/chat-panel'
import { MessageBubble } from '@/components/chat/message-bubble'
import { SourceCard } from '@/components/chat/source-card'
import { api } from '@/lib/api'
import { Upload, X, Send } from 'lucide-react'

interface ImageChatMessage {
  role: 'user' | 'assistant'
  content: string
  imageUrl?: string
  sources?: Array<{ title: string; content: string; score?: number }>
}

export default function SearchPage() {
  const [image, setImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ImageChatMessage[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const handleImageSelect = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) return
    setImage(file)
    const reader = new FileReader()
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string)
    }
    reader.readAsDataURL(file)
  }, [])

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
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

    const q = question.trim() || '请根据图片内容进行检索'
    setLoading(true)

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: q, imageUrl: imagePreview || undefined },
    ])

    try {
      const base64 = await new Promise<string>((resolve) => {
        const reader = new FileReader()
        reader.onload = () => {
          const result = reader.result as string
          const base64Data = result.split(',')[1] || result
          resolve(base64Data)
        }
        reader.readAsDataURL(image)
      })

      const response = await api.post('/search/image', {
        image_base64: base64,
        top_k: 5,
      })

      const results = response.data.results || []
      const answerText = results.length > 0
        ? `找到 ${results.length} 个相关结果：\n${results.map((r: { content: string; source: string; score: number }, i: number) => `${i + 1}. ${r.content}（来源: ${r.source}，相似度: ${r.score}）`).join('\n')}`
        : '未找到相关结果'

      const sources = results.map((r: { content: string; source: string; score: number }) => ({
        title: r.source,
        content: r.content,
        score: r.score,
      }))

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: answerText, sources },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '抱歉，图片检索失败，请稍后重试。' },
      ])
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
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">🔍 知识检索</h1>

      <Tabs defaultValue="text" className="w-full">
        <TabsList>
          <TabsTrigger value="text">文本检索</TabsTrigger>
          <TabsTrigger value="image">图片检索</TabsTrigger>
        </TabsList>

        <TabsContent value="text" className="h-[calc(100vh-220px)]">
          <ChatPanel
            sessionKey="search_text"
            title="知识检索"
            searchMode="hybrid"
            topK={5}
          />
        </TabsContent>

        <TabsContent value="image" className="h-[calc(100vh-220px)]">
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-lg font-semibold">图片检索</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setMessages([])
                  clearImage()
                }}
              >
                清空
              </Button>
            </div>

            <ScrollArea className="flex-1 p-4" ref={scrollRef}>
              {messages.length === 0 && !image && (
                <div className="flex h-full items-center justify-center text-muted-foreground">
                  <p>上传图片开始检索</p>
                </div>
              )}
              <div className="space-y-4">
                {messages.map((msg, idx) => (
                  <div key={idx}>
                    <MessageBubble role={msg.role} content={msg.content} />
                    {msg.role === 'user' && msg.imageUrl && (
                      <div className="flex justify-start mt-1">
                        <img
                          src={msg.imageUrl}
                          alt="上传图片"
                          className="max-h-48 rounded-lg border"
                        />
                      </div>
                    )}
                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="flex justify-start mt-1">
                        <div className="max-w-[75%]">
                          <SourceCard
                            sources={msg.sources.map((s) => ({
                              source: s.title,
                              content: s.content,
                              score: s.score,
                            }))}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2.5 text-gray-500">
                      <span className="mr-1.5">🤖</span>
                      正在分析图片并检索...
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {image && imagePreview && (
              <div className="border-t px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <img
                      src={imagePreview}
                      alt="预览"
                      className="h-16 w-16 rounded-lg border object-cover"
                    />
                    <button
                      onClick={clearImage}
                      className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-white"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="flex-1">
                    <p className="truncate text-sm font-medium">{image.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(image.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="border-t p-4">
              {!image ? (
                <div
                  className={`flex min-h-[120px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
                    isDragging
                      ? 'border-primary bg-primary/5'
                      : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
                  <p className="text-sm font-medium text-muted-foreground">
                    拖拽图片到此处，或点击选择图片
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground/70">
                    支持 JPG、PNG、BMP、GIF、WebP 格式
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleFileInput}
                  />
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入检索问题（可选）..."
                    disabled={loading}
                  />
                  <Button onClick={handleSend} disabled={loading}>
                    <Send className="mr-1 h-4 w-4" />
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
