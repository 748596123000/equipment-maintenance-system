import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, FileText, BookOpen, MessageSquare, Network, X, Loader2, Command, Clock, Trash2, Sparkles } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'

interface SearchResult {
  id: string
  type: 'document' | 'knowledge' | 'case' | 'guide'
  title: string
  summary: string
  url: string
  score?: number
}

interface SearchHistoryItem {
  id: string
  query: string
  timestamp: number
}

interface GlobalSearchProps {
  onClose: () => void
}

const SUGGESTIONS = [
  '发动机维修',
  '液压系统',
  '电气故障',
  '轴承更换',
  '机油更换',
  '设备保养',
  '故障诊断',
  '安全检查',
  '电路接线',
  '机械调整',
]

export function GlobalSearch({ onClose }: GlobalSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([])
  const [showHistory, setShowHistory] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const { theme } = useTheme()
  const isLight = theme === 'light'

  // Define functions before useEffect
  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) return
    
    setLoading(true)
    try {
      const res = await fetch(`/api/v1/search/global?q=${encodeURIComponent(searchQuery)}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (res.ok) {
        const data = await res.json()
        setResults(data.results || [])
      } else {
        setResults(generateLocalResults(searchQuery))
      }
    } catch (error) {
      console.error('搜索失败:', error)
      setResults(generateLocalResults(searchQuery))
    } finally {
      setLoading(false)
    }
  }, [])

  const saveSearch = useCallback((searchQuery: string) => {
    if (searchQuery.trim().length < 2) return

    const newHistoryItem: SearchHistoryItem = {
      id: Date.now().toString(),
      query: searchQuery,
      timestamp: Date.now(),
    }

    const updatedHistory = [
      newHistoryItem,
      ...searchHistory.filter(h => h.query.toLowerCase() !== searchQuery.toLowerCase()),
    ].slice(0, 10)

    setSearchHistory(updatedHistory)
    localStorage.setItem('search_history', JSON.stringify(updatedHistory))
  }, [searchHistory])

  // Initialize search history and focus
  useEffect(() => {
    const savedHistory = localStorage.getItem('search_history')
    if (savedHistory) {
      setSearchHistory(JSON.parse(savedHistory))
    }
    inputRef.current?.focus()
  }, [])

  // Handle search query
  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([])
      setShowHistory(true)
      return
    }

    setShowHistory(false)
    const timer = setTimeout(() => {
      performSearch(query)
      saveSearch(query)
    }, 300)

    return () => clearTimeout(timer)
  }, [query, performSearch, saveSearch])

  const clearHistory = () => {
    setSearchHistory([])
    localStorage.removeItem('search_history')
  }

  const removeHistoryItem = (id: string) => {
    const updated = searchHistory.filter(h => h.id !== id)
    setSearchHistory(updated)
    localStorage.setItem('search_history', JSON.stringify(updated))
  }

  const generateLocalResults = (q: string): SearchResult[] => {
    const allItems: SearchResult[] = [
      { id: '1', type: 'document', title: '发动机维修手册', summary: '详细的发动机维修步骤和注意事项...', url: '/kb' },
      { id: '2', type: 'knowledge', title: '液压系统维护指南', summary: '液压系统日常维护和故障排除...', url: '/knowledge' },
      { id: '3', type: 'case', title: '柴油机无法启动案例', summary: '某型号柴油机无法启动的维修案例...', url: '/cases' },
      { id: '4', type: 'guide', title: '更换机油标准流程', summary: '标准化机油更换作业指引...', url: '/guide' },
      { id: '5', type: 'document', title: '电气系统接线图', summary: '设备电气系统接线原理图...', url: '/kb' },
      { id: '6', type: 'knowledge', title: '轴承更换教程', summary: '轴承拆卸和安装的详细步骤...', url: '/knowledge' },
    ]
    
    const lowerQ = q.toLowerCase()
    return allItems.filter(item => 
      item.title.toLowerCase().includes(lowerQ) || 
      item.summary.toLowerCase().includes(lowerQ)
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => {
          const items = showHistory && searchHistory.length > 0 ? searchHistory : results
          return Math.min(prev + 1, items.length - 1)
        })
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (showHistory && searchHistory[selectedIndex]) {
          setQuery(searchHistory[selectedIndex].query)
        } else if (results[selectedIndex]) {
          navigateToResult(results[selectedIndex])
        }
        break
      case 'Escape':
        onClose()
        break
    }
  }

  const navigateToResult = (result: SearchResult) => {
    navigate(result.url)
    onClose()
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'document':
        return <FileText className="w-4 h-4" />
      case 'knowledge':
        return <BookOpen className="w-4 h-4" />
      case 'case':
        return <MessageSquare className="w-4 h-4" />
      case 'guide':
        return <Network className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'document':
        return 'text-blue-400 bg-blue-400/10'
      case 'knowledge':
        return 'text-green-400 bg-green-400/10'
      case 'case':
        return 'text-yellow-400 bg-yellow-400/10'
      case 'guide':
        return 'text-purple-400 bg-purple-400/10'
      default:
        return 'text-gray-400 bg-gray-400/10'
    }
  }

  const getTypeName = (type: string) => {
    switch (type) {
      case 'document': return '文档'
      case 'knowledge': return '知识'
      case 'case': return '案例'
      case 'guide': return '指引'
      default: return '其他'
    }
  }

  const formatHistoryTime = (timestamp: number) => {
    const diff = Date.now() - timestamp
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return `${days}天前`
  }

  const filteredSuggestions = SUGGESTIONS.filter(s => 
    s.toLowerCase().includes(query.toLowerCase())
  )

  const fuzzyMatch = (text: string, pattern: string): { score: number; matches: number[] } => {
    const lowerText = text.toLowerCase()
    const lowerPattern = pattern.toLowerCase()
    const matches: number[] = []
    let score = 0
    let patternIdx = 0
    
    for (let i = 0; i < lowerText.length && patternIdx < lowerPattern.length; i++) {
      if (lowerText[i] === lowerPattern[patternIdx]) {
        matches.push(i)
        score += 10
        if (i === 0 || lowerText[i - 1] === ' ' || lowerText[i - 1] === '_') {
          score += 15
        }
        patternIdx++
      }
    }
    
    if (patternIdx < lowerPattern.length) {
      return { score: 0, matches: [] }
    }
    
    const consecutiveBonus = calculateConsecutiveBonus(matches)
    score += consecutiveBonus
    
    return { score, matches }
  }

  const calculateConsecutiveBonus = (matches: number[]): number => {
    if (matches.length < 2) return 0
    let bonus = 0
    let streak = 1
    for (let i = 1; i < matches.length; i++) {
      if (matches[i] === matches[i - 1] + 1) {
        streak++
        bonus += streak * 5
      } else {
        streak = 1
      }
    }
    return bonus
  }

  const getSmartSuggestions = (): string[] => {
    if (query.length < 1) return []
    
    const scored = SUGGESTIONS.map(suggestion => ({
      text: suggestion,
      ...fuzzyMatch(suggestion, query)
    }))
    
    return scored
      .filter(s => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8)
      .map(s => s.text)
  }

  const smartSuggestions = getSmartSuggestions()

  return (
    <div className="w-[640px] rounded-2xl shadow-2xl shadow-black/50 overflow-hidden" style={{
      background: isLight ? '#ffffff' : '#1a1a2e',
      border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.3)'
    }}>
      {/* Search Input */}
      <div className="flex items-center gap-3 px-4 py-4" style={{
        borderBottom: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.2)'
      }}>
        <Search className="w-5 h-5" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="搜索文档、知识、案例、指引..."
          className="flex-1 bg-transparent outline-none text-base"
          style={{
            color: isLight ? '#1e293b' : '#e8e8e8',
            '--placeholder-color': isLight ? '#94a3b8' : '#606080'
          } as React.CSSProperties}
        />
        {loading && <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />}
        {query && !loading && (
          <button
            onClick={() => setQuery('')}
            className="p-1 rounded-lg transition-colors"
            style={{ background: isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.1)' }}
          >
            <X className="w-4 h-4" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
          </button>
        )}
        <div className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{
          background: isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.1)'
        }}>
          <Command className="w-3 h-3" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
          <span className="text-xs" style={{ color: isLight ? '#94a3b8' : '#606080' }}>K</span>
        </div>
      </div>

      {/* Search Results */}
      <div className="max-h-[400px] overflow-y-auto scrollbar-luxury">
        {/* Search History */}
        {!query && searchHistory.length > 0 && showHistory && (
          <div className="py-2">
            <div className="flex items-center justify-between px-4 py-2">
              <span className="text-xs uppercase tracking-wider" style={{ color: isLight ? '#64748b' : '#606080' }}>搜索历史</span>
              <button
                onClick={clearHistory}
                className="text-xs transition-colors flex items-center gap-1"
                style={{ color: isLight ? '#64748b' : '#606080' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = isLight ? '#2563eb' : '#3b82f6' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = isLight ? '#64748b' : '#606080' }}
              >
                <Trash2 className="w-3 h-3" />
                清除
              </button>
            </div>
            {searchHistory.map((item, index) => (
              <div
                key={item.id}
                onClick={() => setQuery(item.query)}
                className="mx-2 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200 group"
                style={{
                  background: index === selectedIndex
                    ? (isLight ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.15)')
                    : 'transparent'
                }}
                onMouseEnter={(e) => { if (index !== selectedIndex) e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)' }}
                onMouseLeave={(e) => { if (index !== selectedIndex) e.currentTarget.style.background = 'transparent' }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Clock className="w-4 h-4" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
                    <span className="text-sm" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>{item.query}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: isLight ? '#94a3b8' : '#606080' }}>{formatHistoryTime(item.timestamp)}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        removeHistoryItem(item.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-all"
                      style={{ color: isLight ? '#94a3b8' : '#606080' }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = '#ef4444' }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = isLight ? '#94a3b8' : '#606080' }}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Suggestions */}
        {!query && searchHistory.length === 0 && (
          <div className="py-2">
            <div className="px-4 py-2 text-xs uppercase tracking-wider flex items-center gap-2" style={{ color: isLight ? '#64748b' : '#606080' }}>
              <Sparkles className="w-3 h-3" style={{ color: isLight ? '#2563eb' : '#3b82f6' }} />
              热门搜索
            </div>
            <div className="px-2 grid grid-cols-2 gap-2">
              {SUGGESTIONS.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => setQuery(suggestion)}
                  className="px-3 py-2 text-left text-sm rounded-lg transition-all"
                  style={{ color: isLight ? '#64748b' : '#8080a0' }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.color = isLight ? '#2563eb' : '#3b82f6'
                    ;(e.currentTarget as HTMLElement).style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)'
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.color = isLight ? '#64748b' : '#8080a0'
                    ;(e.currentTarget as HTMLElement).style.background = 'transparent'
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Auto Complete */}
        {query && query.length >= 2 && filteredSuggestions.length > 0 && results.length === 0 && (
          <div className="py-2">
            <div className="px-4 py-2 text-xs uppercase tracking-wider" style={{ color: isLight ? '#64748b' : '#606080' }}>
              搜索建议
            </div>
            {filteredSuggestions.map((suggestion, index) => (
              <div
                key={index}
                onClick={() => setQuery(suggestion)}
                className="mx-2 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200"
                style={{
                  background: index === selectedIndex ? (isLight ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.15)') : 'transparent'
                }}
                onMouseEnter={(e) => { if (index !== selectedIndex) e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)' }}
                onMouseLeave={(e) => { if (index !== selectedIndex) e.currentTarget.style.background = 'transparent' }}
              >
                <div className="flex items-center gap-3">
                  <Search className="w-4 h-4" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
                  <span className="text-sm" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>{suggestion}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {query && query.length < 2 && (
          <div className="px-4 py-8 text-center" style={{ color: isLight ? '#64748b' : '#606080' }}>
            <p className="text-sm">请输入至少2个字符</p>
          </div>
        )}

        {query && query.length >= 2 && results.length === 0 && !loading && (
          <div className="px-4 py-8 text-center" style={{ color: isLight ? '#64748b' : '#606080' }}>
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">未找到相关结果</p>
            <p className="text-xs mt-1">尝试使用不同的关键词</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="py-2">
            <div className="px-4 py-2 text-xs uppercase tracking-wider" style={{ color: isLight ? '#64748b' : '#606080' }}>
              找到 {results.length} 个结果
            </div>
            {results.map((result, index) => (
              <div
                key={result.id}
                onClick={() => navigateToResult(result)}
                className="mx-2 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200"
                style={{
                  background: index === selectedIndex ? (isLight ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.15)') : 'transparent'
                }}
                onMouseEnter={(e) => { if (index !== selectedIndex) e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)' }}
                onMouseLeave={(e) => { if (index !== selectedIndex) e.currentTarget.style.background = 'transparent' }}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${getTypeColor(result.type)}`}>
                    {getTypeIcon(result.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-medium truncate" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>
                        {result.title}
                      </h4>
                      <span className={`flex-shrink-0 px-2 py-0.5 text-xs rounded-full ${getTypeColor(result.type)}`}>
                        {getTypeName(result.type)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs line-clamp-2" style={{ color: isLight ? '#64748b' : '#606080' }}>
                      {result.summary}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!query && searchHistory.length === 0 && (
          <div className="px-4 py-8 text-center" style={{ color: isLight ? '#64748b' : '#606080' }}>
            <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">输入关键词开始搜索</p>
            <p className="text-xs mt-1">支持搜索文档、知识、案例、指引等内容</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3" style={{
        borderTop: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.2)',
        background: isLight ? '#f8fafc' : 'rgba(59,130,246,0.02)'
      }}>
        <div className="flex items-center justify-between text-xs" style={{ color: isLight ? '#64748b' : '#606080' }}>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <span className="px-1.5 py-0.5 rounded" style={{ background: isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.1)', color: isLight ? '#2563eb' : '#3b82f6' }}>↑</span>
              <span className="px-1.5 py-0.5 rounded" style={{ background: isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.1)', color: isLight ? '#2563eb' : '#3b82f6' }}>↓</span>
              导航
            </span>
            <span className="flex items-center gap-1">
              <span className="px-1.5 py-0.5 rounded" style={{ background: isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.1)', color: isLight ? '#2563eb' : '#3b82f6' }}>Enter</span>
              选择
            </span>
            <span className="flex items-center gap-1">
              <span className="px-1.5 py-0.5 rounded" style={{ background: isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.1)', color: isLight ? '#2563eb' : '#3b82f6' }}>Esc</span>
              关闭
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
