import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { User, Lock, Shield, Calendar } from 'lucide-react'

interface UserInfo {
  user_id: string
  username: string
  role: string
  created_at: string
}

export default function ProfilePage() {
  const { user } = useAuthStore()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    async function fetchUserInfo() {
      try {
        const res = await api.get('/auth/me')
        setUserInfo(res.data as UserInfo)
      } catch {
        if (user) {
          setUserInfo({
            user_id: user.id,
            username: user.username,
            role: user.role,
            created_at: '',
          })
        }
      } finally {
        setLoading(false)
      }
    }
    fetchUserInfo()
  }, [user])

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')

    if (newPassword.length < 6) {
      setPasswordError('新密码长度至少6位')
      return
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('两次输入的新密码不一致')
      return
    }
    if (oldPassword === newPassword) {
      setPasswordError('新密码不能与旧密码相同')
      return
    }

    setChangingPassword(true)
    try {
      await api.put('/auth/password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
      setPasswordSuccess('密码修改成功')
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { message?: string } } }
        setPasswordError(axiosErr.response?.data?.message || '密码修改失败')
      } else {
        setPasswordError('密码修改失败')
      }
    } finally {
      setChangingPassword(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">个人信息</h1>
        <div className="h-64 animate-pulse rounded-lg bg-muted" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">个人信息</h1>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            基本信息
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold">
              {userInfo?.username?.charAt(0) || '?'}
            </div>
            <div className="space-y-1">
              <h3 className="text-xl font-semibold">{userInfo?.username || user?.username}</h3>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={
                  userInfo?.role === 'admin'
                    ? 'bg-red-100 text-red-800 border-red-200'
                    : 'bg-blue-100 text-blue-800 border-blue-200'
                }>
                  <Shield className="mr-1 h-3 w-3" />
                  {userInfo?.role === 'admin' ? '管理员' : '普通用户'}
                </Badge>
              </div>
            </div>
          </div>

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">用户ID</p>
              <p className="font-mono text-sm">{userInfo?.user_id || '-'}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">用户名</p>
              <p className="text-sm font-medium">{userInfo?.username || '-'}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">角色</p>
              <p className="text-sm">{userInfo?.role === 'admin' ? '系统管理员' : '普通用户'}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                注册时间
              </p>
              <p className="text-sm">
                {userInfo?.created_at
                  ? new Date(userInfo.created_at).toLocaleString('zh-CN')
                  : '-'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            修改密码
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            {passwordError && (
              <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {passwordError}
              </div>
            )}
            {passwordSuccess && (
              <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
                {passwordSuccess}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="old-password">当前密码</Label>
              <Input
                id="old-password"
                type="password"
                placeholder="请输入当前密码"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-password">新密码</Label>
              <Input
                id="new-password"
                type="password"
                placeholder="请输入新密码（至少6位）"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password">确认新密码</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="请再次输入新密码"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={changingPassword}>
              {changingPassword ? '修改中...' : '修改密码'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
