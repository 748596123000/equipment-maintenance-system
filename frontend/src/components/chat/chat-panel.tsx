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
}

export function ChatPanel({ sessionKey, title = '智能问答', searchMode, topK }: ChatPanelProps) {
  const [input, setInput] = useState('')
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
    if (!question || loading) return

    setInput('')
    setLoading(true)
    try {
      await sendMessage(sessionKey, question, searchMode, topK)
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

  // Theme-aware styles
  const borderColor = isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)'
  const bgColor = isLight ? '#ffffff' : 'rgba(15, 15, 35, 0.5)'
  const textColor = isLight ? '#1e293b' : '#e8e8f0'
  const mutedColor = isLight ? '#94a3b8' : '#505080'
  const inputBg = isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)'
  const inputBorder = isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.3)'
  const accentColor = isLight ? '#2563eb' : '#00f0ff'
  const accentGlow = isLight ? 'rgba(37, 99, 235, 0.15)' : 'rgba(0, 240, 255, 0.15)'

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
              borderColor: isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.2)',
              color: isLight ? '#475569' : '#e8e8f0'
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
              <MessageBubble role={msg.role} content={msg.content} />
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
            <div className="flex justify-start animate-fade-in-up">
              <div 
                className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3"
                style={{ 
                  background: isLight ? '#f1f5f9' : 'rgba(15, 15, 35, 0.8)',
                  border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.15)',
                  boxShadow: isLight ? undefined : '0 0 15px rgba(0, 240, 255, 0.1)'
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

      <div className="border-t p-4" style={{ borderColor }}>
        <div className="flex gap-2">
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
              boxShadow: isLight ? undefined : '0 0 10px rgba(0, 240, 255, 0.1)'
            }}
          />
          <Button 
            onClick={handleSend} 
            disabled={loading || !input.trim()}
            className="btn-cyber"
            style={{
              background: accentColor,
              color: isLight ? '#ffffff' : '#000000',
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
