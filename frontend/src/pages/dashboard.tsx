import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { FileText, Search, Users, MessageSquare, Sparkles, TrendingUp, Clock, Zap, BrainCircuit, Cpu, Layers, ArrowRight, Lightbulb, BookOpen, HelpCircle } from 'lucide-react'
import { ResponsiveContainer, AreaChart, Area } from 'recharts'
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

interface StatCard {
  title: string
  value: number
  icon: React.ReactNode
  trend?: number
  color: string
}

const mockChartData = [
  { value: 20 },
  { value: 35 },
  { value: 28 },
  { value: 45 },
  { value: 38 },
  { value: 55 },
  { value: 48 },
  { value: 62 },
]

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const { theme } = useTheme()
  const navigate = useNavigate()
  const [stats, setStats] = useState<StatCard[]>([])
  const [loading, setLoading] = useState(true)
  const [mounted, setMounted] = useState(false)

  const isLight = theme === 'light'
  
  // Get theme-specific colors
  const colors = isLight ? COLORS.light : COLORS.dark

  // Aliases for backward compatibility
  const textPrimary = colors.textPrimary
  const textSecondary = colors.textSecondary
  const cardBg = colors.cardBg
  const cardBorder = colors.cardBorder
  const gradientStart = colors.gradientStart
  const accentGlow = colors.accentGlow

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    async function fetchStats() {
      try {
        if (user?.role === 'admin') {
          const res = await api.get('/admin/stats')
          const d = res.data
          setStats([
            { title: '知识库文档', value: d.document_count || 0, icon: <FileText className="h-5 w-5" />, trend: 12, color: colors.CYBER_CYAN },
            { title: '问答次数', value: d.chat_count || 0, icon: <Search className="h-5 w-5" />, trend: 8, color: colors.CYBER_BLUE },
            { title: '用户数量', value: d.user_count || 0, icon: <Users className="h-5 w-5" />, trend: 5, color: colors.CYBER_GREEN },
            { title: '知识分块', value: d.total_chunks || 0, icon: <MessageSquare className="h-5 w-5" />, trend: 15, color: colors.CYBER_PURPLE },
          ])
        } else {
          try {
            const res = await api.get('/upload/my/stats')
            const d = res.data
            setStats([
              { title: '知识库文档', value: d.total || 0, icon: <FileText className="h-5 w-5" />, trend: 12, color: colors.CYBER_CYAN },
              { title: '已完成', value: d.completed || 0, icon: <Search className="h-5 w-5" />, trend: 8, color: colors.CYBER_BLUE },
              { title: '待审批', value: d.pending || 0, icon: <MessageSquare className="h-5 w-5" />, trend: -3, color: colors.CYBER_MAGENTA },
            ])
          } catch {
            setStats([
              { title: '知识库文档', value: 0, icon: <FileText className="h-5 w-5" />, trend: 0, color: colors.CYBER_CYAN },
              { title: '已完成', value: 0, icon: <Search className="h-5 w-5" />, trend: 0, color: colors.CYBER_BLUE },
              { title: '待审批', value: 0, icon: <MessageSquare className="h-5 w-5" />, trend: 0, color: colors.CYBER_MAGENTA },
            ])
          }
        }
      } catch {
        setStats([
          { title: '知识库文档', value: 0, icon: <FileText className="h-5 w-5" />, trend: 0, color: colors.CYBER_CYAN },
          { title: '问答次数', value: 0, icon: <Search className="h-5 w-5" />, trend: 0, color: colors.CYBER_BLUE },
          { title: '用户数量', value: 0, icon: <Users className="h-5 w-5" />, trend: 0, color: colors.CYBER_GREEN },
          { title: '知识分块', value: 0, icon: <MessageSquare className="h-5 w-5" />, trend: 0, color: colors.CYBER_PURPLE },
        ])
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      fetchStats()
    } else {
      setLoading(false)
    }
  }, [user?.role])

  const quickActions = [
    { label: '知识检索', icon: Search, path: '/search', color: colors.CYBER_CYAN, description: '快速查找设备维修知识' },
    { label: '上传文档', icon: FileText, path: '/knowledge', color: colors.CYBER_BLUE, description: '添加新的知识库文档' },
    { label: '生成指引', icon: Sparkles, path: '/guide-generate', color: colors.CYBER_GREEN, description: 'AI 生成标准化作业指引' },
    { label: '查看图谱', icon: Layers, path: '/knowledge-graph', color: colors.CYBER_MAGENTA, description: '探索知识关系图谱' },
    { label: '查看案例', icon: BookOpen, path: '/cases', color: colors.CYBER_PURPLE, description: '查看维修案例库' },
    { label: '帮助中心', icon: HelpCircle, path: '/guide', color: colors.CYBER_BLUE, description: '使用指南和帮助' },
  ]
  
  const smartRecommendations = [
    {
      title: '检查常见故障',
      description: '根据您的使用习惯，推荐查看常见的发动机故障解决方案',
      icon: Lightbulb,
      color: colors.CYBER_CYAN,
      action: () => navigate('/search?query=发动机故障'),
      urgency: 'high'
    },
    {
      title: '完善知识库',
      description: '您有3篇文档可以添加到知识图谱，提升检索质量',
      icon: Layers,
      color: colors.CYBER_BLUE,
      action: () => navigate('/knowledge-base'),
      urgency: 'medium'
    },
    {
      title: '生成案例指引',
      description: '根据最新上传的案例，可以生成标准化的作业指引',
      icon: Sparkles,
      color: colors.CYBER_GREEN,
      action: () => navigate('/guide-generate'),
      urgency: 'low'
    }
  ]

  return (
    <div className={`space-y-6 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* Hero Banner - Theme-aware with 3D Perspective */}
      <div className="relative overflow-hidden rounded-2xl perspective-container" style={{
        background: isLight 
          ? `linear-gradient(135deg, ${colors.CYBER_BLUE}08 0%, ${colors.CYBER_CYAN}05 50%, ${colors.CYBER_PURPLE}05 100%)` 
          : `linear-gradient(135deg, ${colors.CYBER_BLUE}22 0%, ${colors.CYBER_CYAN}12 50%, ${colors.CYBER_PURPLE}15 100%)`,
        border: `1px solid ${isLight ? colors.CYBER_BLUE + '20' : colors.CYBER_CYAN + '30'}`,
        boxShadow: isLight 
          ? '0 4px 20px rgba(37, 99, 235, 0.08), inset 0 0 40px rgba(37, 99, 235, 0.03)'
          : `0 0 40px ${colors.CYBER_CYAN}15, inset 0 0 60px ${colors.CYBER_BLUE}08`
      }}>
        {/* Parallax Layer 3 - 最远层 */}
        <div className="parallax-layer-3 absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/4 w-32 h-32 rounded-full opacity-20" style={{
            background: `radial-gradient(circle, ${colors.CYBER_CYAN}30 0%, transparent 70%)`,
            animation: 'parallaxFloat 12s ease-in-out infinite'
          }} />
          <div className="absolute bottom-0 right-1/3 w-24 h-24 rounded-full opacity-15" style={{
            background: `radial-gradient(circle, ${colors.CYBER_BLUE}30 0%, transparent 70%)`,
            animation: 'parallaxFloat 15s ease-in-out infinite reverse'
          }} />
        </div>
        
        {/* Subtle Grid Background */}
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(${isLight ? colors.CYBER_BLUE + '06' : colors.CYBER_CYAN + '08'} 1px, transparent 1px),
            linear-gradient(90deg, ${isLight ? colors.CYBER_BLUE + '06' : colors.CYBER_CYAN + '08'} 1px, transparent 1px)
          `,
          backgroundSize: '30px 30px',
          opacity: isLight ? 0.4 : 0.5
        }} />
        
        {/* Glow Effects */}
        <div className="absolute top-0 left-1/4 w-96 h-96 rounded-full blur-3xl" style={{
          background: `radial-gradient(circle, ${isLight ? colors.CYBER_BLUE + '10' : colors.CYBER_CYAN + '20'} 0%, transparent 70%)`
        }} />
        <div className="absolute bottom-0 right-1/4 w-64 h-64 rounded-full blur-3xl" style={{
          background: `radial-gradient(circle, ${isLight ? colors.CYBER_CYAN + '08' : colors.CYBER_BLUE + '18'} 0%, transparent 70%)`
        }} />
        
        {/* Main Content */}
        <div className="relative z-10 flex flex-col items-center justify-center py-8 px-6">
          {/* Breathing Glow Behind Title */}
          <div 
            className="absolute"
            style={{
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '120%',
              height: '200%',
              background: `radial-gradient(ellipse, ${isLight ? colors.CYBER_BLUE + '08' : colors.CYBER_CYAN + '15'} 0%, transparent 70%)`,
              animation: 'breathe-glow 3s ease-in-out infinite',
              pointerEvents: 'none'
            }}
          />
          
          <GradientText
            as="h1"
            className="text-3xl md:text-4xl font-black tracking-wider text-center relative"
            style={{
              background: isLight
                ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 40%, ${colors.CYBER_CYAN} 70%, ${colors.CYBER_BLUE} 100%)`
                : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 40%, ${colors.CYBER_BLUE} 70%, ${colors.CYBER_CYAN} 100%)`,
              backgroundSize: '200% 200%',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              textShadow: isLight 
                ? `0 2px 20px rgba(37, 99, 235, 0.15)` 
                : `0 0 60px ${colors.CYBER_CYAN}50, 0 0 100px ${colors.CYBER_BLUE}30`,
              letterSpacing: '0.15em',
              animation: 'gradientShift 5s ease infinite'
            }}
          >
            龙芯中科技术股份有限公司
          </GradientText>
          
          <GradientText
            as="p"
            className="mt-3 text-sm tracking-widest relative"
            style={{
              background: isLight
                ? `linear-gradient(90deg, ${colors.CYBER_BLUE}, ${colors.CYBER_CYAN}, ${colors.CYBER_BLUE})`
                : `linear-gradient(90deg, ${colors.CYBER_BLUE}, ${colors.CYBER_CYAN}, ${colors.CYBER_BLUE})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '0.25em',
              opacity: isLight ? 0.7 : 0.85,
              animation: 'gradientShift 5s ease infinite',
              backgroundSize: '200% 200%'
            }}
          >
            LONGSYS TECHNOLOGY CO., LTD.
          </GradientText>
          
          {/* Decorative Line with Breathing Effect */}
          <div className="mt-5 h-px w-32 relative" style={{
            background: `linear-gradient(90deg, transparent, ${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}, transparent)`,
            boxShadow: isLight ? `0 0 10px ${colors.CYBER_BLUE}40` : `0 0 15px ${colors.CYBER_CYAN}`,
            animation: 'pulse-glow 2s ease-in-out infinite'
          }} />
        </div>
        
        {/* Corner Accents with 3D effect */}
        <div className="absolute top-3 left-3 w-10 h-10 border-l-2 border-t-2" style={{ borderColor: isLight ? `${colors.CYBER_BLUE}40` : `${colors.CYBER_CYAN}60` }} />
        <div className="absolute top-3 right-3 w-10 h-10 border-r-2 border-t-2" style={{ borderColor: isLight ? `${colors.CYBER_BLUE}40` : `${colors.CYBER_CYAN}60` }} />
        <div className="absolute bottom-3 left-3 w-10 h-10 border-l-2 border-b-2" style={{ borderColor: isLight ? `${colors.CYBER_CYAN}40` : `${colors.CYBER_BLUE}60` }} />
        <div className="absolute bottom-3 right-3 w-10 h-10 border-r-2 border-b-2" style={{ borderColor: isLight ? `${colors.CYBER_CYAN}40` : `${colors.CYBER_BLUE}60` }} />
      </div>

      {/* Header Section - Theme-aware with parallax */}
      <div className="relative parallax-layer-1">
        <div className="flex items-center gap-4 mb-2">
          <div 
            className="w-12 h-12 rounded-xl flex items-center justify-center glow-border"
            style={{ 
              background: isLight 
                ? `${colors.CYBER_BLUE}10` 
                : `linear-gradient(135deg, ${colors.CYBER_CYAN}20, ${colors.CYBER_CYAN}05)`,
              border: `1px solid ${isLight ? colors.CYBER_BLUE + '20' : colors.CYBER_CYAN + '30'}`,
              boxShadow: isLight 
                ? '0 4px 16px rgba(37, 99, 235, 0.15)' 
                : `0 0 20px rgba(0, 240, 255, 0.2)`
            }}
          >
            <Sparkles size={24} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
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
              欢迎回来，{user?.username || '用户'}
            </GradientText>
            <p className="text-sm" style={{ color: textSecondary }}>以下是系统运行概况</p>
          </div>
        </div>
        {/* Accent Line */}
        <div 
          className="w-full h-px mt-4"
          style={{ 
            background: `linear-gradient(90deg, transparent 0%, ${isLight ? colors.CYBER_BLUE + '50' : colors.CYBER_CYAN + '50'} 50%, transparent 100%)`
          }}
        />
      </div>

      {/* Stats Grid - Theme-aware with 3D cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-stagger">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div 
                key={i} 
                className="h-36 rounded-2xl animate-pulse"
                style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.5)',
                  border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(0, 240, 255, 0.1)'}`
                }}
              />
            ))
          : stats.map((stat, index) => (
              <div 
                key={stat.title} 
                className="cyber-card cyber-card-3d p-6 group cursor-pointer animate-fade-in-up"
                style={{ 
                  animationDelay: `${index * 0.1}s`,
                  background: isLight ? '#ffffff' : undefined,
                  border: isLight ? '1px solid #e2e8f0' : undefined
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div 
                    className="w-14 h-14 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
                    style={{ 
                      backgroundColor: `${stat.color}15`,
                      color: stat.color,
                      border: `1px solid ${stat.color}30`
                    }}
                  >
                    {stat.icon}
                  </div>
                  {stat.trend !== undefined && stat.trend !== 0 && (
                    <div 
                      className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
                        stat.trend > 0 ? (isLight ? 'bg-green-50' : 'bg-green-500/10') : (isLight ? 'bg-red-50' : 'bg-red-500/10')
                      }`}
                      style={{ color: stat.trend > 0 ? colors.CYBER_GREEN : (isLight ? colors.CYBER_BLUE : '#ff3366') }}
                    >
                      <TrendingUp size={12} className={stat.trend < 0 ? 'rotate-180' : ''} />
                      {Math.abs(stat.trend)}%
                    </div>
                  )}
                </div>
                <div 
                  className="text-3xl font-bold mb-1"
                  style={{ color: textPrimary }}
                >
                  {stat.value.toLocaleString()}
                </div>
                <div className="text-sm" style={{ color: textSecondary }}>{stat.title}</div>
                <div className="mt-4 h-12">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockChartData}>
                      <defs>
                        <linearGradient id={`gradient-${index}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={stat.color} stopOpacity={0.3} />
                          <stop offset="95%" stopColor={stat.color} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke={stat.color}
                        strokeWidth={2}
                        fill={`url(#gradient-${index})`}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
      </div>

      {/* Quick Actions - Theme-aware with holographic effect */}
      <div className="glass-card p-8" style={{
        boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
      }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center gap-3" style={{ color: textPrimary }}>
            <Zap size={22} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
            快捷操作
          </h2>
          <div className="text-xs" style={{ color: textSecondary }}>选择以下操作快速开始</div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {quickActions.map((action, index) => {
            const Icon = action.icon
            return (
              <button
                key={action.path}
                onClick={() => navigate(action.path)}
                className="quick-action-btn group cyber-card-3d"
                style={{ 
                  animationDelay: `${index * 0.1}s`,
                  background: isLight ? '#ffffff' : undefined,
                  border: isLight ? '1px solid #e2e8f0' : undefined
                }}
              >
                <div className="relative z-10 flex flex-col items-center gap-3">
                  <div 
                    className="w-14 h-14 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
                    style={{ 
                      backgroundColor: `${action.color}15`,
                      color: action.color,
                      border: `1px solid ${action.color}30`
                    }}
                  >
                    <Icon size={26} />
                  </div>
                  <div className="text-center">
                    <span className="text-sm font-medium block mb-1" style={{ color: textPrimary }}>
                      {action.label}
                    </span>
                    <span className="text-xs block" style={{ color: textSecondary }}>
                      {action.description}
                    </span>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
      
      {/* Smart Recommendations - Theme-aware */}
      <div className="glass-card p-8" style={{
        boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
      }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center gap-3" style={{ color: textPrimary }}>
            <BrainCircuit size={22} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
            智能推荐
          </h2>
          <div className="flex items-center gap-2 text-xs" style={{ color: textSecondary }}>
            <Cpu size={14} />
            基于 AI 分析
          </div>
        </div>
        
        <div className="space-y-4">
          {smartRecommendations.map((rec, index) => {
            const Icon = rec.icon
            const urgencyColors: Record<string, string> = {
              high: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN,
              medium: colors.CYBER_PURPLE,
              low: colors.CYBER_GREEN
            }
            const urgencyColor = urgencyColors[rec.urgency] || (isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN)
            return (
              <button
                key={index}
                onClick={rec.action}
                className="group w-full text-left p-5 rounded-xl transition-all duration-300 flex items-center gap-4"
                style={{ 
                  background: isLight ? '#ffffff' : 'rgba(15, 15, 35, 0.5)',
                  border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.1)',
                  borderLeft: `3px solid ${urgencyColor}`,
                  boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
                }}
              >
                <div 
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ 
                    backgroundColor: `${rec.color}15`,
                    color: rec.color,
                    border: `1px solid ${rec.color}30`
                  }}
                >
                  <Icon size={22} />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-sm mb-1" style={{ color: textPrimary }}>
                    {rec.title}
                  </h4>
                  <p className="text-xs line-clamp-2" style={{ color: textSecondary }}>
                    {rec.description}
                  </p>
                </div>
                <ArrowRight 
                  size={18} 
                  className="flex-shrink-0 transition-transform group-hover:translate-x-1" 
                  style={{ color: textSecondary }} 
                />
              </button>
            )
          })}
        </div>
      </div>

      {/* Bottom Section: Recent Activity & System Status - Theme-aware with 3D effect */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="glass-card p-6 cyber-card-3d">
          <div className="flex items-center gap-3 mb-6">
            <Clock size={20} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
            <h3 className="text-lg font-bold" style={{ color: textPrimary }}>最近活动</h3>
          </div>
          <div className="space-y-4">
            {[
              { time: '10分钟前', action: '上传了新文档', type: 'document' },
              { time: '30分钟前', action: '完成了知识检索', type: 'search' },
              { time: '1小时前', action: '生成了作业指引', type: 'guide' },
              { time: '2小时前', action: '更新了知识库', type: 'update' },
            ].map((item, index) => (
              <div 
                key={index} 
                className="flex items-center gap-4 p-3 rounded-xl transition-colors cursor-pointer"
                style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(15, 15, 35, 0.4)',
                  border: isLight ? '1px solid #e2e8f0' : 'none'
                }}
              >
                <div 
                  className="w-2 h-2 rounded-full"
                  style={{ 
                    background: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN, 
                    boxShadow: isLight ? `0 0 8px ${colors.CYBER_BLUE}50` : `0 0 10px ${colors.CYBER_CYAN}` 
                  }}
                />
                <div className="flex-1">
                  <p className="text-sm" style={{ color: textPrimary }}>{item.action}</p>
                  <p className="text-xs" style={{ color: textSecondary }}>{item.time}</p>
                </div>
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ 
                    background: isLight ? `${colors.CYBER_BLUE}10` : `${colors.CYBER_CYAN}10`,
                    color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN
                  }}
                >
                  <Sparkles size={14} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Status */}
        <div className="glass-card p-6 cyber-card-3d">
          <div className="flex items-center gap-3 mb-6">
            <TrendingUp size={20} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
            <h3 className="text-lg font-bold" style={{ color: textPrimary }}>系统状态</h3>
          </div>
          <div className="space-y-5">
            {[
              { name: '后端服务', status: '正常运行', color: colors.CYBER_GREEN },
              { name: '向量数据库', status: '正常', color: colors.CYBER_GREEN },
              { name: 'AI 模型', status: '已连接', color: colors.CYBER_GREEN },
              { name: '文档处理', status: '就绪', color: colors.CYBER_GREEN },
            ].map((item, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div 
                    className={`w-3 h-3 rounded-full ${isLight ? '' : 'animate-pulse'}`}
                    style={{ 
                      background: item.color, 
                      boxShadow: isLight ? `0 0 8px ${item.color}40` : `0 0 10px ${item.color}` 
                    }}
                  />
                  <span className="text-sm" style={{ color: textPrimary }}>{item.name}</span>
                </div>
                <span 
                  className="text-sm font-medium neon-text"
                  style={{ color: item.color }}
                >
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}