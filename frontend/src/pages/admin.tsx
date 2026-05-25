import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/css-tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trash2, Plus, FileText, Users, MessageSquare, Activity, UserCheck, UserX, Clock, Settings2, Shield, Database, Zap, ChevronRight, Server, UserCog, ScrollText, AlertCircle, CheckCircle2 } from "lucide-react";
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

const LOCAL_COLORS = COLORS

interface ComponentHealth {
  status: string
  message?: string
}

interface HealthInfo {
  status: string
  service?: string
  version?: string
  uptime?: number
  components?: {
    database?: ComponentHealth
    chromadb?: ComponentHealth
    llm?: ComponentHealth
    embedding?: ComponentHealth
  }
}

interface UserItem { id: string; username: string; role: string; created_at: string; status?: string }
interface LogItem { id: string; created_at: string; user_id: string; action: string; detail: string; ip_address: string }
interface Pagination { total: number; page: number; page_size: number }
interface LogResponse { logs: LogItem[]; pagination: Pagination }
interface AdminStats { document_count: number; user_count: number; chat_count: number; total_chunks: number; guide_count: number; chroma_status: string; db_size_mb: number }

export default function AdminPage() {
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  
  const [mounted, setMounted] = useState(false);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [logTotal, setLogTotal] = useState(0);
  const [logPage, setLogPage] = useState(1);
  const logPageSize = 20;
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<UserItem | null>(null);
  const [pendingUsers, setPendingUsers] = useState<UserItem[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => { setMounted(true) }, []);

  const fetchUsers = useCallback(async () => {
    try { const res = await api.get<{ users: UserItem[] }>("/admin/users"); setUsers(res.data.users || []); }
    catch { setUsers([]); }
  }, []);

  const fetchLogs = useCallback(async (page: number) => {
    try {
      const res = await api.get<LogResponse>("/admin/logs", { params: { page, page_size: logPageSize } });
      setLogs(res.data.logs || []);
      const p = res.data.pagination;
      setLogTotal(p?.total || 0); setLogPage(p?.page || 1);
    } catch { setLogs([]); setLogTotal(0); }
  }, []);

  const fetchStats = useCallback(async () => {
    try { const res = await api.get<AdminStats>("/admin/stats"); setStats(res.data); }
    catch { setStats(null); }
  }, []);

  const fetchHealth = useCallback(async () => {
    try { const res = await api.get("/admin/health"); setHealth(res.data); }
    catch { 
      // Fallback: try main health endpoint
      try {
        const mainRes = await api.get("/health/ready");
        setHealth(mainRes.data);
      } catch {
        setHealth({ status: 'degraded', components: {} });
      }
    }
  }, []);

  const fetchPendingUsers = useCallback(async () => {
    try { const res = await api.get<{ users: UserItem[] }>("/auth/pending-users"); setPendingUsers(res.data.users || []); }
    catch { setPendingUsers([]); }
  }, []);

  useEffect(() => { fetchUsers(); fetchLogs(1); fetchStats(); fetchHealth(); fetchPendingUsers(); }, []);

  const handleApproveUser = useCallback(async (userId: string) => {
    try { await api.post(`/auth/${userId}/approve`); fetchPendingUsers(); fetchUsers(); }
    catch { setErrorMsg("审批操作失败，请稍后重试"); }
  }, [fetchPendingUsers, fetchUsers]);

  const handleRejectUser = useCallback(async (userId: string) => {
    try { await api.post(`/auth/${userId}/reject`); fetchPendingUsers(); }
    catch { setErrorMsg("拒绝操作失败，请稍后重试"); }
  }, [fetchPendingUsers]);

  const handleCreateUser = useCallback(async () => {
    try {
      await api.post("/admin/users", { username: newUsername, password: newPassword, role: newRole });
      fetchUsers(); setCreateDialogOpen(false);
      setNewUsername(""); setNewPassword(""); setNewRole("user");
    } catch { setErrorMsg("创建用户失败，请检查用户名是否重复"); }
  }, [newUsername, newPassword, newRole, fetchUsers]);

  const handleDeleteUser = useCallback(async () => {
    if (!deleteTarget) return;
    try { await api.delete(`/admin/users/${deleteTarget.id}`); fetchUsers(); }
    catch { setErrorMsg("删除用户失败，请稍后重试"); }
    finally { setDeleteDialogOpen(false); setDeleteTarget(null); }
  }, [deleteTarget, fetchUsers]);

  const totalPages = Math.ceil(logTotal / logPageSize);

  return (
    <div className={`space-y-6 ${mounted ? 'opacity-100' : 'opacity-0'} transition-opacity duration-300`}>
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_PURPLE} 100%)` 
              : `linear-gradient(135deg, ${colors.CYBER_PURPLE} 0%, ${colors.CYBER_BLUE} 100%)`, 
            boxShadow: `0 4px 20px ${isLight ? colors.CYBER_BLUE : colors.CYBER_PURPLE}30` 
          }}>
          <Settings2 size={28} style={{ color: '#ffffff' }} />
        </div>
        <div>
          <GradientText as="h1" className="text-2xl font-bold" style={{ 
            background: isLight 
              ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_PURPLE} 100%)` 
              : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_PURPLE} 100%)`, 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent' 
          }}>
            系统管理中心
          </GradientText>
          <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>System Administration Console</p>
        </div>
      </div>

      {/* Stats Cards - Optimized for smooth rendering */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '文档总数', value: stats?.document_count ?? 0, icon: FileText, color: colors.CYBER_PURPLE },
          { label: '用户数', value: stats?.user_count ?? 0, icon: Users, color: colors.CYBER_BLUE },
          { label: '问答次数', value: stats?.chat_count ?? 0, icon: MessageSquare, color: colors.CYBER_GREEN },
          { label: '知识分块', value: stats?.total_chunks ?? 0, icon: Database, color: colors.CYBER_YELLOW },
        ].map((stat) => (
          <div key={stat.label} className="p-5 rounded-xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.8)', 
            border: `1px solid ${isLight ? '#e2e8f0' : stat.color + '20'}`,
            transition: 'transform 150ms ease, box-shadow 150ms ease',
            willChange: 'transform',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = `0 8px 25px ${stat.color}15`
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}>
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${stat.color}15` }}>
                <stat.icon size={20} style={{ color: stat.color }} />
              </div>
              <div className="text-2xl font-bold" style={{ color: stat.color }}>{stat.value.toLocaleString()}</div>
            </div>
            <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Health Status - Simplified */}
      {health && (
        <div className="p-4 rounded-xl" style={{ 
          background: isLight ? '#ffffff' : 'rgba(15,15,30,0.8)', 
          border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_PURPLE + '20'}` 
        }}>
          <div className="flex items-center gap-3">
            {health.status === 'healthy' ? (
              <CheckCircle2 size={18} style={{ color: colors.CYBER_GREEN }} />
            ) : (
              <AlertCircle size={18} style={{ color: health.status === 'degraded' ? colors.CYBER_YELLOW : colors.CYBER_RED }} />
            )}
            <span className="text-sm font-medium" style={{ color: health.status === 'healthy' ? colors.CYBER_GREEN : health.status === 'degraded' ? colors.CYBER_YELLOW : colors.CYBER_RED }}>
              系统{health.status === 'healthy' ? '运行正常' : health.status === 'degraded' ? '部分异常' : '异常'}
            </span>
            {health.version && <Badge variant="outline" className="ml-auto text-xs" style={{ borderColor: `${colors.CYBER_PURPLE}50`, background: `${colors.CYBER_PURPLE}10`, color: colors.CYBER_PURPLE }}>v{health.version}</Badge>}
          </div>
        </div>
      )}

      {/* Main Tabs - Simplified for performance */}
      <div className="rounded-xl overflow-hidden" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_PURPLE + '20'}`,
          }}>
        <Tabs defaultValue="users" className="w-full">
          <TabsList className="w-full justify-start gap-0 px-4 pt-4 pb-0 h-auto bg-transparent border-b-0 rounded-none">
            <TabsTrigger value="users">
              <UserCog size={16} className="mr-2" /> 用户管理
            </TabsTrigger>
            <TabsTrigger value="approval">
              <ScrollText size={16} className="mr-2" /> 用户审批
              {pendingUsers.length > 0 && <Badge className="ml-2 h-5 min-w-[20px] px-1.5 text-xs" style={{ background: `${colors.CYBER_YELLOW}30`, color: colors.CYBER_YELLOW }}>{pendingUsers.length}</Badge>}
            </TabsTrigger>
            <TabsTrigger value="logs">
              <Activity size={16} className="mr-2" /> 系统日志
            </TabsTrigger>
            <TabsTrigger value="info">
                <Server size={16} className="mr-2" /> 系统信息
            </TabsTrigger>
          </TabsList>

          <div className="p-6">
            <TabsContent value="users" className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Users size={18} style={{ color: colors.CYBER_CYAN }} /> 用户列表
                </h2>
                <Button onClick={() => setCreateDialogOpen(true)} className="rounded-lg font-medium" style={{ background: `linear-gradient(135deg, ${colors.CYBER_PURPLE} 0%, ${colors.CYBER_BLUE} 100%)`, color: '#fff' }}>
                  <Plus className="mr-1 h-4 w-4" /> 创建用户
                </Button>
              </div>
              <div className="rounded-xl overflow-hidden" style={{ 
                background: isLight ? '#ffffff' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}` 
              }}>
                <Table>
                  <TableHeader>
                    <TableRow style={{ background: isLight ? '#f1f5f9' : `${colors.CYBER_CYAN}10` }}>
                      <TableHead style={{ color: isLight ? '#1e293b' : colors.CYBER_CYAN, fontWeight: '600' }}>用户名</TableHead>
                      <TableHead style={{ color: isLight ? '#1e293b' : colors.CYBER_CYAN, fontWeight: '600' }}>角色</TableHead>
                      <TableHead style={{ color: isLight ? '#1e293b' : colors.CYBER_CYAN, fontWeight: '600' }}>创建时间</TableHead>
                      <TableHead style={{ color: isLight ? '#1e293b' : colors.CYBER_CYAN, fontWeight: '600' }} className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.length === 0 ? (
                      <TableRow><TableCell colSpan={4} className="h-24 text-center" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>暂无用户数据</TableCell></TableRow>
                    ) : (
                      users.map((u) => (
                        <TableRow key={u.id} className="hover:bg-[rgba(0,240,255,0.05)] transition-colors">
                          <TableCell className="font-medium">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-black" style={{ background: `linear-gradient(135deg, ${colors.CYBER_PURPLE} 0%, ${colors.CYBER_BLUE} 100%)` }}>
                                {u.username.charAt(0).toUpperCase()}
                              </div>
                              <span style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{u.username}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" style={{ background: u.role === "admin" ? `${colors.CYBER_CYAN}20` : `${colors.CYBER_PURPLE}20`, color: u.role === "admin" ? colors.CYBER_CYAN : colors.CYBER_PURPLE, borderColor: u.role === "admin" ? `${colors.CYBER_CYAN}50` : `${colors.CYBER_PURPLE}50` }}>
                              <Shield className="mr-1 h-3 w-3" /> {u.role === "admin" ? "管理员" : "普通用户"}
                            </Badge>
                          </TableCell>
                          <TableCell style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>{new Date(u.created_at).toLocaleString("zh-CN")}</TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="icon" onClick={() => { setDeleteTarget(u); setDeleteDialogOpen(true); }} title="删除用户" className="hover:bg-[rgba(239,68,68,0.1)]">
                              <Trash2 className="h-4 w-4" style={{ color: colors.CYBER_RED }} />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="approval" className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <ScrollText size={18} style={{ color: colors.CYBER_CYAN }} /> 待审批用户
                </h2>
                <Button variant="outline" size="sm" onClick={fetchPendingUsers} className="rounded-lg" style={{ 
                  borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}50`,
                  color: isLight ? '#475569' : '#e8e8e8',
                  background: isLight ? '#ffffff' : 'transparent'
                }}>
                  <Zap className="mr-1 h-4 w-4" /> 刷新
                </Button>
              </div>
              {pendingUsers.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Clock className="h-12 w-12 mb-4" style={{ color: isLight ? '#cbd5e1' : '#505080' }} />
                  <p className="text-lg" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>暂无待审批用户</p>
                  <p className="text-sm mt-2" style={{ color: isLight ? '#94a3b8' : 'rgba(148,163,184,0.5)' }}>所有用户注册申请已处理完毕</p>
                </div>
              ) : (
<div className="rounded-xl overflow-hidden" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`,
                boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
              }}>
                  <Table>
                    <TableHeader>
                      <TableRow style={{ background: `${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}10` }}>
                        <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>用户名</TableHead>
                        <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>注册时间</TableHead>
                        <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>状态</TableHead>
                        <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pendingUsers.map((u) => (
                        <TableRow key={u.id} className="hover:bg-[rgba(0,240,255,0.05)] transition-colors">
                          <TableCell className="font-medium">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-black" style={{ background: `linear-gradient(135deg, ${colors.CYBER_CYAN} 0%, ${colors.CYBER_BLUE} 100%)` }}>
                                {u.username.charAt(0).toUpperCase()}
                              </div>
                              <span style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{u.username}</span>
                            </div>
                          </TableCell>
                          <TableCell style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>{new Date(u.created_at).toLocaleString("zh-CN")}</TableCell>
                          <TableCell>
                            <Badge variant="outline" style={{ background: `${colors.CYBER_YELLOW}20`, color: colors.CYBER_YELLOW, borderColor: `${colors.CYBER_YELLOW}50` }}>
                              <Clock className="mr-1 h-3 w-3" /> 待审批
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Button variant="outline" size="sm" onClick={() => handleApproveUser(u.id)} className="rounded-lg" style={{ borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_GREEN}50`, color: isLight ? colors.CYBER_GREEN : colors.CYBER_GREEN }}>
                                <UserCheck className="mr-1 h-3.5 w-3.5" /> 通过
                              </Button>
                              <Button variant="outline" size="sm" onClick={() => handleRejectUser(u.id)} className="rounded-lg" style={{ 
                                borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_RED}50`, 
                                color: isLight ? colors.CYBER_RED : colors.CYBER_RED,
                                background: isLight ? '#ffffff' : 'transparent'
                              }}>
                                <UserX className="mr-1 h-3.5 w-3.5" /> 拒绝
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>

            <TabsContent value="logs" className="space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Activity size={18} style={{ color: colors.CYBER_CYAN }} /> 系统日志
              </h2>
              <div className="rounded-xl overflow-hidden" style={{ 
                background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`,
                boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
              }}>
                <Table>
                  <TableHeader>
                    <TableRow style={{ background: `${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}10` }}>
                      <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>时间</TableHead>
                      <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>用户</TableHead>
                      <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>操作</TableHead>
                      <TableHead style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>详情</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 ? (
                      <TableRow><TableCell colSpan={4} className="h-24 text-center" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>暂无日志数据</TableCell></TableRow>
                    ) : (
                      logs.map((log) => (
                        <TableRow key={log.id} className="hover:bg-[rgba(0,240,255,0.05)] transition-colors">
                          <TableCell className="font-mono text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>{new Date(log.created_at).toLocaleString("zh-CN")}</TableCell>
                          <TableCell style={{ color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>{log.user_id}</TableCell>
                          <TableCell>
                            <Badge variant="outline" style={{ borderColor: `${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}50`, background: `${isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN}10`, color: isLight ? colors.CYBER_BLUE : colors.CYBER_CYAN }}>
                              {log.action}
                            </Badge>
                          </TableCell>
                          <TableCell className="max-w-[300px] truncate" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>{log.detail}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
              <div className="flex items-center justify-between px-2">
                <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>共 {logTotal} 条记录，第 {logPage} / {totalPages || 1} 页</p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" disabled={logPage <= 1} onClick={() => fetchLogs(logPage - 1)} className="rounded-lg" style={{ borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}50` }}>上一页</Button>
                  <Button variant="outline" size="sm" disabled={logPage >= totalPages} onClick={() => fetchLogs(logPage + 1)} className="rounded-lg" style={{ borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}50` }}>下一页</Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="info" className="space-y-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Server size={18} style={{ color: colors.CYBER_CYAN }} /> 系统信息
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { label: '文档总数', value: stats?.document_count?.toLocaleString() ?? '-', icon: FileText, color: colors.CYBER_PURPLE },
                  { label: '用户数', value: stats?.user_count?.toLocaleString() ?? '-', icon: Users, color: colors.CYBER_BLUE },
                  { label: '问答次数', value: stats?.chat_count?.toLocaleString() ?? '-', icon: MessageSquare, color: colors.CYBER_GREEN },
                  { label: '知识分块', value: stats?.total_chunks?.toLocaleString() ?? '-', icon: Database, color: colors.CYBER_YELLOW },
                ].map((stat) => (
                  <div key={stat.label} className="p-5 rounded-xl" style={{ 
                    background: isLight ? '#ffffff' : 'rgba(15,15,30,0.8)', 
                    border: `1px solid ${isLight ? '#e2e8f0' : stat.color + '30'}`,
                    boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.04)' : undefined
                  }}>
                    <div>
                      <p className="text-sm" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>{stat.label}</p>
                      <p className="text-2xl font-bold" style={{ color: stat.color }}>{stat.value}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-6 rounded-xl" style={{ 
                background: isLight ? '#ffffff' : 'rgba(15,15,30,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_GREEN + '30'}` 
              }}>
<div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Activity className="h-5 w-5" style={{ color: health?.status === 'healthy' ? colors.CYBER_GREEN : health?.status === 'degraded' ? colors.CYBER_YELLOW : colors.CYBER_RED }} /> 系统健康状态
                  </h3>
                  <Badge variant="outline" style={{ 
                    background: health?.status === 'healthy' ? `${colors.CYBER_GREEN}20` : health?.status === 'degraded' ? `${colors.CYBER_YELLOW}20` : `${colors.CYBER_RED}20`, 
                    color: health?.status === 'healthy' ? colors.CYBER_GREEN : health?.status === 'degraded' ? colors.CYBER_YELLOW : colors.CYBER_RED, 
                    borderColor: health?.status === 'healthy' ? `${colors.CYBER_GREEN}50` : health?.status === 'degraded' ? `${colors.CYBER_YELLOW}50` : `${colors.CYBER_RED}50` 
                  }}>
                    {health?.status === 'healthy' ? '全部正常' : health?.status === 'degraded' ? '部分异常' : '异常'}
                  </Badge>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  {health?.version && (
                    <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_CYAN}10`, border: `1px solid ${colors.CYBER_CYAN}30` }}>
                      <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>系统版本</p>
                      <p className="text-sm font-medium" style={{ color: colors.CYBER_CYAN }}>v{health.version}</p>
                    </div>
                  )}
                  {health?.uptime !== undefined && (
                    <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_BLUE}10`, border: `1px solid ${colors.CYBER_BLUE}30` }}>
                      <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>运行时长</p>
                      <p className="text-sm font-medium" style={{ color: colors.CYBER_BLUE }}>{Math.floor(health.uptime / 3600)} 小时 {Math.floor((health.uptime % 3600) / 60)} 分钟</p>
                    </div>
                  )}
                  <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_GREEN}10`, border: `1px solid ${colors.CYBER_GREEN}30` }}>
                    <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>数据库状态</p>
                    <p className="text-sm font-medium" style={{ color: colors.CYBER_GREEN }}>{stats?.chroma_status === 'connected' ? '已连接' : stats?.chroma_status || '未知'}</p>
                  </div>
                </div>
                {health?.components && (
                  <div className="space-y-3">
                    <p className="text-sm font-medium" style={{ color: isLight ? '#475569' : 'rgba(148,163,184,0.8)' }}>组件状态详情</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(health.components).map(([key, comp]) => (
                        <div key={key} className="p-4 rounded-xl flex items-center gap-3" style={{ 
                          background: comp?.status === 'healthy' ? `${colors.CYBER_GREEN}05` : comp?.status === 'degraded' || comp?.status === 'unavailable' ? `${colors.CYBER_YELLOW}05` : `${colors.CYBER_RED}05`,
                          border: `1px solid ${comp?.status === 'healthy' ? colors.CYBER_GREEN + '20' : comp?.status === 'degraded' || comp?.status === 'unavailable' ? colors.CYBER_YELLOW + '20' : colors.CYBER_RED + '20'}`
                        }}>
                          {comp?.status === 'healthy' ? (
                            <CheckCircle2 size={18} style={{ color: colors.CYBER_GREEN }} />
                          ) : (
                            <AlertCircle size={18} style={{ color: comp?.status === 'degraded' || comp?.status === 'unavailable' ? colors.CYBER_YELLOW : colors.CYBER_RED }} />
                          )}
                          <div className="flex-1">
                            <p className="text-sm font-medium" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>
                              {key === 'database' ? '数据库' : key === 'chromadb' ? '向量数据库(ChromaDB)' : key === 'llm' ? '大语言模型(LLM)' : key === 'embedding' ? 'Embedding服务' : key}
                            </p>
                            <p className="text-xs" style={{ color: comp?.status === 'healthy' ? colors.CYBER_GREEN : comp?.status === 'degraded' || comp?.status === 'unavailable' ? colors.CYBER_YELLOW : colors.CYBER_RED }}>
                              {comp?.status === 'healthy' ? '运行正常' : comp?.status === 'degraded' ? '部分异常（服务降级）' : comp?.status === 'unavailable' ? '暂不可用（未配置API Key）' : '异常'}
                            </p>
                            {comp?.message && (
                              <p className="text-xs mt-1" style={{ color: isLight ? '#94a3b8' : 'rgba(148,163,184,0.6)' }}>{comp.message}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {health?.version && (
                    <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_CYAN}10`, border: `1px solid ${colors.CYBER_CYAN}30` }}>
                      <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>系统版本</p>
                      <p className="text-sm font-medium" style={{ color: colors.CYBER_CYAN }}>v{health.version}</p>
                    </div>
                  )}
                  {health?.uptime !== undefined && (
                    <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_BLUE}10`, border: `1px solid ${colors.CYBER_BLUE}30` }}>
                      <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>运行时长</p>
                      <p className="text-sm font-medium" style={{ color: colors.CYBER_BLUE }}>{Math.floor(health.uptime / 3600)} 小时 {Math.floor((health.uptime % 3600) / 60)} 分钟</p>
                    </div>
                  )}
                  <div className="p-4 rounded-xl" style={{ background: `${colors.CYBER_GREEN}10`, border: `1px solid ${colors.CYBER_GREEN}30` }}>
                    <p className="text-xs mb-1" style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.7)' }}>数据库状态</p>
                    <p className="text-sm font-medium" style={{ color: colors.CYBER_GREEN }}>{stats?.chroma_status === 'connected' ? '已连接' : stats?.chroma_status || '未知'}</p>
                  </div>
                </div>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_PURPLE + '30'}` 
          }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, ${colors.CYBER_BLUE} 0%, ${colors.CYBER_PURPLE} 100%)` 
                  : `linear-gradient(135deg, ${colors.CYBER_PURPLE} 0%, ${colors.CYBER_BLUE} 100%)` 
              }}>
                <UserCog size={20} style={{ color: '#ffffff' }} />
              </div>
              <GradientText as="h2" className="text-xl" style={{ 
                background: isLight 
                  ? `linear-gradient(135deg, #1e293b 0%, ${colors.CYBER_PURPLE} 100%)` 
                  : `linear-gradient(135deg, #ffffff 0%, ${colors.CYBER_PURPLE} 100%)`, 
                WebkitBackgroundClip: 'text', 
                WebkitTextFillColor: 'transparent' 
              }}>创建用户</GradientText>
            </div>
            <DialogDescription style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>创建一个新的系统用户账号</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>用户名</label>
              <Input placeholder="请输入用户名" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} style={{ 
                background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                color: isLight ? '#1e293b' : '#f0f0f0' 
              }} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>密码</label>
              <Input type="password" placeholder="请输入密码" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} style={{ 
                background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                color: isLight ? '#1e293b' : '#f0f0f0' 
              }} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: isLight ? '#475569' : '#c0c0d0' }}>角色</label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger className="rounded-xl" style={{ 
                  background: isLight ? '#f8fafc' : 'rgba(10,10,25,0.8)', 
                  border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '20'}`, 
                  color: isLight ? '#1e293b' : '#f0f0f0' 
                }}>
                  <SelectValue placeholder="选择角色" />
                </SelectTrigger>
                <SelectContent style={{ 
                  background: isLight ? '#ffffff' : 'rgba(20,20,40,0.98)', 
                  border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_CYAN + '15'}` 
                }}>
                  <SelectItem value="user">普通用户</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)} className="rounded-xl" style={{ 
              borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}50`, 
              color: isLight ? '#475569' : '#e8e8e8',
              background: isLight ? '#ffffff' : 'transparent'
            }}>取消</Button>
            <Button onClick={handleCreateUser} className="rounded-xl" style={{ 
              background: isLight ? colors.CYBER_PURPLE : `linear-gradient(135deg, ${colors.CYBER_PURPLE} 0%, ${colors.CYBER_BLUE} 100%)`, 
              color: '#fff' 
            }}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="rounded-2xl" style={{ 
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)', 
            border: `1px solid ${isLight ? '#e2e8f0' : colors.CYBER_RED + '30'}` 
          }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${colors.CYBER_RED}20` }}>
                <Trash2 size={20} style={{ color: colors.CYBER_RED }} />
              </div>
              <DialogTitle className="text-xl" style={{ color: colors.CYBER_RED }}>确认删除用户</DialogTitle>
            </div>
            <DialogDescription style={{ color: isLight ? '#64748b' : 'rgba(148,163,184,0.6)' }}>确定要删除用户「{deleteTarget?.username}」吗？此操作不可撤销。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="rounded-xl" style={{ 
              borderColor: isLight ? '#e2e8f0' : `${colors.CYBER_CYAN}50`, 
              color: isLight ? '#475569' : '#e8e8e8',
              background: isLight ? '#ffffff' : 'transparent'
            }}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteUser} className="rounded-xl" style={{ background: colors.CYBER_RED }}><Trash2 className="mr-1 h-4 w-4" /> 删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}