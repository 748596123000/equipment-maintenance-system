import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RefreshCw, CheckCircle2 } from 'lucide-react'

export default function RegisterPage() {
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
  const navigate = useNavigate()

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
    fetchCaptcha()
  }, [fetchCaptcha])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (username.length < 3) {
      setError('用户名至少3个字符')
      return
    }
    if (password.length < 6) {
      setError('密码至少6个字符')
      return
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }
    if (!captchaCode.trim()) {
      setError('请输入验证码')
      return
    }

    setLoading(true)

    try {
      await api.post('/auth/register', {
        username,
        password,
        captcha_id: captchaId,
        captcha_code: captchaCode,
      })
      setSuccess(true)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string; message?: string } } }
        setError(axiosErr.response?.data?.detail || axiosErr.response?.data?.message || '注册失败，请稍后重试')
      } else {
        setError('注册失败，请稍后重试')
      }
      fetchCaptcha()
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 to-indigo-800 p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center space-y-4">
            <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto" />
            <h2 className="text-xl font-bold">注册成功</h2>
            <p className="text-muted-foreground">
              您的注册申请已提交，请等待管理员审批后即可登录使用。
            </p>
            <Button onClick={() => navigate('/login')} className="w-full">
              返回登录
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 to-indigo-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-2">
          <CardTitle className="text-2xl font-bold">用户注册</CardTitle>
          <p className="text-sm text-muted-foreground">设备检修知识检索与作业系统</p>
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
                placeholder="至少3个字符"
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
                placeholder="至少6个字符"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password">确认密码</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="再次输入密码"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
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
              {loading ? '注册中...' : '注 册'}
            </Button>
            <div className="text-center">
              <Link
                to="/login"
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                已有账号？返回登录
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
