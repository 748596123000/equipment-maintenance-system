import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { GradientText } from '@/components/ui/gradient-text'
import { Shield, Lock, User, ChevronRight, RefreshCw } from 'lucide-react'
import { useTheme, COLORS } from '@/hooks/useTheme'

const LOCAL_COLORS = COLORS

export default function LoginPage() {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [captchaCode, setCaptchaCode] = useState('')
  const [captchaId, setCaptchaId] = useState('')
  const [captchaImage, setCaptchaImage] = useState('')
  const [captchaLoading, setCaptchaLoading] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mounted, setMounted] = useState(false)
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const user = useAuthStore((s) => s.user)

  useEffect(() => {
    setMounted(true)
  }, [])

  const fetchCaptcha = async () => {
    try {
      setCaptchaLoading(true)
      const res = await api.get<{ captcha_id: string; captcha_image: string }>('/auth/captcha')
      setCaptchaId(res.data.captcha_id)
      setCaptchaImage(res.data.captcha_image)
      setCaptchaCode('')
    } catch {
      setCaptchaId('')
      setCaptchaImage('')
    } finally {
      setCaptchaLoading(false)
    }
  }

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true })
    }
  }, [user, navigate])

  useEffect(() => {
    fetchCaptcha()
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!captchaCode.trim()) {
      setError('请输入验证码')
      return
    }

    setLoading(true)

    try {
      const res = await api.post('/auth/login', {
        username,
        password,
        captcha_id: captchaId,
        captcha_code: captchaCode,
      })
      const { token, user_id, username: name, role } = res.data as { 
        token: string; 
        user_id: string; 
        username: string; 
        role: string 
      }
      const userData = { 
        id: user_id, 
        username: name, 
        role: role as 'admin' | 'user' 
      }
      login(userData, token)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { 
          response?: { 
            data?: { 
              detail?: string; 
              message?: string 
            } 
          } 
        }
        setError(axiosErr.response?.data?.detail || axiosErr.response?.data?.message || '登录失败，请检查用户名和密码')
      } else {
        setError('登录失败，请检查用户名和密码')
      }
      fetchCaptcha()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div 
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{
        background: isLight
          ? 'linear-gradient(180deg, #f8fafc 0%, #e2e8f0 50%, #f0f4f8 100%)'
          : 'linear-gradient(180deg, #050510 0%, #0a0a1f 50%, #050515 100%)'
      }}
    >
      {/* CSS-only粒子背景 */}
      <div className="particle-container pointer-events-none">
        <div className="css-particles" style={{ left: '5%', animationDelay: '0s', animationDuration: '25s', boxShadow: '0 0 6px #00f0ff' }} />
        <div className="css-particles" style={{ left: '15%', animationDelay: '4s', animationDuration: '20s', boxShadow: '0 0 6px #ff00ff' }} />
        <div className="css-particles" style={{ left: '25%', animationDelay: '8s', animationDuration: '28s', boxShadow: '0 0 6px #8b5cf6' }} />
        <div className="css-particles" style={{ left: '40%', animationDelay: '2s', animationDuration: '22s', boxShadow: '0 0 6px #00f0ff' }} />
        <div className="css-particles" style={{ left: '55%', animationDelay: '6s', animationDuration: '26s', boxShadow: '0 0 6px #0066ff' }} />
        <div className="css-particles" style={{ left: '70%', animationDelay: '10s', animationDuration: '24s', boxShadow: '0 0 6px #ff00ff' }} />
        <div className="css-particles" style={{ left: '80%', animationDelay: '3s', animationDuration: '18s', boxShadow: '0 0 6px #00f0ff' }} />
        <div className="css-particles" style={{ left: '90%', animationDelay: '7s', animationDuration: '30s', boxShadow: '0 0 6px #8b5cf6' }} />
      </div>
      
      {/* 扫描线覆盖层 */}
      <div className="scanline-overlay pointer-events-none" />
      
      {/* 焦散光斑 */}
      <div className="caustic-light pointer-events-none" style={{ top: '20%', left: '20%' }} />
      <div className="caustic-light pointer-events-none" style={{ bottom: '30%', right: '15%', animationDelay: '3s' }} />
      
      {/* Cyberpunk Grid Background */}
      <div 
        className="absolute inset-0 opacity-40 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,240,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,240,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px'
        }}
      />
      
      {/* Ambient Glow Effects */}
      <div 
        className="absolute top-0 left-0 w-[500px] h-[500px] rounded-full animate-pulse pointer-events-none"
        style={{ 
          background: 'radial-gradient(circle, rgba(0,240,255,0.15) 0%, transparent 70%)',
          animationDuration: '4s'
        }} 
      />
      <div 
        className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full animate-pulse pointer-events-none"
        style={{ 
          background: 'radial-gradient(circle, rgba(255,0,255,0.1) 0%, transparent 70%)',
          animationDuration: '6s',
          animationDelay: '2s'
        }} 
      />
      
      {/* 增强的几何装饰 - 3D立体方块 */}
      <div 
        className="absolute top-[10%] left-[8%] w-20 h-20 border-2 animate-float perspective-container pointer-events-none"
        style={{ 
          borderColor: 'rgba(0,240,255,0.25)',
          animationDuration: '10s',
          transform: 'rotateY(15deg) rotateX(-15deg)',
          transformStyle: 'preserve-3d'
        }} 
      >
        <div className="absolute inset-0 border border-rgba(0,240,255,0.1)" style={{ transform: 'translateZ(20px)' }} />
      </div>
      <div 
        className="absolute top-[20%] right-[12%] w-16 h-16 border-2 animate-float pointer-events-none"
        style={{ 
          borderColor: 'rgba(255,0,255,0.2)',
          animationDuration: '12s',
          animationDelay: '1s',
          transform: 'rotate(45deg)'
        }} 
      />
      <div 
        className="absolute bottom-[15%] left-[15%] w-14 h-14 border animate-float pointer-events-none"
        style={{ 
          borderColor: 'rgba(139,92,246,0.15)',
          animationDuration: '14s',
          animationDelay: '2s',
          transform: 'rotate(30deg)'
        }} 
      />
      
      {/* 动态电路线条装饰 */}
      <svg className="absolute top-[30%] left-[5%] w-32 h-32 opacity-20 pointer-events-none" viewBox="0 0 100 100">
        <path d="M10,50 L30,50 L30,30 L50,30 L50,50 L70,50 L70,70 L90,70" 
              stroke="rgba(0,240,255,0.5)" strokeWidth="1" fill="none" />
        <circle cx="30" cy="50" r="3" fill="rgba(0,240,255,0.5)" />
        <circle cx="50" cy="30" r="3" fill="rgba(0,240,255,0.5)" />
        <circle cx="70" cy="50" r="3" fill="rgba(0,240,255,0.5)" />
      </svg>
      <svg className="absolute bottom-[25%] right-[8%] w-28 h-28 opacity-15 pointer-events-none" viewBox="0 0 100 100">
        <path d="M90,30 L70,30 L70,50 L50,50 L50,70 L30,70 L30,90" 
              stroke="rgba(255,0,255,0.5)" strokeWidth="1" fill="none" />
        <circle cx="70" cy="30" r="3" fill="rgba(255,0,255,0.5)" />
        <circle cx="50" cy="50" r="3" fill="rgba(255,0,255,0.5)" />
        <circle cx="30" cy="70" r="3" fill="rgba(255,0,255,0.5)" />
      </svg>
      
      {/* 全息装饰线条 */}
      <div className="absolute top-[40%] right-[5%] w-0.5 h-40 holographic opacity-30 pointer-events-none" />
      <div className="absolute bottom-[35%] left-[3%] w-0.5 h-32 holographic opacity-20 pointer-events-none" style={{ animationDelay: '2s' }} />
      
      {/* Top Cyber Accent Line */}
      <div 
        className="absolute top-0 left-0 right-0 h-0.5 pointer-events-none"
        style={{ background: `linear-gradient(90deg, transparent 0%, ${colors.CYBER_CYAN} 50%, transparent 100%)` }} 
      />

      {/* Login Form Card with 3D Effect */}
      <div 
        className={`
          relative z-10 w-full max-w-[440px] mx-6
          transition-all duration-700
          ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}
        `}
      >
        {/* 流动边框效果外层 */}
        <div className="cyber-border-animated rounded-2xl p-[2px]" style={{ pointerEvents: 'none' }}>
          <div 
            className="relative rounded-xl p-8"
            style={{ 
              background: isLight ? 'rgba(255, 255, 255, 0.98)' : 'rgba(10, 10, 25, 0.95)',
              boxShadow: isLight ? '0 25px 50px -12px rgba(0, 0, 0, 0.1), 0 0 40px rgba(59, 130, 246, 0.05)' : '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 40px rgba(0, 240, 255, 0.1)',
              position: 'relative',
              zIndex: 20,
              pointerEvents: 'auto'
            }}
          >
            {/* Card Header */}
            <div className="text-center mb-8">
              <div 
                className="w-14 h-14 mx-auto rounded-xl flex items-center justify-center mb-4"
                style={{ 
                  background: `linear-gradient(135deg, ${colors.CYBER_CYAN}20, ${colors.CYBER_CYAN}05)`,
                  border: `1px solid ${colors.CYBER_CYAN}30`
                }}
              >
                <Shield size={26} style={{ color: colors.CYBER_CYAN }} />
              </div>
              <GradientText
                as="h2"
                className="text-2xl font-bold mb-2"
                style={{ 
                  background: isLight 
                    ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
                    : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}
              >
                欢迎回来
              </GradientText>
              <p style={{ color: isLight ? '#64748b' : '#6b7280' }}>设备检修知识检索与作业系统</p>
            </div>
            
            {/* Error Message */}
            {error && (
              <div 
                className="mb-6 px-4 py-3 rounded-lg text-sm animate-fade-in-up"
                style={{ 
                  background: isLight ? 'rgba(220, 38, 38, 0.08)' : 'rgba(255, 51, 102, 0.1)',
                  border: isLight ? '1px solid rgba(220, 38, 38, 0.2)' : '1px solid rgba(255, 51, 102, 0.3)',
                  color: isLight ? '#dc2626' : '#ff3366'
                }}
                role="alert"
                aria-live="assertive"
              >
                {error}
              </div>
            )}
            
            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-5" role="form" aria-label="登录表单" noValidate>
              {/* Username Field */}
              <div className="space-y-2">
                <Label htmlFor="username" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? '#475569' : '#a0a0c0' }}>
                  <User size={14} style={{ color: colors.CYBER_CYAN }} />
                  用户名
                </Label>
                <div className="relative group">
                  <div 
                    className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-10"
                    style={{ color: isLight ? '#94a3b8' : '#505080' }}
                  >
                    <User size={18} />
                  </div>
                  <Input
                    id="username"
                    type="text"
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    aria-required="true"
                    className="w-full h-12 pl-12 pr-4 rounded-lg focus:outline-none transition-all"
                    style={{ 
                      background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)',
                      border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.2)',
                      color: isLight ? '#1e293b' : '#ffffff'
                    }}
                  />
                  <div 
                    className="absolute inset-0 rounded-lg pointer-events-none transition-all"
                    style={{ border: '1px solid transparent' }} 
                  />
                </div>
              </div>
              
              {/* Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? '#475569' : '#a0a0c0' }}>
                  <Lock size={14} style={{ color: colors.CYBER_CYAN }} />
                  密码
                </Label>
                <div className="relative group">
                  <div 
                    className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-10"
                    style={{ color: isLight ? '#94a3b8' : '#505080' }}
                  >
                    <Lock size={18} />
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="请输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    aria-required="true"
                    className="w-full h-12 pl-12 pr-4 rounded-lg focus:outline-none transition-all"
                    style={{ 
                      background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)',
                      border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.2)',
                      color: isLight ? '#1e293b' : '#ffffff'
                    }}
                  />
                  <div 
                    className="absolute inset-0 rounded-lg pointer-events-none transition-all"
                    style={{ border: '1px solid transparent' }} 
                  />
                </div>
              </div>
              
              {/* Captcha Field */}
              <div className="space-y-2">
                <Label htmlFor="captcha" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? '#475569' : '#a0a0c0' }}>
                  <Shield size={14} style={{ color: colors.CYBER_CYAN }} />
                  验证码
                </Label>
                <div className="flex items-center gap-3">
                  <Input
                    id="captcha"
                    type="text"
                    placeholder="请输入验证码"
                    value={captchaCode}
                    onChange={(e) => setCaptchaCode(e.target.value)}
                    className="h-12 text-center tracking-[0.3em] text-lg rounded-lg focus:outline-none"
                    style={{ 
                      background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)',
                      border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.2)',
                      flex: 1,
                      color: isLight ? '#1e293b' : '#ffffff'
                    }}
                    autoComplete="off"
                  />
                  <button
                    type="button"
                    onClick={fetchCaptcha}
                    className="h-12 w-[140px] rounded-lg overflow-hidden flex items-center justify-center transition-all"
                    style={{ 
                      background: isLight ? '#ffffff' : 'rgba(10, 10, 25, 0.9)',
                      border: isLight ? '1px solid #e2e8f0' : '1px solid rgba(0, 240, 255, 0.2)'
                    }}
                    role="button"
                    aria-label="刷新验证码"
                  >
                    {captchaLoading ? (
                      <RefreshCw className="h-5 w-5 animate-spin" style={{ color: colors.CYBER_CYAN }} />
                    ) : captchaImage ? (
                      <img
                        src={captchaImage}
                        alt="验证码"
                        className="w-full h-full object-contain"
                        draggable={false}
                      />
                    ) : (
                      <span className="text-xs" style={{ color: isLight ? '#94a3b8' : '#505080' }}>加载中</span>
                    )}
                  </button>
                </div>
              </div>
              
              {/* Submit Button */}
              <Button 
                type="submit" 
                className="w-full h-12 text-base font-semibold rounded-lg flex items-center justify-center gap-2 transition-all mt-6"
                style={{ 
                  background: `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`,
                  color: '#000000',
                  boxShadow: `0 4px 20px rgba(0, 240, 255, 0.3)`,
                  position: 'relative',
                  zIndex: 30
                }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    登录中...
                  </>
                ) : (
                  <>
                    登 录
                    <ChevronRight size={18} />
                  </>
                )}
              </Button>
              
              {/* Register Link */}
              <div className="text-center pt-4">
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 text-sm transition-colors"
                  style={{ color: isLight ? '#475569' : '#6b7280' }}
                >
                  没有账号？立即注册
                  <ChevronRight size={14} />
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
      
      {/* Bottom Info */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-center text-xs pointer-events-none" style={{ color: isLight ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.3)' }}>
        <p>© 2026 设备检修知识检索与作业系统 v2.0</p>
        <p className="mt-1 tracking-wider">Powered by AI & Knowledge Graph</p>
      </div>
    </div>
  )
}