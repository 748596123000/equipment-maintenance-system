import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { api } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { User, Lock, Shield, Calendar, Activity, Info, Key, Settings2 } from 'lucide-react'
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

const LOCAL_COLORS = COLORS

interface UserInfo {
  user_id: string; username: string; role: string; created_at: string
}

export default function ProfilePage() {
  const { user } = useAuthStore()
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  const textPrimary = colors.textPrimary
  const textSecondary = colors.textSecondary
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
          setUserInfo({ user_id: user.id, username: user.username, role: user.role, created_at: '' })
        }
      } finally { setLoading(false) }
    }
    fetchUserInfo()
  }, [user])

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPasswordError(''); setPasswordSuccess('')
    if (newPassword.length < 8) { setPasswordError('新密码长度至少8位'); return }
    if (!/[A-Z]/.test(newPassword)) { setPasswordError('新密码需包含大写字母'); return }
    if (!/[a-z]/.test(newPassword)) { setPasswordError('新密码需包含小写字母'); return }
    if (!/[0-9]/.test(newPassword)) { setPasswordError('新密码需包含数字'); return }
    if (newPassword !== confirmPassword) { setPasswordError('两次输入的新密码不一致'); return }
    if (oldPassword === newPassword) { setPasswordError('新密码不能与旧密码相同'); return }
    setChangingPassword(true)
    try {
      await api.put('/auth/password', { old_password: oldPassword, new_password: newPassword })
      setPasswordSuccess('密码修改成功')
      setOldPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { message?: string } } }
        setPasswordError(axiosErr.response?.data?.message || '密码修改失败')
      } else { setPasswordError('密码修改失败') }
    } finally { setChangingPassword(false) }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <GradientText as="h1" className="text-2xl font-bold" style={{ 
          background: isLight 
            ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
            : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
          WebkitBackgroundClip: 'text', 
          WebkitTextFillColor: 'transparent' 
        }}>个人信息中心</GradientText>
        <div className="h-64 rounded-2xl" style={{ 
          background: isLight 
            ? 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)' 
            : 'linear-gradient(135deg, rgba(15,15,30,0.8) 0%, rgba(21,21,40,0.8) 100%)', 
          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}` 
        }} />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ 
          background: isLight 
            ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_CYAN} 100%)` 
            : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, 
          boxShadow: `0 10px 40px ${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}40` 
        }}>
          <Info size={28} style={{ color: isLight ? '#ffffff' : '#000' }} />
        </div>
        <div>
          <GradientText as="h1" className="text-2xl font-bold" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
              : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent' 
          }}>个人信息中心</GradientText>
          <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>管理您的账户信息和安全设置</p>
        </div>
      </div>

      {/* Accent line */}
      <div className="w-full h-px" style={{ background: `linear-gradient(90deg, transparent 0%, ${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}50 50%, transparent 100%)` }} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <div className="lg:col-span-1">
          <Card className="rounded-xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '30'}`,
            boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.06)' : undefined
          }}>
            <CardHeader className="text-center pb-4">
              <div className="mx-auto w-24 h-24 rounded-full flex items-center justify-center text-4xl font-bold text-black mb-4" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_CYAN} 100%)` 
                  : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, 
                boxShadow: `0 10px 40px ${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}40` 
              }}>
                {userInfo?.username?.charAt(0)?.toUpperCase() || '?'}
              </div>
              <GradientText as="h3" className="text-xl" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_BLUE} 100%)` 
                  : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_CYAN} 100%)`, 
                WebkitBackgroundClip: 'text', 
                WebkitTextFillColor: 'transparent' 
              }}>
                {userInfo?.username || user?.username}
              </GradientText>
              <Badge variant="outline" className="mx-auto mt-2 px-4 py-1" style={{ background: `${colors.CYBER_CYAN}20`, color: colors.CYBER_CYAN, borderColor: `${colors.CYBER_CYAN}50` }}>
                <Shield className="mr-1 h-3 w-3" />
                {userInfo?.role === 'admin' ? '管理员' : '普通用户'}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              <div className="flex items-center justify-between p-3 rounded-xl" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
                boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
              }}>
                <div className="flex items-center gap-2">
                  <User size={16} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
                  <span className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>用户ID</span>
                </div>
                <span className="text-sm font-mono" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>{userInfo?.user_id ? userInfo.user_id.slice(0, 8) + '...' : '-'}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}`,
                boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
              }}>
                <div className="flex items-center gap-2">
                  <Calendar size={16} style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }} />
                  <span className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>注册时间</span>
                </div>
                <span className="text-sm" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>
                  {userInfo?.created_at ? new Date(userInfo.created_at).toLocaleDateString('zh-CN') : '-'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '15'}`,
                boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
              }}>
                <div className="flex items-center gap-2">
                  <Activity size={16} style={{ color: colors.CYBER_GREEN }} />
                  <span className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>账户状态</span>
                </div>
                <Badge className="px-2 py-0.5" style={{ background: `${colors.CYBER_GREEN}20`, color: colors.CYBER_GREEN, borderColor: `${colors.CYBER_GREEN}50` }}>正常</Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Account Info */}
          <Card className="rounded-xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '30'}` 
          }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" style={{ color: colors.CYBER_CYAN }} /> 账户信息
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl" style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                  border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
                }}>
                  <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>用户名</p>
                  <p className="text-sm font-medium" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{userInfo?.username || user?.username}</p>
                </div>
                <div className="p-4 rounded-xl" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
                  }}>
                  <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>角色</p>
                  <p className="text-sm font-medium" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{userInfo?.role === 'admin' ? '系统管理员' : '普通用户'}</p>
                </div>
                <div className="p-4 rounded-xl" style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                  border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
                }}>
                  <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>用户ID</p>
                  <p className="text-sm font-mono break-all" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>{userInfo?.user_id || '-'}</p>
                </div>
                <div className="p-4 rounded-xl" style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(13,13,26,0.6)', 
                  border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
                }}>
                  <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>注册时间</p>
                  <p className="text-sm" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>
                    {userInfo?.created_at ? new Date(userInfo.created_at).toLocaleString('zh-CN') : '-'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Change Password */}
          <Card className="rounded-xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '30'}` 
          }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock className="h-5 w-5" style={{ color: colors.CYBER_CYAN }} /> 修改密码
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
                {passwordError && (
                  <div className="rounded-xl px-4 py-3 text-sm flex items-center gap-2" style={{ background: `${colors.CYBER_RED}15`, border: `1px solid ${colors.CYBER_RED}30`, color: colors.CYBER_RED }}>
                    <Shield className="h-4 w-4 shrink-0" /> {passwordError}
                  </div>
                )}
                {passwordSuccess && (
                  <div className="rounded-xl px-4 py-3 text-sm flex items-center gap-2" style={{ background: `${colors.CYBER_GREEN}15`, border: `1px solid ${colors.CYBER_GREEN}30`, color: colors.CYBER_GREEN }}>
                    <Shield className="h-4 w-4 shrink-0" /> {passwordSuccess}
                  </div>
                )}
                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>当前密码</label>
                  <Input id="old-password" type="password" placeholder="请输入当前密码" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required className="h-11 rounded-xl" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f0f0f0' 
                  }} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>新密码</label>
                  <Input id="new-password" type="password" placeholder="请输入新密码（至少8位，含大小写字母和数字）" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required className="h-11 rounded-xl" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f0f0f0' 
                  }} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>确认新密码</label>
                  <Input id="confirm-password" type="password" placeholder="请再次输入新密码" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className="h-11 rounded-xl" style={{ 
                    background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                    color: isLight ? '#1e293b' : '#f0f0f0' 
                  }} />
                </div>
                <Button type="submit" disabled={changingPassword} className="h-11 rounded-xl font-medium" style={{ 
                  background: isLight ? colors.CYBER_BLUE : `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)`, 
                  color: '#ffffff', 
                  boxShadow: `0 4px 20px ${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}40` 
                }}>
                  {changingPassword ? '修改中...' : '修改密码'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}