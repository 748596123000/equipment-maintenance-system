import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trash2, Plus, FileText, Users, Search, MessageSquare, Activity } from "lucide-react";

interface UserItem {
  id: string;
  username: string;
  role: string;
  created_at: string;
}

interface LogItem {
  id: string;
  created_at: string;
  user_id: string;
  action: string;
  detail: string;
  ip_address: string;
}

interface Pagination {
  total: number;
  page: number;
  page_size: number;
}

interface LogResponse {
  logs: LogItem[];
  pagination: Pagination;
}

interface AdminStats {
  document_count: number;
  user_count: number;
  chat_count: number;
  total_chunks: number;
  guide_count: number;
  chroma_status: string;
  db_size_mb: number;
}

interface HealthInfo {
  status: string;
  version?: string;
  uptime?: number;
}

export default function AdminPage() {
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

  const fetchUsers = useCallback(async () => {
    try {
      const res = await api.get<{ users: UserItem[] }>("/admin/users");
      setUsers(res.data.users || []);
    } catch {
      setUsers([]);
    }
  }, []);

  const fetchLogs = useCallback(async (page: number) => {
    try {
      const res = await api.get<LogResponse>("/admin/logs", {
        params: { page, page_size: logPageSize },
      });
      setLogs(res.data.logs || []);
      const p = res.data.pagination;
      setLogTotal(p?.total || 0);
      setLogPage(p?.page || 1);
    } catch {
      setLogs([]);
      setLogTotal(0);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get<AdminStats>("/admin/stats");
      setStats(res.data);
    } catch {
      setStats(null);
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await api.get("/admin/health");
      setHealth(res.data);
    } catch {
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchLogs(1);
    fetchStats();
    fetchHealth();
  }, [fetchUsers, fetchLogs, fetchStats, fetchHealth]);

  const handleCreateUser = useCallback(async () => {
    try {
      await api.post("/admin/users", {
        username: newUsername,
        password: newPassword,
        role: newRole,
      });
      fetchUsers();
    } catch {
    } finally {
      setCreateDialogOpen(false);
      setNewUsername("");
      setNewPassword("");
      setNewRole("user");
    }
  }, [newUsername, newPassword, newRole, fetchUsers]);

  const handleDeleteUser = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/admin/users/${deleteTarget.id}`);
      fetchUsers();
    } catch {
    } finally {
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    }
  }, [deleteTarget, fetchUsers]);

  const totalPages = Math.ceil(logTotal / logPageSize);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">⚙️ 系统管理</h1>

      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">用户管理</TabsTrigger>
          <TabsTrigger value="logs">系统日志</TabsTrigger>
          <TabsTrigger value="info">系统信息</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">用户列表</h2>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-1 h-4 w-4" />
              创建用户
            </Button>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>用户名</TableHead>
                <TableHead>角色</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    暂无用户数据
                  </TableCell>
                </TableRow>
              ) : (
                users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.username}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          u.role === "admin"
                            ? "bg-purple-100 text-purple-800 border-purple-200"
                            : "bg-blue-100 text-blue-800 border-blue-200"
                        }
                      >
                        {u.role === "admin" ? "管理员" : "普通用户"}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(u.created_at).toLocaleString("zh-CN")}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setDeleteTarget(u);
                          setDeleteDialogOpen(true);
                        }}
                        title="删除用户"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <h2 className="text-lg font-semibold">系统日志</h2>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>用户</TableHead>
                <TableHead>操作</TableHead>
                <TableHead>详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    暂无日志数据
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{new Date(log.created_at).toLocaleString("zh-CN")}</TableCell>
                    <TableCell>{log.user_id}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.action}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">{log.detail}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              共 {logTotal} 条记录，第 {logPage} / {totalPages || 1} 页
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={logPage <= 1}
                onClick={() => fetchLogs(logPage - 1)}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={logPage >= totalPages}
                onClick={() => fetchLogs(logPage + 1)}
              >
                下一页
              </Button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="info" className="space-y-4">
          <h2 className="text-lg font-semibold">系统统计</h2>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">文档总数</CardTitle>
                <FileText className="h-5 w-5 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {stats?.document_count?.toLocaleString() ?? "-"}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">用户数</CardTitle>
                <Users className="h-5 w-5 text-purple-500" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {stats?.user_count?.toLocaleString() ?? "-"}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">问答次数</CardTitle>
                <Search className="h-5 w-5 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {stats?.chat_count?.toLocaleString() ?? "-"}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">知识分块</CardTitle>
                <MessageSquare className="h-5 w-5 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {stats?.total_chunks?.toLocaleString() ?? "-"}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-lg font-semibold">系统健康状态</CardTitle>
              <Activity className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {health ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">运行状态：</span>
                    <Badge
                      variant="outline"
                      className={
                        health.status === "ok" || health.status === "healthy"
                          ? "bg-green-100 text-green-800 border-green-200"
                          : "bg-red-100 text-red-800 border-red-200"
                      }
                    >
                      {health.status === "ok" || health.status === "healthy" ? "正常运行" : health.status}
                    </Badge>
                  </div>
                  {health.version && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">系统版本：</span>
                      <span className="text-sm text-muted-foreground">{health.version}</span>
                    </div>
                  )}
                  {health.uptime !== undefined && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">运行时长：</span>
                      <span className="text-sm text-muted-foreground">
                        {Math.floor(health.uptime / 3600)} 小时 {Math.floor((health.uptime % 3600) / 60)} 分钟
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">无法获取系统健康状态</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建用户</DialogTitle>
            <DialogDescription>创建一个新的系统用户账号。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">用户名</label>
              <Input
                placeholder="请输入用户名"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">密码</label>
              <Input
                type="password"
                placeholder="请输入密码"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">角色</label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger>
                  <SelectValue placeholder="选择角色" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">普通用户</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateUser}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除用户</DialogTitle>
            <DialogDescription>
              确定要删除用户「{deleteTarget?.username}」吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteUser}>
              <Trash2 className="mr-1 h-4 w-4" />
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
