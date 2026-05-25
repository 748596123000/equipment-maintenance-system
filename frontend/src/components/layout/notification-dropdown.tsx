import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'
import { sanitizeText } from '@/lib/sanitize'
import { useAuthStore } from '@/stores/auth-store'
import { useTheme } from '@/hooks/useTheme'
import {
  Bell,
  Check,
  Upload,
  AlertCircle,
  Clock,
  Shield,
  MessageSquare,
  ChevronRight,
  X,
  FileText,
  Volume2,
  VolumeX,
  Monitor,
  Settings
} from 'lucide-react'

interface Notification {
  id: string
  type: string
  title: string
  content: string
  priority: string
  is_read: boolean
  created_at: string
  related_id: string | null
  related_type: string | null
  sender_name: string | null
}

export function NotificationDropdown() {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)
  const [isOpen, setIsOpen] = useState(false)
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [desktopEnabled, setDesktopEnabled] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>('default')
  const user = useAuthStore((s) => s.user)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const prevUnreadCountRef = useRef(0)

  useEffect(() => {
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission)
    }
    loadSettings()
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchNotifications()
    }
  }, [isOpen, user])

  useEffect(() => {
    if (prevUnreadCountRef.current === 0 && unreadCount > 0) {
      if (soundEnabled) {
        playNotificationSound()
      }
      if (desktopEnabled && notifications.length > 0) {
        showDesktopNotification(notifications[0])
      }
    }
    prevUnreadCountRef.current = unreadCount
  }, [unreadCount, notifications])

  const loadSettings = () => {
    const savedSound = localStorage.getItem('notificationSound')
    const savedDesktop = localStorage.getItem('notificationDesktop')
    if (savedSound !== null) setSoundEnabled(savedSound === 'true')
    if (savedDesktop !== null) setDesktopEnabled(savedDesktop === 'true')
  }

  const saveSettings = () => {
    localStorage.setItem('notificationSound', soundEnabled.toString())
    localStorage.setItem('notificationDesktop', desktopEnabled.toString())
  }

  const playNotificationSound = () => {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)
    
    oscillator.frequency.value = 800
    oscillator.type = 'sine'
    gainNode.gain.value = 0.3
    
    oscillator.start()
    
    setTimeout(() => {
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
      setTimeout(() => oscillator.stop(), 300)
    }, 100)
  }

  const requestDesktopPermission = async () => {
    if (!('Notification' in window)) {
      alert('您的浏览器不支持桌面通知')
      return
    }
    
    const permission = await Notification.requestPermission()
    setNotificationPermission(permission)
    if (permission === 'granted') {
      setDesktopEnabled(true)
      saveSettings()
      new Notification('设备检修知识系统', {
        body: '桌面通知已启用！',
        icon: '🔔'
      })
    }
  }

  const showDesktopNotification = (notification: Notification) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.content,
        icon: getNotificationIconEmoji(notification.type),
        tag: notification.id
      })
    }
  }

  const getNotificationIconEmoji = (type: string) => {
    switch (type) {
      case 'upload_pending': return '📤'
      case 'upload_approved': return '✅'
      case 'upload_rejected': return '❌'
      case 'case_pending': return '📋'
      case 'system': return '🔔'
      default: return '💬'
    }
  }

  const fetchNotifications = async () => {
    if (!user) return
    
    try {
      const isAdmin = user.role === 'admin'
      const res = await api.get('/notifications/list', {
        params: {
          user_id: user.username,
          is_admin: isAdmin,
          limit: 50
        }
      })
      
      const data = res.data
      setNotifications(data.notifications || [])
      setUnreadCount(data.unread_count || 0)
    } catch (error) {
      console.error('获取通知失败:', error)
      setNotifications([])
      setUnreadCount(0)
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async (id: string) => {
    try {
      await api.post(`/notifications/${id}/read`)
      setNotifications(prev => prev.map(n => 
        n.id === id ? { ...n, is_read: true } : n
      ))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  }

  const markAllAsRead = async () => {
    if (!user) return
    try {
      const isAdmin = user.role === 'admin'
      await api.post('/notifications/read-all', null, {
        params: { user_id: user.username, is_admin: isAdmin }
      })
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch (error) {
      console.error('标记全部已读失败:', error)
    }
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'upload_pending':
        return <Upload className="w-5 h-5 text-blue-400" />
      case 'upload_approved':
        return <Check className="w-5 h-5 text-green-400" />
      case 'upload_rejected':
        return <AlertCircle className="w-5 h-5 text-red-400" />
      case 'case_pending':
        return <FileText className="w-5 h-5 text-yellow-400" />
      case 'system':
        return <Shield className="w-5 h-5 text-purple-400" />
      default:
        return <MessageSquare className="w-5 h-5 text-gray-400" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
      case 'urgent':
        return 'border-l-red-500'
      case 'normal':
        return 'border-l-yellow-500'
      default:
        return 'border-l-blue-500'
    }
  }

  const getPriorityColorValue = (priority: string) => {
    switch (priority) {
      case 'high':
      case 'urgent':
        return '#ef4444'
      case 'normal':
        return '#eab308'
      default:
        return '#3b82f6'
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN')
  }

  const toggleSound = () => {
    setSoundEnabled(!soundEnabled)
    saveSettings()
  }

  const toggleDesktop = () => {
    if (!desktopEnabled && notificationPermission !== 'granted') {
      requestDesktopPermission()
    } else {
      setDesktopEnabled(!desktopEnabled)
      saveSettings()
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2.5 rounded-xl transition-all duration-300"
        style={{ 
          background: isLight ? '#ffffff' : 'rgba(26,26,46,0.8)',
          border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.2)',
          color: isLight ? '#64748b' : '#909090'
        }}
        onMouseEnter={(e) => {
          if (isLight) {
            e.currentTarget.style.background = '#f8fafc'
            e.currentTarget.style.borderColor = 'rgba(59,130,246,0.4)'
            e.currentTarget.style.color = '#3b82f6'
          }
        }}
        onMouseLeave={(e) => {
          if (isLight) {
            e.currentTarget.style.background = '#ffffff'
            e.currentTarget.style.borderColor = '#e2e8f0'
            e.currentTarget.style.color = '#64748b'
          }
        }}
        title="消息通知"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] flex items-center justify-center px-1 text-xs font-bold bg-gradient-to-br from-red-500 to-red-600 text-white rounded-full animate-pulse shadow-lg shadow-red-500/30">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => {
              setIsOpen(false)
              setShowSettings(false)
            }} 
          />
          <div className="absolute right-0 top-full mt-2 z-50 w-[420px] max-h-[600px] rounded-xl shadow-2xl overflow-hidden"
            style={{
              background: isLight ? '#ffffff' : '#1a1a2e',
              border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.2)'
            }}
          >
            <div className="px-4 py-3 flex items-center justify-between" style={{
              borderBottom: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.2)',
              background: isLight ? '#f8fafc' : 'linear-gradient(to right, rgba(59,130,246,0.1), transparent)'
            }}>
              <div className="flex items-center gap-2">
                <Bell className="w-5 h-5" style={{ color: isLight ? '#3b82f6' : '#3b82f6' }} />
                <h3 className="font-bold" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>消息中心</h3>
                {unreadCount > 0 && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-red-500 text-white rounded-full">
                    {unreadCount} 未读
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowSettings(!showSettings)
                  }}
                  className="p-1.5 rounded-lg transition-colors"
                  style={{ 
                    background: isLight ? 'transparent' : 'rgba(59,130,246,0.1)',
                    color: isLight ? '#64748b' : '#606080'
                  }}
                  onMouseEnter={(e) => { if (!isLight) e.currentTarget.style.background = 'rgba(59,130,246,0.2)' }}
                  onMouseLeave={(e) => { if (!isLight) e.currentTarget.style.background = 'rgba(59,130,246,0.1)' }}
                  title="通知设置"
                >
                  <Settings className="w-4 h-4" />
                </button>
                {!showSettings && (
                  <>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        markAllAsRead()
                      }}
                      className="text-xs px-2 py-1 transition-colors"
                      style={{ color: isLight ? '#3b82f6' : '#3b82f6' }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = isLight ? '#2563eb' : '#f0d78c' }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = isLight ? '#3b82f6' : '#3b82f6' }}
                    >
                      全部已读
                    </button>
                  </>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setIsOpen(false)
                    setShowSettings(false)
                  }}
                  className="p-1 rounded transition-colors"
                  style={{ 
                    background: isLight ? 'transparent' : 'rgba(59,130,246,0.1)',
                    color: isLight ? '#64748b' : '#606080'
                  }}
                  onMouseEnter={(e) => { if (!isLight) e.currentTarget.style.background = 'rgba(59,130,246,0.2)' }}
                  onMouseLeave={(e) => { if (!isLight) e.currentTarget.style.background = 'rgba(59,130,246,0.1)' }}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {showSettings ? (
              <div className="p-4 space-y-4">
                <h4 className="font-medium mb-3 flex items-center gap-2" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>
                  <Settings className="w-4 h-4" style={{ color: isLight ? '#3b82f6' : '#3b82f6' }} />
                  通知设置
                </h4>
                
                <div className="space-y-3">
                  <button
                    onClick={toggleSound}
                    className="w-full flex items-center justify-between p-3 rounded-lg transition-colors"
                    style={{ 
                      background: isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.1)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)' }}
                  >
                    <div className="flex items-center gap-3">
                      {soundEnabled ? (
                        <Volume2 className="w-5 h-5" style={{ color: isLight ? '#3b82f6' : '#3b82f6' }} />
                      ) : (
                        <VolumeX className="w-5 h-5" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
                      )}
                      <div className="text-left">
                        <div className="text-sm font-medium" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>声音提示</div>
                        <div className="text-xs" style={{ color: isLight ? '#64748b' : '#606080' }}>收到新通知时播放提示音</div>
                      </div>
                    </div>
                    <div className="w-12 h-6 rounded-full transition-colors relative" style={{
                      background: soundEnabled ? '#3b82f6' : (isLight ? '#e2e8f0' : '#303045')
                    }}>
                      <div className="absolute top-1 w-4 h-4 rounded-full bg-white transition-transform shadow-md" style={{
                        transform: soundEnabled ? 'translateX(28px)' : 'translateX(4px)'
                      }} />
                    </div>
                  </button>

                  <button
                    onClick={toggleDesktop}
                    className="w-full flex items-center justify-between p-3 rounded-lg transition-colors"
                    style={{ 
                      background: isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.1)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)' }}
                  >
                    <div className="flex items-center gap-3">
                      <Monitor className="w-5 h-5" style={{ color: isLight ? (desktopEnabled ? '#3b82f6' : '#94a3b8') : (desktopEnabled ? '#3b82f6' : '#606080') }} />
                      <div className="text-left">
                        <div className="text-sm font-medium" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>桌面通知</div>
                        <div className="text-xs" style={{ color: isLight ? '#64748b' : '#606080' }}>在桌面显示通知弹窗</div>
                      </div>
                    </div>
                    <div className="w-12 h-6 rounded-full transition-colors relative" style={{
                      background: desktopEnabled ? '#3b82f6' : (isLight ? '#e2e8f0' : '#303045')
                    }}>
                      <div className="absolute top-1 w-4 h-4 rounded-full bg-white transition-transform shadow-md" style={{
                        transform: desktopEnabled ? 'translateX(28px)' : 'translateX(4px)'
                      }} />
                    </div>
                  </button>

                  {notificationPermission === 'denied' && (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                      桌面通知权限已被拒绝，请在浏览器设置中启用
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                <div className="max-h-[400px] overflow-y-auto">
                  {loading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="w-8 h-8 border-4 rounded-full animate-spin" style={{ borderColor: isLight ? 'rgba(59,130,246,0.2)' : 'rgba(59,130,246,0.2)', borderTopColor: '#3b82f6' }} />
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12" style={{ color: isLight ? '#64748b' : '#606080' }}>
                      <Bell className="w-12 h-12 mb-3 opacity-50" />
                      <p className="text-sm">暂无消息通知</p>
                    </div>
                  ) : (
                    <div className="divide-y" style={{ borderTopColor: isLight ? '#f1f5f9' : 'rgba(59,130,246,0.1)' }}>
                      {notifications.map((notification) => (
                        <div
                          key={notification.id}
                          onClick={() => {
                            markAsRead(notification.id)
                          }}
                          className="relative px-4 py-3 cursor-pointer transition-all duration-200 border-l-4"
                          style={{ 
                            borderLeftColor: getPriorityColorValue(notification.priority),
                            background: notification.is_read 
                              ? (isLight ? 'transparent' : 'transparent')
                              : (isLight ? 'rgba(59,130,246,0.03)' : 'rgba(59,130,246,0.03)')
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.05)' }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = notification.is_read ? 'transparent' : (isLight ? 'rgba(59,130,246,0.03)' : 'rgba(59,130,246,0.03)') }}
                        >
                          <div className="flex gap-3">
                            <div className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: notification.is_read ? (isLight ? 'rgba(59,130,246,0.05)' : 'rgba(59,130,246,0.1)') : (isLight ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.2)') }}>
                              {getNotificationIcon(notification.type)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-start justify-between gap-2">
                                <h4 className="text-sm font-medium truncate" style={{ color: notification.is_read ? (isLight ? '#64748b' : '#909090') : (isLight ? '#1e293b' : '#e8e8e8') }}>
                                  {notification.title}
                                </h4>
                                {!notification.is_read && (
                                  <span className="flex-shrink-0 w-2 h-2 rounded-full" style={{ background: '#3b82f6' }} />
                                )}
                              </div>
                              <p className="mt-1 text-xs line-clamp-2" style={{ color: isLight ? '#64748b' : '#606080' }}>
                                {sanitizeText(notification.content)}
                              </p>
                              <div className="mt-2 flex items-center gap-2 text-xs" style={{ color: isLight ? '#94a3b8' : '#505060' }}>
                                <Clock className="w-3 h-3" />
                                <span>{formatTime(notification.created_at)}</span>
                                {notification.sender_name && (
                                  <>
                                    <span>·</span>
                                    <span>来自 {notification.sender_name}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            <ChevronRight className="w-4 h-4 self-center" style={{ color: isLight ? '#94a3b8' : '#505060' }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {notifications.length > 0 && (
                  <div className="px-4 py-3" style={{ 
                    borderTop: isLight ? '1px solid #e2e8f0' : '1px solid rgba(59,130,246,0.2)',
                    background: isLight ? '#f8fafc' : 'rgba(59,130,246,0.02)'
                  }}>
                    <button
                      onClick={() => setIsOpen(false)}
                      className="w-full py-2 text-sm transition-colors"
                      style={{ color: isLight ? '#3b82f6' : '#3b82f6' }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = isLight ? '#2563eb' : '#f0d78c' }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = isLight ? '#3b82f6' : '#3b82f6' }}
                    >
                      查看全部消息
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
