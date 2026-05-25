import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useChatStore } from '@/stores/chat-store'
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

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleNewChat}>
            新建对话
          </Button>
          <Button variant="ghost" size="sm" onClick={handleClear}>
            清空
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p>请输入您的问题，开始对话</p>
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
            <div className="flex justify-start">
              <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2.5 text-gray-500">
                <span className="mr-1.5">🤖</span>
                正在思考中...
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题..."
            disabled={loading}
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
