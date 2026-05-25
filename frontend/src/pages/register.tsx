import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RefreshCw, CheckCircle2, User, Lock, Shield, Sparkles, ChevronRight } from 'lucide-react'
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

const LOCAL_COLORS = COLORS

export default function RegisterPage() {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [captchaCode, setCaptchaCode] = useState('')
  const [captchaId, setCaptchaId] = useState('')
  const [captchaImage, setCaptchaImage] = useState('')
  const [captchaLoading, setCaptchaLoading] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [mounted, setMounted] = useState(false)
  const navigate = useNavigate()

  const getPasswordStrength = (pwd: string): { level: number; label: string; color: string } => {
    if (!pwd) return { level: 0, label: '', color: '' }
    let score = 0
    if (pwd.length >= 6) score++
    if (pwd.length >= 8) score++
    if (pwd.length >= 12) score++
    if (/[a-z]/.test(pwd)) score++
    if (/[A-Z]/.test(pwd)) score++
    if (/[0-9]/.test(pwd)) score++
    if (/[^a-zA-Z0-9]/.test(pwd)) score++
    if (score <= 2) return { level: 1, label: '弱', color: colors.CYBER_RED }
    if (score <= 4) return { level: 2, label: '中等', color: '#f59e0b' }
    if (score <= 6) return { level: 3, label: '良好', color: colors.CYBER_GREEN }
    return { level: 4, label: '强', color: colors.CYBER_CYAN }
  }

  const passwordStrength = getPasswordStrength(password)

  useEffect(() => { setMounted(true) }, [])

  const fetchCaptcha = useCallback(async () => {
    try {
      setCaptchaLoading(true)
      const res = await api.get<{ captcha_id: string; captcha_image: string }>('/auth/captcha')
      setCaptchaId(res.data.captcha_id)
      setCaptchaImage(res.data.captcha_image)
      setCaptchaCode('')
    } catch {
      setCaptchaId(''); setCaptchaImage('')
    } finally { setCaptchaLoading(false) }
  }, [])

  useEffect(() => { fetchCaptcha() }, [fetchCaptcha])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (username.length < 3) { setError('用户名至少3个字符'); return }
    if (password.length < 8) { setError('密码至少8个字符'); return }
    if (!/[A-Z]/.test(password)) { setError('密码需包含大写字母'); return }
    if (!/[a-z]/.test(password)) { setError('密码需包含小写字母'); return }
    if (!/[0-9]/.test(password)) { setError('密码需包含数字'); return }
    if (password !== confirmPassword) { setError('两次输入的密码不一致'); return }
    if (!captchaCode.trim()) { setError('请输入验证码'); return }
    setLoading(true)
    try {
      await api.post('/auth/register', { username, password, captcha_id: captchaId, captcha_code: captchaCode })
      setSuccess(true)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string; message?: string } } }
        setError(axiosErr.response?.data?.detail || axiosErr.response?.data?.message || '注册失败，请稍后重试')
      } else { setError('注册失败，请稍后重试') }
      fetchCaptcha()
    } finally { setLoading(false) }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #0a0a1a 100%)' }}>
        <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(0,240,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,240,255,0.03) 1px, transparent 1px)', backgroundSize: '50px 50px' }} />
        <div className="absolute top-0 left-0 w-[600px] h-[600px] rounded-full blur-[150px]" style={{ background: `radial-gradient(circle, ${colors.CYBER_GREEN}20 0%, transparent 70%)` }} />

        <div className="relative z-10 w-full max-w-md mx-6">
          <div className="relative rounded-2xl p-[1px]" style={{ background: `linear-gradient(135deg, ${colors.CYBER_GREEN}80 0%, ${colors.CYBER_CYAN}40 100%)` }}>
            <div className="relative rounded-[18px] p-8 text-center" style={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div className="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center mb-6" style={{ background: `${colors.CYBER_GREEN}15`, boxShadow: `0 0 30px ${colors.CYBER_GREEN}30` }}>
                <CheckCircle2 size={36} style={{ color: colors.CYBER_GREEN }} />
              </div>
              <GradientText as="h2" className="text-2xl font-bold mb-3" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_GREEN} 100%)` 
                  : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_GREEN} 100%)`, 
                WebkitBackgroundClip: 'text', 
                WebkitTextFillColor: 'transparent' 
              }}>注册成功</GradientText>
              <p className="mb-6 text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>您的注册申请已提交，请等待管理员审批后即可登录使用。</p>
              <Button onClick={() => navigate('/login')} className="w-full h-12 text-base font-semibold rounded-xl flex items-center justify-center gap-2" style={{ background: `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, color: '#000', boxShadow: `0 4px 20px ${colors.CYBER_CYAN}40` }}>
                返回登录 <ChevronRight size={18} />
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #0a0a1a 100%)' }}>
      {/* Cyberpunk Grid Background */}
      <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(0,240,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,240,255,0.03) 1px, transparent 1px)', backgroundSize: '50px 50px' }} />

      {/* Glow orbs */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] rounded-full blur-[150px]" style={{ background: `radial-gradient(circle, ${colors.CYBER_CYAN}15 0%, transparent 70%)` }} />
      <div className="absolute bottom-0 left-0 w-[700px] h-[700px] rounded-full blur-[180px]" style={{ background: `radial-gradient(circle, ${colors.CYBER_MAGENTA}10 0%, transparent 70%)` }} />

      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: `linear-gradient(90deg, transparent 0%, ${colors.CYBER_CYAN}80 50%, transparent 100%)` }} />

      {/* Left side branding */}
      <div className={`absolute left-0 top-0 h-full w-1/2 hidden xl:flex flex-col justify-center px-16 transition-all duration-1000 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-20'}`}>
        <div className="relative max-w-lg">
          <div className="relative mb-10">
            <div className="relative w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: `linear-gradient(145deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, boxShadow: `0 10px 40px ${colors.CYBER_CYAN}40` }}>
              <Sparkles size={32} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
            </div>
          </div>

          <GradientText as="h1" className="text-4xl font-bold mb-4" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
              : `linear-gradient(135deg, #f1f5f9 0%, ${colors.CYBER_CYAN} 100%)`, 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent', 
            letterSpacing: '-0.03em' 
          }}>
            设备检修知识系统
          </GradientText>
          <p className="text-base mb-10" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)', letterSpacing: '0.05em' }}>Equipment Maintenance Knowledge System</p>

          <div className="space-y-4">
            {[
              { color: colors.CYBER_CYAN, label: '安全可靠的企业级系统' },
              { color: colors.CYBER_BLUE, label: '强大的多模态检索能力' },
              { color: colors.CYBER_GREEN, label: '高效智能的作业指引' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 group cursor-pointer">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${item.color}20` }}>
                  <div className="w-2 h-2 rounded-full" style={{ background: item.color, boxShadow: `0 0 10px ${item.color}` }} />
                </div>
                <span style={{ color: 'rgba(241,245,249,0.8)' }} className="group-hover:text-white transition-colors">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Register form card */}
      <div className={`relative z-10 w-full max-w-md mx-6 transition-all duration-700 delay-300 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <div className="relative rounded-2xl p-[1px]" style={{ background: `linear-gradient(135deg, ${colors.CYBER_CYAN}60 0%, ${colors.CYBER_MAGENTA}40 100%)` }}>
          <div className="relative rounded-[18px] p-8" style={{ background: 'rgba(15,23,42,0.95)' }}>
            <div className="text-center mb-8">
              <div className="w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-4" style={{ background: `${colors.CYBER_CYAN}15`, boxShadow: `0 0 20px ${colors.CYBER_CYAN}20` }}>
                <Sparkles size={26} style={{ color: colors.CYBER_CYAN }} />
              </div>
              <GradientText as="h2" className="text-2xl font-bold mb-2" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
                  : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
                WebkitBackgroundClip: 'text', 
                WebkitTextFillColor: 'transparent' 
              }}>创建账号</GradientText>
              <p style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>填写以下信息完成注册</p>
            </div>

            {error && (
              <div className="mb-6 px-4 py-3 rounded-xl text-sm animate-fade-in-up" style={{ background: `${colors.CYBER_RED}15`, border: `1px solid ${colors.CYBER_RED}40`, color: colors.CYBER_RED }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="username" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? 'rgba(30,41,59,0.7)' : 'rgba(241,245,249,0.7)' }}>
                  <User size={14} style={{ color: colors.CYBER_CYAN }} /> 用户名
                </Label>
                <div className="relative group">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-20" style={{ color: isLight ? '#94a3b8' : '#505080' }}>
                    <User size={18} />
                  </div>
                  <Input id="username" type="text" placeholder="至少3个字符" value={username} onChange={(e) => setUsername(e.target.value)} required className="w-full h-12 pl-12 pr-4 rounded-xl text-base" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.9)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f1f5f9' 
                  }} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? 'rgba(30,41,59,0.7)' : 'rgba(241,245,249,0.7)' }}>
                  <Lock size={14} style={{ color: colors.CYBER_CYAN }} /> 密码
                </Label>
                <div className="relative group">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-20" style={{ color: isLight ? '#94a3b8' : '#505080' }}>
                    <Lock size={18} />
                  </div>
                  <Input id="password" type="password" placeholder="至少8位，含大小写字母和数字" value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full h-12 pl-12 pr-4 rounded-xl text-base" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.9)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f1f5f9' 
                  }} />
                </div>
                {password && (
                  <div className="mt-2 space-y-2">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map((level) => (
                        <div key={level} className="h-1 flex-1 rounded-full transition-all duration-300" style={{ background: level <= passwordStrength.level ? passwordStrength.color : `${colors.CYBER_CYAN}15` }} />
                      ))}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs" style={{ color: passwordStrength.color }}>密码强度：{passwordStrength.label}</span>
                      <span className="text-xs" style={{ color: isLight ? '#94a3b8' : 'rgba(148,163,184,0.5)' }}>{password.length < 8 ? '至少8位，含大小写字母和数字' : !/[A-Z]/.test(password) ? '需包含大写字母' : !/[a-z]/.test(password) ? '需包含小写字母' : !/[0-9]/.test(password) ? '需包含数字' : password.length >= 12 ? '优秀' : '良好'}</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? 'rgba(30,41,59,0.7)' : 'rgba(241,245,249,0.7)' }}>
                  <Lock size={14} style={{ color: colors.CYBER_CYAN }} /> 确认密码
                </Label>
                <div className="relative group">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 transition-colors pointer-events-none z-20" style={{ color: isLight ? '#94a3b8' : '#505080' }}>
                    <Lock size={18} />
                  </div>
                  <Input id="confirm-password" type="password" placeholder="再次输入密码" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className="w-full h-12 pl-12 pr-4 rounded-xl text-base" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.9)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f1f5f9' 
                  }} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="captcha" className="flex items-center gap-2 text-sm font-medium" style={{ color: isLight ? 'rgba(30,41,59,0.7)' : 'rgba(241,245,249,0.7)' }}>
                  <Shield size={14} style={{ color: colors.CYBER_CYAN }} /> 验证码
                </Label>
                <div className="flex items-center gap-3">
                  <Input id="captcha" type="text" placeholder="请输入验证码" value={captchaCode} onChange={(e) => setCaptchaCode(e.target.value)} className="h-12 text-center tracking-[0.2em] text-base rounded-xl" style={{ 
                    flex: 1, 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.9)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f1f5f9' 
                  }} autoComplete="off" required />
                  <button type="button" onClick={fetchCaptcha} className="h-12 w-[130px] rounded-xl overflow-hidden flex items-center justify-center" style={{ 
                    background: isLight ? '#f1f5f9' : 'rgba(30,41,59,0.8)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '30'}` 
                  }}>
                    {captchaLoading ? (
                      <div className="w-5 h-5 border-2 rounded-full animate-spin" style={{ borderColor: `${colors.CYBER_CYAN}30`, borderTopColor: colors.CYBER_CYAN }} />
                    ) : captchaImage ? (
                      <img src={captchaImage} alt="验证码" className="w-full h-full object-contain" draggable={false} />
                    ) : (
                      <span className="text-xs" style={{ color: isLight ? '#94a3b8' : '#505080' }}>加载中</span>
                    )}
                  </button>
                </div>
              </div>

              <Button type="submit" className="w-full h-12 text-base font-semibold rounded-xl flex items-center justify-center gap-2 transition-all mt-6" style={{ background: `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, color: '#000', boxShadow: `0 4px 20px ${colors.CYBER_CYAN}40` }} disabled={loading}>
                {loading ? (
                  <><div className="w-4 h-4 border-2 rounded-full animate-spin" style={{ borderColor: '#00000040', borderTopColor: '#000' }} /> 注册中...</>
                ) : (
                  <><Sparkles size={18} /> 注 册 <ChevronRight size={18} /></>
                )}
              </Button>

              <div className="text-center pt-4">
                <Link to="/login" className="inline-flex items-center gap-2 text-sm transition-colors" style={{ color: 'rgba(148,163,184,0.6)' }}>
                  已有账号？返回登录 <ChevronRight size={14} />
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Bottom info */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-center px-8" style={{ maxWidth: '400px' }}>
        <p className="text-xs" style={{ color: 'rgba(148,163,184,0.3)' }}>© 2026 设备检修知识检索与作业系统 v2.0</p>
        <p className="mt-1 tracking-wider text-xs" style={{ color: 'rgba(148,163,184,0.2)' }}>Powered by AI & Knowledge Graph</p>
      </div>
    </div>
  )
}