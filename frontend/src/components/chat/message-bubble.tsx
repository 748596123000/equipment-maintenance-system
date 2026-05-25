import { useTheme } from '@/hooks/useTheme'
import { sanitizeChatContent } from '@/lib/sanitize'

interface MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const { theme } = useTheme()
  const isLight = theme === 'light'

  // Sanitize content for XSS protection
  // User messages are treated as plain text (never HTML)
  // AI messages can contain limited HTML but are sanitized
  const safeContent = sanitizeChatContent(content, role === 'user')

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div 
          className="max-w-[75%] rounded-2xl rounded-br-sm px-4 py-2.5"
          style={{ 
            background: isLight ? '#2563eb' : '#00f0ff',
            color: isLight ? '#ffffff' : '#000000'
          }}
        >
          {safeContent}
        </div>
      </div>
    )
  }

  // AI assistant message - preserve line breaks and basic formatting
  return (
    <div className="flex justify-start">
      <div 
        className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-2.5"
        style={{ 
          background: isLight ? '#f1f5f9' : 'rgba(15, 15, 35, 0.8)',
          color: isLight ? '#1e293b' : '#e8e8f0'
        }}
      >
        <span className="mr-1.5">🤖</span>
        {/* Use dangerouslySetInnerHTML with sanitized content for AI messages */}
        {safeContent.includes('<') ? (
          <span dangerouslySetInnerHTML={{ __html: safeContent }} />
        ) : (
          <span style={{ whiteSpace: 'pre-wrap' }}>{safeContent}</span>
        )}
      </div>
    </div>
  )
}