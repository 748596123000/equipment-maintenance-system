import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RefreshCw } from 'lucide-react'
import type { User } from '@/stores/auth-store'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [captchaCode, setCaptchaCode] = useState('')
  const [captchaId, setCaptchaId] = useState('')
  const [captchaImage, setCaptchaImage] = useState('')
  const [captchaLoading, setCaptchaLoading] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const user = useAuthStore((s) => s.user)

  const fetchCaptcha = useCallback(async () => {
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
  }, [])

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true })
    }
  }, [user, navigate])

  useEffect(() => {
    fetchCaptcha()
  }, [fetchCaptcha])

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
      const { token, user_id, username: name, role } = res.data as { token: string; user_id: string; username: string; role: string }
      const user: User = { id: user_id, username: name, role: role as 'admin' | 'user' }
      login(user, token)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string; message?: string } } }
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 to-indigo-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-2">
          <CardTitle className="text-2xl font-bold">设备检修知识检索与作业系统</CardTitle>
          <p className="text-sm text-muted-foreground">工业设备智能运维平台</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                type="text"
                placeholder="请输入用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="captcha">验证码</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="captcha"
                  type="text"
                  placeholder="请输入验证码"
                  value={captchaCode}
                  onChange={(e) => setCaptchaCode(e.target.value)}
                  className="flex-1"
                  autoComplete="off"
                  required
                />
                <div
                  className="flex-shrink-0 h-9 w-[120px] rounded-md border border-input cursor-pointer overflow-hidden flex items-center justify-center bg-white"
                  onClick={fetchCaptcha}
                  title="点击刷新验证码"
                >
                  {captchaLoading ? (
                    <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                  ) : captchaImage ? (
                    <img
                      src={captchaImage}
                      alt="验证码"
                      className="w-full h-full object-contain"
                      draggable={false}
                    />
                  ) : (
                    <span className="text-xs text-muted-foreground">加载中</span>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">点击图片刷新验证码</p>
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '登录中...' : '登 录'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
