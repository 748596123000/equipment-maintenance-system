import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useChatStore } from '@/stores/chat-store'
import { useTheme } from '@/hooks/useTheme'
import { MessageBubble } from './message-bubble'
import { SourceCard } from './source-card'

interface ChatPanelProps {
  sessionKey: string
  title?: string
  searchMode?: string
  topK?: number
  forceDarkContent?: boolean
}

export function ChatPanel({ sessionKey, title = '智能问答', searchMode, topK, forceDarkContent }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [pendingImage, setPendingImage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  
  const { theme } = useTheme()
  const isLight = theme === 'light'

  const sessions = useChatStore((s) => s.sessions)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const clearSession = useChatStore((s) => s.clearSession)

  const messages = sessions[sessionKey]?.messages || []

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if ((!question && !pendingImage) || loading) return

    setInput('')
    const imageData = pendingImage
    setPendingImage(null)
    setLoading(true)
    try {
      await sendMessage(sessionKey, question, searchMode, topK, imageData || undefined)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewChat = () => {
    clearSession(sessionKey)
    setInput('')
  }

  const handleClear = () => {
    clearSession(sessionKey)
  }

  const effectiveLight = forceDarkContent ? false : isLight

  const borderColor = effectiveLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)'
  const bgColor = effectiveLight ? '#ffffff' : 'rgba(15, 15, 35, 0.5)'
  const textColor = effectiveLight ? '#1e293b' : '#e8e8f0'
  const mutedColor = effectiveLight ? '#94a3b8' : '#505080'
  const inputBg = effectiveLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)'
  const inputBorder = effectiveLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.3)'
  const accentColor = effectiveLight ? '#2563eb' : '#00f0ff'
  const accentGlow = effectiveLight ? 'rgba(37, 99, 235, 0.15)' : 'rgba(0, 240, 255, 0.15)'

  return (
    <div className="flex h-full flex-col">
      <div 
        className="flex items-center justify-between border-b px-4 py-3"
        style={{ borderColor }}
      >
        <h2 className="text-lg font-semibold neon-text" style={{ color: accentColor }}>{title}</h2>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleNewChat}
            style={{ 
              borderColor: effectiveLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.2)',
              color: effectiveLight ? '#475569' : '#e8e8f0'
            }}
          >
            新建对话
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleClear}
            style={{ color: mutedColor }}
          >
            清空
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 && (
          <div 
            className="flex h-full items-center justify-center"
            style={{ color: mutedColor }}
          >
            <p className="text-center">
              <span className="text-2xl mb-2 block">🔍</span>
              <span className="text-sm">请输入您的问题，开始对话</span>
            </p>
          </div>
        )}
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx}>
              <MessageBubble role={msg.role} content={msg.content} forceDark={forceDarkContent} />
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="flex justify-start mt-1">
                  <div className="max-w-[75%]">
                    <SourceCard
                      sources={msg.sources.map((s) => ({
                        source: s.title,
                        content: s.content,
                        score: s.score,
                      }))}
                      forceDark={forceDarkContent}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex justify-start animate-fade-in-up">
              <div 
                className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3"
                style={{ 
                  background: effectiveLight ? '#f1f5f9' : 'rgba(15, 15, 35, 0.8)',
                  border: effectiveLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.15)',
                  boxShadow: effectiveLight ? undefined : '0 0 15px rgba(0, 240, 255, 0.1)'
                }}
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ 
                    background: accentColor,
                    animation: 'pulse-glow 1.5s ease-in-out infinite'
                  }} />
                  <span className="text-sm" style={{ color: mutedColor }}>正在思考中</span>
                  <span className="typewriter-cursor" style={{ color: accentColor }}>...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-3" style={{ borderColor }}>
        {pendingImage && (
          <div className="flex items-center gap-2 p-2 mb-2 rounded-lg" style={{ background: effectiveLight ? '#f1f5f9' : 'rgba(30,30,50,0.8)' }}>
            <img src={`data:image/png;base64,${pendingImage}`} alt="待发送图片" className="h-10 w-10 object-cover rounded" />
            <span className="text-xs text-muted-foreground">已选择图片</span>
            <button onClick={() => setPendingImage(null)} className="text-muted-foreground hover:text-foreground">
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (!file) return
              const reader = new FileReader()
              reader.onload = (ev) => {
                const result = ev.target?.result as string
                setPendingImage(result.split(',')[1])
              }
              reader.readAsDataURL(file)
              e.target.value = ''
            }}
          />
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 h-8 w-8"
            onClick={() => fileInputRef.current?.click()}
            title="上传图片"
          >
            <ImageIcon className="h-4 w-4" />
          </Button>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题..."
            disabled={loading}
            className="cyber-input"
            style={{ 
              background: inputBg,
              borderColor: inputBorder,
              color: textColor,
              boxShadow: effectiveLight ? undefined : '0 0 10px rgba(0, 240, 255, 0.1)'
            }}
          />
          <Button
            onClick={handleSend}
            disabled={loading || (!input.trim() && !pendingImage)}
            className="btn-cyber"
            style={{
              background: accentColor,
              color: effectiveLight ? '#ffffff' : '#000000',
              boxShadow: `0 0 15px ${accentGlow}`
            }}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
